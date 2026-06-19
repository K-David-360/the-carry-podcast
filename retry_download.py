#!/usr/bin/env python3
"""
retry_download.py — Download audio from an existing NotebookLM notebook and publish.

Use when the pipeline generated audio but failed at the download step.
The notebook ID is logged by finance_pipeline.py as:
    INFO  Deleting notebook <notebook-id>
or in the traceback context.

Usage:
    python retry_download.py <notebook-id> "<episode-title>" [--date YYYY-MM-DD]

Example:
    python retry_download.py df5b62c5-7e73-4436-ac05-c05258cce61a \
        "The Carry: Building castles in the sky" --date 2026-06-19
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from notebooklm import NotebookLMClient
from notebooklm_utils import delete_notebook
from finance_pipeline import remux_to_m4a, publish_to_github
from pipeline_utils import read_state, write_state

STATE_PATH = Path(__file__).parent / "state.json"
LOG_FILE = Path(__file__).parent / "pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


async def download_audio(notebook_id: str, output_path: Path) -> str | None:
    async with await NotebookLMClient.from_storage() as c:
        audio_title = None
        try:
            artifacts = await c.artifacts.list_audio(notebook_id)
            if artifacts:
                audio_title = artifacts[0].title
                log.info("NotebookLM audio title: %s", audio_title)
        except Exception:
            pass

        log.info("Downloading to %s", output_path)
        await c.artifacts.download_audio(notebook_id, str(output_path))
        if output_path.exists():
            log.info("Downloaded (%d bytes)", output_path.stat().st_size)

        return audio_title


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry download from an existing NotebookLM notebook.")
    parser.add_argument("notebook_id", help="NotebookLM notebook ID from the pipeline log")
    parser.add_argument("episode_title", help="Episode title (e.g. 'The Carry: ...')")
    parser.add_argument("--date", default=None, help="Episode date YYYY-MM-DD (default: today)")
    parser.add_argument("--keep-notebook", action="store_true", help="Don't delete the notebook after download")
    args = parser.parse_args()

    date_str = args.date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    episode_title = args.episode_title
    notebook_id = args.notebook_id

    log.info("Retrying download for notebook %s", notebook_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / f"the-carry-{date_str}.raw"
        m4a_path = Path(tmpdir) / f"the-carry-{date_str}.m4a"

        try:
            audio_title = asyncio.run(download_audio(notebook_id, raw_path))
        except Exception as exc:
            log.error("Download failed: %s", exc, exc_info=True)
            sys.exit(1)

        if audio_title:
            episode_title = f"{episode_title}: {audio_title}"
            log.info("Full episode title: %s", episode_title)

        log.info("Remuxing...")
        try:
            remux_to_m4a(raw_path, m4a_path)
            log.info("Remux complete (%d bytes)", m4a_path.stat().st_size)
        except Exception as exc:
            log.error("Remux failed: %s", exc, exc_info=True)
            sys.exit(1)

        state = read_state(STATE_PATH)
        description = f"Institutional research + FT Alphaville. Week of {date_str}."

        try:
            publish_to_github(m4a_path, episode_title, description, date_str)
        except Exception as exc:
            log.error("Publish failed: %s", exc, exc_info=True)
            sys.exit(1)

        if not args.keep_notebook:
            try:
                asyncio.run(delete_notebook(notebook_id))
            except Exception as exc:
                log.warning("Could not delete notebook: %s", exc)

        write_state(STATE_PATH, state)
        log.info("Done.")


if __name__ == "__main__":
    main()
