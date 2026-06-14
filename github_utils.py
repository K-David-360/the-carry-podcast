"""
github_utils.py — GitHub API helpers and feed.xml utilities for The Carry podcast.
Adapted from morning-brew-podcast/pipeline.py.
"""

import base64
import logging
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO = "K-David-360/the-carry-podcast"
BASE_URL = "https://k-david-360.github.io/the-carry-podcast"
API_BASE = f"https://api.github.com/repos/{REPO}/contents"
FEED_PATH = "feed.xml"
AUDIO_DIR = "audio"
RETENTION_DAYS = 30

ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

log = logging.getLogger(__name__)


def _gh_headers() -> dict:
    token = GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_get_file(path: str) -> tuple[str, str]:
    resp = requests.get(f"{API_BASE}/{path}", headers=_gh_headers())
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def gh_put_file(path: str, content: str | bytes, message: str, sha: Optional[str] = None) -> None:
    if isinstance(content, str):
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    else:
        encoded = base64.b64encode(content).decode("ascii")
    payload: dict = {"message": message, "content": encoded}
    if sha:
        payload["sha"] = sha
    requests.put(f"{API_BASE}/{path}", json=payload, headers=_gh_headers()).raise_for_status()


def gh_put_large_file(path: str, content: bytes, message: str) -> None:
    """Upload large binary via shallow git clone + push (bypasses 25 MB REST limit)."""
    git_bin = shutil.which("git") or "/usr/bin/git"
    token = GITHUB_TOKEN or os.getenv("GITHUB_TOKEN", "")
    clone_url = f"https://{token}@github.com/{REPO}.git"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        def _git(*args: str) -> None:
            r = subprocess.run([git_bin, "-C", str(tmp), *args], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"git {args[0]} failed:\n{r.stderr}")

        subprocess.run([git_bin, "clone", "--depth=1", clone_url, str(tmp)],
                       capture_output=True, text=True, check=True)
        dest = tmp / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        _git("config", "user.email", "pipeline@the-carry-podcast")
        _git("config", "user.name", "The Carry Pipeline")
        _git("config", "http.postBuffer", "157286400")
        _git("add", path)
        _git("commit", "-m", message)
        _git("push")
        shutil.rmtree(str(tmp), ignore_errors=True)


def gh_delete_file(path: str, sha: str, message: str) -> None:
    resp = requests.delete(f"{API_BASE}/{path}",
                           json={"message": message, "sha": sha}, headers=_gh_headers())
    if resp.status_code != 404:
        resp.raise_for_status()


def gh_get_sha(path: str) -> Optional[str]:
    resp = requests.get(f"{API_BASE}/{path}", headers=_gh_headers())
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()["sha"]


def build_item(title: str, description: str, audio_url: str, file_size: int,
               guid: str, pub_date: datetime, duration: str) -> ET.Element:
    item = ET.Element("item")

    def sub(tag: str, text: str) -> ET.Element:
        el = ET.SubElement(item, tag)
        el.text = text
        return el

    sub("title", title)
    sub("description", description)
    enc = ET.SubElement(item, "enclosure")
    enc.set("url", audio_url)
    enc.set("length", str(file_size))
    enc.set("type", "audio/mp4")
    sub("guid", guid).set("isPermaLink", "false")
    sub("pubDate", format_datetime(pub_date))
    sub(f"{{{ITUNES_NS}}}duration", duration)
    sub(f"{{{ITUNES_NS}}}summary", description)
    return item


def remove_old_items(channel: ET.Element, cutoff: datetime) -> list[str]:
    to_remove: list[str] = []
    for item in list(channel.findall("item")):
        pub_el = item.find("pubDate")
        if pub_el is None or not pub_el.text:
            continue
        pub_date = parsedate_to_datetime(pub_el.text)
        if pub_date and pub_date < cutoff:
            enc = item.find("enclosure")
            if enc is not None:
                fname = (enc.get("url", "")).rstrip("/").split("/")[-1]
                if fname:
                    to_remove.append(fname)
            channel.remove(item)
    return to_remove


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    pad = "\n" + "  " * level
    child_pad = "\n" + "  " * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_pad
        if not elem.tail or not elem.tail.strip():
            elem.tail = pad
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = pad
    elif level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad
