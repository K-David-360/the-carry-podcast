#!/usr/bin/env python3
"""
finance_pipeline.py — Weekly "The Carry" podcast pipeline.

1. Check FT Alphaville Substack RSS for a new post this week
2. Load this week's research emails
3. Create NotebookLM notebook with both sources (or research-only)
4. Generate and download audio
5. Remux → GitHub upload → feed.xml update
6. Update state.json

Usage:
    python finance_pipeline.py              # full run
    python finance_pipeline.py --dry-run    # check sources only, no side effects

Cron (Pi, Friday 6:30am Central — set TZ=America/Chicago in crontab):
    30 6 * * 5 /home/pi/the-carry-podcast/.venv/bin/python3 \
        /home/pi/the-carry-podcast/finance_pipeline.py >> \
        /home/pi/the-carry-podcast/pipeline.log 2>&1
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from pipeline_utils import read_state, write_state, load_gir_content, parse_alphaville_rss
from notebooklm_utils import generate_podcast_audio, delete_notebook
from github_utils import (
    gh_put_large_file, gh_get_file, gh_put_file, gh_get_sha, gh_delete_file,
    build_item, remove_old_items, indent_xml,
    BASE_URL, AUDIO_DIR, FEED_PATH, RETENTION_DAYS,
)

load_dotenv(Path(__file__).parent / ".env")

GIR_EMAIL_DIR = Path(__file__).parent / "gir_emails"
STATE_PATH = Path(__file__).parent / "state.json"
LOG_FILE = Path(__file__).parent / "pipeline.log"
ALPHAVILLE_RSS_URL = "https://ftav.substack.com/feed"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
log = logging.getLogger(__name__)


def load_env_config() -> None:
    if not os.getenv("GITHUB_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN is not set in .env")


def fetch_alphaville_rss() -> Optional[dict]:
    try:
        resp = requests.get(ALPHAVILLE_RSS_URL, timeout=15)
        resp.raise_for_status()
        return parse_alphaville_rss(resp.text)
    except Exception as exc:
        log.error("Failed to fetch Alphaville RSS: %s", exc)
        return None


def get_audio_duration(audio_path: Path) -> str:
    import json as _json
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.warning("ffprobe failed: %s", result.stderr.strip())
        return "00:00:00"
    data = _json.loads(result.stdout)
    total = int(float(data["format"]["duration"]))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def remux_to_m4a(input_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_path), "-c", "copy",
         "-movflags", "+faststart", str(output_path)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{result.stderr[-500:]}")


def publish_to_github(m4a_path: Path, title: str, description: str, date_str: str) -> None:
    audio_filename = m4a_path.name
    audio_repo_path = f"{AUDIO_DIR}/{audio_filename}"
    audio_url = f"{BASE_URL}/{AUDIO_DIR}/{audio_filename}"
    file_size = m4a_path.stat().st_size
    guid = f"the-carry-{date_str}"
    pub_date = datetime.now(tz=ZoneInfo("America/Chicago")).replace(
        hour=6, minute=30, second=0, microsecond=0
    )
    duration = get_audio_duration(m4a_path)
    log.info("Duration: %s", duration)

    log.info("Uploading %s...", audio_filename)
    gh_put_large_file(audio_repo_path, m4a_path.read_bytes(), f"Add audio for {date_str}")
    log.info("Audio uploaded")

    feed_content, feed_sha = gh_get_file(FEED_PATH)
    root = ET.ElementTree(ET.fromstring(feed_content)).getroot()
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("<channel> not found in feed.xml")

    new_item = build_item(
        title=title, description=description, audio_url=audio_url,
        file_size=file_size, guid=guid, pub_date=pub_date, duration=duration,
    )
    children = list(channel)
    first_item_idx = next((i for i, c in enumerate(children) if c.tag == "item"), len(children))
    channel.insert(first_item_idx, new_item)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=RETENTION_DAYS)
    stale = remove_old_items(channel, cutoff)
    if stale:
        log.info("Removing %d expired episode(s): %s", len(stale), stale)
        for fname in stale:
            stale_sha = gh_get_sha(f"{AUDIO_DIR}/{fname}")
            if stale_sha:
                gh_delete_file(f"{AUDIO_DIR}/{fname}", stale_sha, f"Remove expired {fname}")

    indent_xml(root)
    updated_feed = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root, encoding="unicode", xml_declaration=False
    )
    gh_put_file(FEED_PATH, updated_feed, f"Publish The Carry — {title} ({date_str})", feed_sha)
    log.info("Feed updated: %s/feed.xml", BASE_URL)


def run_pipeline(dry_run: bool = False) -> bool:
    """Returns True if episode was (or would be) published, False if skipped."""
    today = datetime.now(tz=timezone.utc)
    date_str = today.strftime("%Y-%m-%d")
    state = read_state(STATE_PATH)

    alphaville_item = fetch_alphaville_rss()
    alphaville_url: Optional[str] = None
    alphaville_title: Optional[str] = None

    if alphaville_item:
        if alphaville_item["guid"] != state.get("last_alphaville_guid", ""):
            alphaville_url = alphaville_item["url"]
            alphaville_title = alphaville_item["title"]
            log.info("New Alphaville post: %s", alphaville_title)
        else:
            log.info("No new Alphaville post — GIR-only episode")
    else:
        log.warning("Could not fetch Alphaville RSS")

    gir_content = load_gir_content(GIR_EMAIL_DIR)
    if gir_content:
        log.info("GIR content: %d chars", len(gir_content))
    else:
        log.warning("No GIR emails this week")

    if not gir_content and not alphaville_url:
        log.warning("No content from either source — skipping")
        return False

    if alphaville_title and gir_content:
        episode_title = f"The Carry: {alphaville_title}"
        description = (f"{alphaville_title} — GS research intelligence + FT Alphaville. "
                       f"Week of {date_str}.")
    elif alphaville_title:
        episode_title = f"The Carry: {alphaville_title}"
        description = f"{alphaville_title} — FT Alphaville. Week of {date_str}."
    else:
        episode_title = f"The Carry — Market Intelligence {date_str}"
        description = f"Institutional market intelligence. Week of {date_str}."

    log.info("Episode: %s", episode_title)

    if dry_run:
        log.info("Dry-run — stopping here. Sources: GIR=%s, Alphaville=%s",
                 bool(gir_content), alphaville_url or "none")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / f"the-carry-{date_str}.raw"
        m4a_path = Path(tmpdir) / f"the-carry-{date_str}.m4a"

        try:
            audio_title, notebook_id = asyncio.run(generate_podcast_audio(
                gir_content=gir_content or "",
                alphaville_url=alphaville_url,
                title=episode_title,
                output_path=raw_path,
            ))
        except Exception as exc:
            log.error("NotebookLM failed: %s", exc, exc_info=True)
            return False

        if audio_title:
            episode_title = f"{episode_title}: {audio_title}"
            log.info("Full episode title: %s", episode_title)

        log.info("Remuxing...")
        try:
            remux_to_m4a(raw_path, m4a_path)
        except Exception as exc:
            log.error("Remux failed: %s", exc, exc_info=True)
            return False
        log.info("Remux complete (%d bytes)", m4a_path.stat().st_size)

        try:
            publish_to_github(m4a_path, episode_title, description, date_str)
        except Exception as exc:
            log.error("GitHub publish failed: %s", exc, exc_info=True)
            return False

        if notebook_id:
            try:
                asyncio.run(delete_notebook(notebook_id))
            except Exception as exc:
                log.warning("Failed to delete notebook %s: %s", notebook_id, exc)

        if alphaville_item:
            state["last_alphaville_guid"] = alphaville_item["guid"]
        state["last_run_date"] = date_str
        write_state(state, STATE_PATH)
        log.info("State updated")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="The Carry podcast pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check sources only — no NotebookLM or GitHub")
    args = parser.parse_args()

    load_env_config()

    log.info("=" * 60)
    log.info("The Carry pipeline starting — %s",
             datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"))
    log.info("=" * 60)

    if not run_pipeline(dry_run=args.dry_run):
        log.error("Pipeline produced no episode.")
        sys.exit(1)

    log.info("Pipeline complete.")


if __name__ == "__main__":
    main()
