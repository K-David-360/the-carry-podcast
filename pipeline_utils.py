"""
pipeline_utils.py — Shared utilities for finance_pipeline.py.
"""

import json
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

_DEFAULT_STATE: dict = {"last_alphaville_guid": "", "last_run_date": ""}


def read_state(state_path: Path) -> dict:
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT_STATE)


def write_state(state: dict, state_path: Path) -> None:
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_gir_content(gir_dir: Path, reference_date: Optional[date] = None) -> Optional[str]:
    """
    Scan gir_dir for .txt files from Monday of reference_date's week through
    reference_date (inclusive). Returns concatenated text with date headers, or None.
    """
    if reference_date is None:
        reference_date = date.today()

    week_start = reference_date - timedelta(days=reference_date.weekday())
    files: list[tuple[date, Path]] = []
    current = week_start
    while current <= reference_date:
        path = gir_dir / f"{current.isoformat()}.txt"
        if path.exists():
            files.append((current, path))
        current += timedelta(days=1)

    if not files:
        return None

    parts: list[str] = []
    for day, path in files:
        parts.append(f"=== Goldman Sachs Market Intelligence — {day.strftime('%A, %B %d, %Y')} ===")
        parts.append(path.read_text(encoding="utf-8").strip())
        parts.append("")
    return "\n\n".join(parts)


def parse_alphaville_rss(rss_text: str) -> Optional[dict]:
    """Parse FT Alphaville RSS. Returns dict with title/url/guid for latest item, or None."""
    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError:
        return None

    channel = root.find("channel")
    if channel is None:
        return None

    item = channel.find("item")
    if item is None:
        return None

    def text(tag: str) -> str:
        el = item.find(tag)
        return (el.text or "").strip() if el is not None else ""

    url = text("link")
    if not url:
        return None

    return {"title": text("title"), "url": url, "guid": text("guid") or url}
