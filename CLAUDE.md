# The Carry Podcast — Project Reference

**Goal:** Weekly financial podcast pipeline that ingests Goldman Sachs GIR emails and FT Alphaville Substack posts, generates audio via NotebookLM, and publishes to Apple Podcasts via a GitHub Pages RSS feed.

**Architecture:** Two production scripts: `collect_gir.py` polls a dedicated Gmail inbox daily (Mon–Fri) via IMAP and saves GS email bodies as dated text files; `finance_pipeline.py` runs weekly (Friday 6:30am Central) to check Alphaville's Substack RSS, load the week's GIR files, create a NotebookLM notebook with both sources, generate audio, and publish to GitHub Pages. Mirrors the sibling `morning-brew-podcast` project's publish pattern. Runs entirely on the Raspberry Pi at `192.168.1.136` — no Mac required after initial setup.

**Tech Stack:** Python 3.11, notebooklm-py[browser], requests, beautifulsoup4, python-dotenv, imaplib (stdlib), xml.etree.ElementTree (stdlib), pytest, pytest-asyncio

---

## Source Context

**Source 1 — GS GIR emails:** Goldman Sachs GIR (Global Investment Research) daily market intelligence emails arrive from `@alerts.publishing.gs.com`. They are forwarded server-side via an iCloud Mail rule to a dedicated Gmail account. The Pi polls that Gmail via IMAP daily and saves email bodies as `gir_emails/YYYY-MM-DD.txt`.

**Source 2 — FT Alphaville Substack:** Published weekly at `https://ftav.substack.com` (usually Thursday UK morning, before 6am Central). The Substack is completely free and publicly accessible — posts can be added to NotebookLM as URLs with no auth. The RSS feed at `https://ftav.substack.com/feed` is used to detect new posts via GUID comparison against `state.json`.

**Frequency:** Weekly, Friday 6:30am Central. Alphaville posts by ~6am Central on Thursdays; by Friday morning it has been live for hours.

**Fallback logic:** If no new Alphaville post this week, run with GIR-only content. If no GIR content either, abort.

---

## File Map

| File | Role |
|------|------|
| `collect_gir.py` | Daily (Mon–Fri): IMAP → save GS email bodies as `gir_emails/YYYY-MM-DD.txt` |
| `finance_pipeline.py` | Weekly (Friday): Alphaville RSS + GIR files → NotebookLM → GitHub → feed.xml |
| `pipeline_utils.py` | Shared utilities: state management, GIR file loading, RSS parsing |
| `notebooklm_utils.py` | NotebookLM audio generation wrapper |
| `github_utils.py` | GitHub API helpers + feed.xml manipulation |
| `tests/test_collect_gir.py` | Unit tests: email parsing, file saving |
| `tests/test_pipeline_utils.py` | Unit tests: RSS parsing, state management, GIR file loading |
| `tests/test_notebooklm_utils.py` | Unit tests: NotebookLM integration (mocked) |
| `tests/test_feed_utils.py` | Unit tests: feed item creation, old item pruning |
| `tests/test_finance_pipeline.py` | Integration tests: pipeline orchestration (all external calls mocked) |
| `gir_emails/` | Daily GIR text files (gitignored) |
| `state.json` | Last-processed Alphaville GUID + last run date (gitignored) |
| `.env` | `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GITHUB_TOKEN` (gitignored) |
| `.env.example` | Template for .env |
| `pipeline.log` | Run log (gitignored) |
| `CLAUDE.md` | This file |

---

## Key Commands

```bash
# Run tests
source .venv/bin/activate
pytest tests/ -v

# Collect GIR emails manually
python collect_gir.py

# Dry-run pipeline (source check only, no side effects)
python finance_pipeline.py --dry-run

# Full pipeline run
python finance_pipeline.py
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in:

```
GMAIL_USER=your-dedicated-gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Google App Password, not account password
GITHUB_TOKEN=ghp_...
```

**Gmail IMAP:** Enable IMAP in Gmail settings. Create an App Password at Google Account → Security → App Passwords.

**iCloud forwarding rule:** icloud.com → Mail → Settings → Rules → From contains `alerts.publishing.gs.com` → Forward to `<dedicated-gmail>`.

**NotebookLM auth:** Reuses the existing `morning-brew-podcast` session (same Google account). To check: `notebooklm auth check --test --json`. To re-auth: see `morning-brew-podcast/CLAUDE.md`.

---

## GitHub / Feed

- **Repo:** `K-David-360/the-carry-podcast`
- **Pages URL:** `https://k-david-360.github.io/the-carry-podcast`
- **Feed:** `https://k-david-360.github.io/the-carry-podcast/feed.xml`
- **Retention:** 30 days (weekly show)
- Large audio files (>25 MB) bypass the GitHub REST API via shallow git clone + push.

---

## Pi Deployment

- **Host:** `192.168.1.136`, user `pi`
- **Project path:** `/home/pi/the-carry-podcast/`
- **Venv:** `/home/pi/the-carry-podcast/.venv/`
- Sibling project `morning-brew-podcast` lives at `/home/pi/morning-brew-podcast/` — read its `CLAUDE.md` for shared auth/feed patterns.

**Cron (add via `crontab -e` on Pi):**
```
TZ=America/Chicago

# Daily GIR collection (Mon–Fri 6am Central)
0 6 * * 1-5 /home/pi/the-carry-podcast/.venv/bin/python3 /home/pi/the-carry-podcast/collect_gir.py >> /home/pi/the-carry-podcast/pipeline.log 2>&1

# Weekly pipeline (Friday 6:30am Central)
30 6 * * 5 /home/pi/the-carry-podcast/.venv/bin/python3 /home/pi/the-carry-podcast/finance_pipeline.py >> /home/pi/the-carry-podcast/pipeline.log 2>&1
```

---

## Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

### Task 1: Project Scaffold

**Files:**
- Create: `.env.example`
- Create: `.gitignore`
- Create: `gir_emails/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**
```bash
mkdir -p /Users/David/Documents/Claude/the-carry-podcast/{gir_emails,tests}
touch /Users/David/Documents/Claude/the-carry-podcast/gir_emails/.gitkeep
touch /Users/David/Documents/Claude/the-carry-podcast/tests/__init__.py
```

- [ ] **Step 2: Create .env.example**
File: `.env.example`
```
GMAIL_USER=your-dedicated-gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
GITHUB_TOKEN=ghp_...
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 3: Create .gitignore**
File: `.gitignore`
```
.env
gir_emails/*.txt
state.json
pipeline.log
__pycache__/
*.pyc
.venv/
*.raw
```

- [ ] **Step 4: Create Python venv and install dependencies**
```bash
cd /Users/David/Documents/Claude/the-carry-podcast
python3.11 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 python-dotenv "notebooklm-py[browser]" mutagen anthropic pytest pytest-asyncio
```

- [ ] **Step 5: Verify imports**
```bash
source .venv/bin/activate
python -c "import requests, bs4, dotenv, notebooklm, mutagen, anthropic; print('OK')"
```
Expected output: `OK`

- [ ] **Step 6: Initialize git and commit**
```bash
git init
git add .gitignore .env.example gir_emails/.gitkeep tests/__init__.py
git commit -m "chore: project scaffold for the-carry-podcast"
```

---

### Task 2: GIR Email Collection (`collect_gir.py`)

**Files:**
- Create: `collect_gir.py`
- Create: `tests/test_collect_gir.py`

**What this does:** Connect to Gmail IMAP (`imap.gmail.com:993`), search for UNSEEN messages from `alerts.publishing.gs.com`, extract plain-text body (stripping HTML if needed), save as `gir_emails/YYYY-MM-DD.txt` (appending if multiple emails arrive on the same day), mark messages as read.

- [ ] **Step 1: Write failing tests**
File: `tests/test_collect_gir.py`
```python
import email
import email.mime.multipart
import email.mime.text
import email.message
from pathlib import Path
import tempfile
import pytest

from collect_gir import extract_body, get_email_date, save_email


def make_plain_email(body: str, date_str: str = "Thu, 11 Jun 2026 06:00:00 +0000") -> email.message.Message:
    msg = email.message.EmailMessage()
    msg["From"] = "noreply@alerts.publishing.gs.com"
    msg["Subject"] = "GS Market Intelligence"
    msg["Date"] = date_str
    msg.set_content(body)
    return msg


def make_html_email(html: str, date_str: str = "Thu, 11 Jun 2026 06:00:00 +0000") -> email.message.Message:
    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["From"] = "noreply@alerts.publishing.gs.com"
    msg["Subject"] = "GS Market Intelligence"
    msg["Date"] = date_str
    msg.attach(email.mime.text.MIMEText(html, "html"))
    return msg


def test_extract_body_plain_text():
    msg = make_plain_email("US equities rose 1.2% on strong NFP data.")
    assert "US equities rose 1.2%" in extract_body(msg)


def test_extract_body_html_strips_tags():
    msg = make_html_email("<html><body><p>Oil markets <b>rallied</b> on inventory draw.</p></body></html>")
    body = extract_body(msg)
    assert "Oil markets" in body
    assert "rallied" in body
    assert "<b>" not in body


def test_extract_body_multipart_prefers_plain():
    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg.attach(email.mime.text.MIMEText("Plain text version", "plain"))
    msg.attach(email.mime.text.MIMEText("<b>HTML version</b>", "html"))
    assert extract_body(msg).strip() == "Plain text version"


def test_get_email_date_parses_date_header():
    msg = make_plain_email("content", date_str="Thu, 11 Jun 2026 06:00:00 +0000")
    assert get_email_date(msg) == "2026-06-11"


def test_get_email_date_falls_back_to_today_on_bad_header():
    from datetime import datetime, timezone
    msg = make_plain_email("content")
    msg.replace_header("Date", "not-a-date")
    result = get_email_date(msg)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    assert result == today


def test_save_email_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        gir_dir = Path(tmpdir)
        save_email("2026-06-11", "US equities content", gir_dir)
        f = gir_dir / "2026-06-11.txt"
        assert f.exists()
        assert "US equities content" in f.read_text()


def test_save_email_appends_on_same_day():
    with tempfile.TemporaryDirectory() as tmpdir:
        gir_dir = Path(tmpdir)
        save_email("2026-06-11", "First email", gir_dir)
        save_email("2026-06-11", "Second email", gir_dir)
        content = (gir_dir / "2026-06-11.txt").read_text()
        assert "First email" in content
        assert "Second email" in content


def test_save_email_different_days_separate_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        gir_dir = Path(tmpdir)
        save_email("2026-06-09", "Monday content", gir_dir)
        save_email("2026-06-10", "Tuesday content", gir_dir)
        assert (gir_dir / "2026-06-09.txt").exists()
        assert (gir_dir / "2026-06-10.txt").exists()
        assert "Tuesday content" not in (gir_dir / "2026-06-09.txt").read_text()
```

- [ ] **Step 2: Run tests to confirm they fail**
```bash
cd /Users/David/Documents/Claude/the-carry-podcast
source .venv/bin/activate
pytest tests/test_collect_gir.py -v
```
Expected: `ImportError` — `collect_gir.py` does not exist yet.

- [ ] **Step 3: Implement collect_gir.py**
File: `collect_gir.py`
```python
#!/usr/bin/env python3
"""
collect_gir.py — Daily GIR email collector.

Polls a dedicated Gmail inbox via IMAP for unread messages from
@alerts.publishing.gs.com, extracts the text body, and saves each as
gir_emails/YYYY-MM-DD.txt (appending if multiple arrive on the same day).

Usage:
    python collect_gir.py

Cron (Pi, Mon–Fri 6am Central, set TZ=America/Chicago in crontab):
    0 6 * * 1-5 /home/pi/the-carry-podcast/.venv/bin/python3 \
        /home/pi/the-carry-podcast/collect_gir.py >> \
        /home/pi/the-carry-podcast/pipeline.log 2>&1
"""

import email
import email.message
import imaplib
import logging
import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GIR_SENDER_DOMAIN = "alerts.publishing.gs.com"
GIR_EMAIL_DIR = Path(__file__).parent / "gir_emails"
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

LOG_FILE = Path(__file__).parent / "pipeline.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
log = logging.getLogger(__name__)


def extract_body(msg: email.message.Message) -> str:
    """Extract plain text from an email, stripping HTML if no plain-text part exists."""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if "attachment" in str(part.get("Content-Disposition", "")):
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ct == "text/plain":
                plain_parts.append(text)
            elif ct == "text/html":
                html_parts.append(text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html_parts.append(text)
            else:
                plain_parts.append(text)

    if plain_parts:
        return "\n\n".join(plain_parts).strip()
    if html_parts:
        return BeautifulSoup("\n\n".join(html_parts), "html.parser").get_text(
            separator="\n", strip=True
        )
    return ""


def get_email_date(msg: email.message.Message) -> str:
    """Return YYYY-MM-DD from email Date header, falling back to today (UTC)."""
    try:
        return parsedate_to_datetime(msg.get("Date", "")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def save_email(date_str: str, body: str, gir_dir: Path) -> None:
    """Save or append email body to gir_dir/YYYY-MM-DD.txt."""
    gir_dir.mkdir(parents=True, exist_ok=True)
    path = gir_dir / f"{date_str}.txt"
    separator = "\n\n--- (additional message) ---\n\n" if path.exists() else ""
    with open(path, "a", encoding="utf-8") as f:
        f.write(separator + body)
    log.info("Saved GIR email for %s (%d chars) → %s", date_str, len(body), path.name)


def collect_gir_emails(
    imap_host: str = IMAP_HOST,
    imap_port: int = IMAP_PORT,
    gmail_user: str = GMAIL_USER,
    gmail_password: str = GMAIL_APP_PASSWORD,
    gir_dir: Path = GIR_EMAIL_DIR,
) -> int:
    """Connect to Gmail IMAP, fetch unseen GS emails, save to gir_dir. Returns count saved."""
    if not gmail_user or not gmail_password:
        raise RuntimeError("GMAIL_USER and GMAIL_APP_PASSWORD must be set in .env")

    log.info("Connecting to %s:%d as %s", imap_host, imap_port, gmail_user)
    mail = imaplib.IMAP4_SSL(imap_host, imap_port)
    mail.login(gmail_user, gmail_password)

    try:
        mail.select("INBOX")
        status, message_ids = mail.search(None, f'(UNSEEN FROM "{GIR_SENDER_DOMAIN}")')
        if status != "OK":
            log.warning("IMAP search returned non-OK status: %s", status)
            return 0

        ids = [i for i in message_ids[0].split() if i]
        log.info("Found %d unseen GIR message(s)", len(ids))

        saved = 0
        for msg_id in ids:
            fetch_status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if fetch_status != "OK" or not msg_data or not msg_data[0]:
                log.warning("Failed to fetch message %s", msg_id)
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            body = extract_body(msg)

            if not body:
                log.warning("Empty body for message %s, skipping", msg_id)
                mail.store(msg_id, "+FLAGS", "\\Seen")
                continue

            date_str = get_email_date(msg)
            subject = msg.get("Subject", "(no subject)")
            log.info("Processing: %s [%s]", subject[:80], date_str)

            save_email(date_str, body, gir_dir)
            mail.store(msg_id, "+FLAGS", "\\Seen")
            saved += 1

        return saved

    finally:
        mail.logout()


def main() -> None:
    log.info("=" * 50)
    log.info("collect_gir.py starting")
    log.info("=" * 50)
    try:
        count = collect_gir_emails()
        log.info("Done. Saved %d GIR email(s).", count)
    except Exception as exc:
        log.error("collect_gir failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect all 8 to pass**
```bash
pytest tests/test_collect_gir.py -v
```
Expected: 8 PASSED, 0 failed.

- [ ] **Step 5: Commit**
```bash
git add collect_gir.py tests/test_collect_gir.py
git commit -m "feat: add GIR email collector (IMAP + body extraction)"
```

---

### Task 3: Data Loading Utilities (`pipeline_utils.py`)

**Files:**
- Create: `pipeline_utils.py`
- Create: `tests/test_pipeline_utils.py`

**What this provides:** (1) `read_state`/`write_state` for `state.json`, (2) `load_gir_content` scans this week's files and concatenates, (3) `parse_alphaville_rss` extracts the latest post from feed XML.

- [ ] **Step 1: Write failing tests**
File: `tests/test_pipeline_utils.py`
```python
import json
import tempfile
from datetime import date
from pathlib import Path
import pytest

from pipeline_utils import read_state, write_state, load_gir_content, parse_alphaville_rss


def test_read_state_missing_file_returns_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        state = read_state(Path(tmpdir) / "state.json")
        assert state["last_alphaville_guid"] == ""
        assert state["last_run_date"] == ""


def test_write_then_read_state_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "state.json"
        write_state({"last_alphaville_guid": "abc123", "last_run_date": "2026-06-11"}, path)
        state = read_state(path)
        assert state["last_alphaville_guid"] == "abc123"
        assert state["last_run_date"] == "2026-06-11"


def test_load_gir_content_returns_none_when_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        assert load_gir_content(Path(tmpdir), reference_date=date(2026, 6, 13)) is None


def test_load_gir_content_combines_files_in_date_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        gir_dir = Path(tmpdir)
        (gir_dir / "2026-06-08.txt").write_text("Monday content")
        (gir_dir / "2026-06-09.txt").write_text("Tuesday content")
        result = load_gir_content(gir_dir, reference_date=date(2026, 6, 13))
        assert result is not None
        assert "Monday content" in result
        assert "Tuesday content" in result
        assert result.index("Monday content") < result.index("Tuesday content")


def test_load_gir_content_ignores_prior_week():
    with tempfile.TemporaryDirectory() as tmpdir:
        gir_dir = Path(tmpdir)
        (gir_dir / "2026-06-01.txt").write_text("Last week content")
        (gir_dir / "2026-06-08.txt").write_text("This week content")
        result = load_gir_content(gir_dir, reference_date=date(2026, 6, 13))
        assert "Last week content" not in result
        assert "This week content" in result


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>FT Alphaville</title>
    <item>
      <title>The big quant convergence</title>
      <link>https://ftav.substack.com/p/the-big-quant-convergence</link>
      <guid>https://ftav.substack.com/p/the-big-quant-convergence</guid>
      <pubDate>Thu, 29 May 2026 09:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Old post</title>
      <link>https://ftav.substack.com/p/old-post</link>
      <guid>https://ftav.substack.com/p/old-post</guid>
      <pubDate>Thu, 22 May 2026 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def test_parse_alphaville_rss_returns_latest_item():
    item = parse_alphaville_rss(SAMPLE_RSS)
    assert item["title"] == "The big quant convergence"
    assert item["url"] == "https://ftav.substack.com/p/the-big-quant-convergence"
    assert item["guid"] == "https://ftav.substack.com/p/the-big-quant-convergence"


def test_parse_alphaville_rss_empty_feed_returns_none():
    assert parse_alphaville_rss('<?xml version="1.0"?><rss><channel></channel></rss>') is None


def test_parse_alphaville_rss_malformed_returns_none():
    assert parse_alphaville_rss("not xml at all") is None
```

- [ ] **Step 2: Run tests to confirm they fail**
```bash
pytest tests/test_pipeline_utils.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement pipeline_utils.py**
File: `pipeline_utils.py`
```python
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
```

- [ ] **Step 4: Run tests — expect all 9 to pass**
```bash
pytest tests/test_pipeline_utils.py -v
```
Expected: 9 PASSED.

- [ ] **Step 5: Commit**
```bash
git add pipeline_utils.py tests/test_pipeline_utils.py
git commit -m "feat: add pipeline utilities (state, GIR loading, RSS parsing)"
```

---

### Task 4: NotebookLM Integration (`notebooklm_utils.py`)

**Files:**
- Create: `notebooklm_utils.py`
- Create: `tests/test_notebooklm_utils.py`

**IMPORTANT — verify add_file API before coding.** Run:
```bash
source .venv/bin/activate
python -c "import notebooklm.sources as s; print([m for m in dir(s) if not m.startswith('_')])"
```
If `add_text` or `add_paste` exists, use it instead of the `add_file` + temp file approach below (simpler — skip the NamedTemporaryFile step). The implementation uses `add_file` with a temp `.txt` as the safe fallback.

- [ ] **Step 1: Write failing tests**
File: `tests/test_notebooklm_utils.py`
```python
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from notebooklm_utils import generate_podcast_audio, delete_notebook


def make_mock_client(audio_title="The Carry Trade"):
    client = AsyncMock()
    nb = MagicMock(); nb.id = "nb-test-id"
    client.notebooks.create = AsyncMock(return_value=nb)
    client.sources.add_url = AsyncMock(return_value=None)
    client.sources.add_file = AsyncMock(return_value=None)
    status = MagicMock(); status.task_id = "task-123"
    client.artifacts.generate_audio = AsyncMock(return_value=status)
    completion = MagicMock(); completion.is_complete = True; completion.status = "complete"
    client.artifacts.wait_for_completion = AsyncMock(return_value=completion)
    artifact = MagicMock(); artifact.title = audio_title
    client.artifacts.list_audio = AsyncMock(return_value=[artifact])
    client.artifacts.download_audio = AsyncMock(return_value=None)
    client.notebooks.delete = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_generate_audio_adds_both_sources(tmp_path):
    client = make_mock_client()
    output_path = tmp_path / "audio.raw"
    output_path.write_bytes(b"fake")

    audio_title, notebook_id = await generate_podcast_audio(
        gir_content="GS market intelligence",
        alphaville_url="https://ftav.substack.com/p/test",
        title="The Carry — Test",
        output_path=output_path,
        client=client,
    )

    assert notebook_id == "nb-test-id"
    assert audio_title == "The Carry Trade"
    client.sources.add_file.assert_called_once()
    client.sources.add_url.assert_called_once_with(
        "nb-test-id", "https://ftav.substack.com/p/test", wait=True
    )
    client.artifacts.generate_audio.assert_called_once()


@pytest.mark.asyncio
async def test_generate_audio_gir_only_skips_add_url(tmp_path):
    client = make_mock_client()
    output_path = tmp_path / "audio.raw"
    output_path.write_bytes(b"fake")

    await generate_podcast_audio(
        gir_content="GS content only",
        alphaville_url=None,
        title="The Carry — GIR Only",
        output_path=output_path,
        client=client,
    )

    client.sources.add_url.assert_not_called()
    client.sources.add_file.assert_called_once()
    client.artifacts.generate_audio.assert_called_once()


@pytest.mark.asyncio
async def test_delete_notebook_calls_delete():
    client = make_mock_client()
    await delete_notebook("nb-test-id", client=client)
    client.notebooks.delete.assert_called_once_with("nb-test-id")
```

- [ ] **Step 2: Run tests to confirm they fail**
```bash
pytest tests/test_notebooklm_utils.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement notebooklm_utils.py**
File: `notebooklm_utils.py`
```python
"""
notebooklm_utils.py — NotebookLM audio generation for The Carry podcast.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

from notebooklm import NotebookLMClient, AudioFormat, AudioLength
from notebooklm.exceptions import NetworkError

log = logging.getLogger(__name__)

AUDIO_PROMPT = """\
Host format: Two hosts — one speaks from the Goldman Sachs analyst lens (data, positioning, \
model-driven views), the other from FT Alphaville's tradition (wry, skeptical of consensus, \
comfortable calling out when something is strange or overdone). Tone is dry and intelligent — \
Bloomberg Odd Lots, not CNBC. Assume a financially literate audience.

Structure:

1. Cold open (30 sec): Drop into the most interesting tension or data point from this week's \
material — a number that surprises, a narrative that doesn't hold together, or a call that \
deserves scrutiny. No "welcome to" boilerplate.

2. GS intelligence layer (3–4 min): Walk through key themes from the Goldman Sachs research. \
One host presents the data-driven view. The other probes: what's the model missing? What's the \
consensus, and why might it be wrong?

3. Alphaville lens (2–3 min, include only if Alphaville content is present in the sources): \
Surface the best story or observation from the week. What is Alphaville noticing that mainstream \
coverage isn't? What's the wry observation buried in the data?

4. Synthesis (2 min): Where do the two views converge or diverge? What does it mean for the week \
ahead — positioning, risk, what to watch?

5. Close (30 sec): One clean, non-hedged take on the single most important thing from this week's \
material. No "thanks for listening" filler.

Style rules:
* Dry wit is encouraged — these are people who find basis trades genuinely interesting.
* When the data is weird, say it's weird. Do not normalize everything.
* Short sentences. No jargon without a quick definition.
* The hosts should occasionally disagree — not for drama, but because smart people reading the \
same data sometimes do.\
"""


class _DirectClient:
    """No-op async context manager for injecting a client in tests."""
    def __init__(self, client):
        self._client = client
    async def __aenter__(self):
        return self._client
    async def __aexit__(self, *a):
        pass


async def generate_podcast_audio(
    gir_content: str,
    alphaville_url: Optional[str],
    title: str,
    output_path: Path,
    client=None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Create NotebookLM notebook, add GIR content + optional Alphaville URL,
    generate audio, download to output_path. Returns (audio_title, notebook_id).
    """
    MAX_RETRIES = 5
    RETRY_BACKOFF = [30, 60, 120, 180, 300]

    context = _DirectClient(client) if client is not None else await NotebookLMClient.from_storage()

    async with context as c:
        log.info("Creating notebook: %s", title)
        nb = await c.notebooks.create(title)
        notebook_id = nb.id
        log.info("Notebook created: %s", notebook_id)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(gir_content)
            tmp_path = Path(tmp.name)

        try:
            log.info("Adding GIR content (%d chars)", len(gir_content))
            await c.sources.add_file(notebook_id, str(tmp_path), wait=True)
            log.info("GIR source added")
        finally:
            tmp_path.unlink(missing_ok=True)

        if alphaville_url:
            log.info("Adding Alphaville URL: %s", alphaville_url)
            await c.sources.add_url(notebook_id, alphaville_url, wait=True)
            log.info("Alphaville source added")

        log.info("Generating audio...")
        status = await c.artifacts.generate_audio(
            notebook_id,
            instructions=AUDIO_PROMPT,
            audio_format=AudioFormat.DEEP_DIVE,
            audio_length=AudioLength.DEFAULT,
            language="en",
        )

        if not status.task_id:
            raise RuntimeError(f"Audio rejected: {getattr(status, 'error', 'unknown')}")

        log.info("Audio started (task_id: %s)", status.task_id)

        final = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                final = await c.artifacts.wait_for_completion(
                    notebook_id, status.task_id, timeout=1200, initial_interval=15
                )
                break
            except NetworkError as exc:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"Network error after {MAX_RETRIES} retries: {exc}") from exc
                wait = RETRY_BACKOFF[attempt]
                log.warning("Network error (%d/%d), retry in %ds: %s",
                            attempt + 1, MAX_RETRIES, wait, exc)
                await asyncio.sleep(wait)

        if not final.is_complete:
            raise RuntimeError(f"Audio did not complete. Status: {final.status}")

        log.info("Audio generation complete")

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

        return audio_title, notebook_id


async def delete_notebook(notebook_id: str, client=None) -> None:
    context = _DirectClient(client) if client is not None else await NotebookLMClient.from_storage()
    async with context as c:
        log.info("Deleting notebook %s", notebook_id)
        await c.notebooks.delete(notebook_id)
        log.info("Notebook deleted")
```

- [ ] **Step 4: Run tests — expect all 3 to pass**
```bash
pytest tests/test_notebooklm_utils.py -v
```
Expected: 3 PASSED.

- [ ] **Step 5: Commit**
```bash
git add notebooklm_utils.py tests/test_notebooklm_utils.py
git commit -m "feat: add NotebookLM audio generation utilities"
```

---

### Task 5: GitHub + Feed Utilities (`github_utils.py`)

**Files:**
- Create: `github_utils.py`
- Create: `tests/test_feed_utils.py`

**Note:** Adapted directly from `morning-brew-podcast/pipeline.py`. Retention is 30 days (weekly show, vs. 7 days for the daily morning-brew).

- [ ] **Step 1: Write failing tests**
File: `tests/test_feed_utils.py`
```python
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import pytest

from github_utils import build_item, remove_old_items

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)


def make_channel(pub_dates: list) -> ET.Element:
    from email.utils import format_datetime
    channel = ET.Element("channel")
    for dt in pub_dates:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "Test episode"
        enc = ET.SubElement(item, "enclosure")
        enc.set("url", "https://example.com/audio/test.m4a")
        enc.set("length", "1000")
        enc.set("type", "audio/mp4")
        ET.SubElement(item, "guid").text = "test-guid"
        ET.SubElement(item, "pubDate").text = format_datetime(dt)
    return channel


def test_build_item_has_required_fields():
    pub_date = datetime(2026, 6, 13, 6, 30, 0, tzinfo=timezone.utc)
    item = build_item(
        title="The Carry: Torque is cheap",
        description="Markets this week",
        audio_url="https://example.com/audio/2026-06-13.m4a",
        file_size=12345678,
        guid="the-carry-2026-06-13",
        pub_date=pub_date,
        duration="00:21:14",
    )
    assert item.find("title").text == "The Carry: Torque is cheap"
    assert item.find("enclosure").get("length") == "12345678"
    assert item.find("guid").text == "the-carry-2026-06-13"
    assert item.find(f"{{{ITUNES_NS}}}duration").text == "00:21:14"
    assert item.find("description").text == "Markets this week"


def test_remove_old_items_removes_expired():
    now = datetime.now(tz=timezone.utc)
    channel = make_channel([now - timedelta(days=3), now - timedelta(days=35)])
    assert len(channel.findall("item")) == 2
    stale = remove_old_items(channel, now - timedelta(days=30))
    assert len(channel.findall("item")) == 1
    assert len(stale) == 1


def test_remove_old_items_keeps_recent():
    now = datetime.now(tz=timezone.utc)
    channel = make_channel([now - timedelta(days=7), now - timedelta(days=14)])
    stale = remove_old_items(channel, now - timedelta(days=30))
    assert len(channel.findall("item")) == 2
    assert stale == []
```

- [ ] **Step 2: Run tests to confirm they fail**
```bash
pytest tests/test_feed_utils.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement github_utils.py**
File: `github_utils.py`
```python
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
```

- [ ] **Step 4: Run full test suite**
```bash
pytest tests/ -v
```
Expected: all tests PASS, 0 failures.

- [ ] **Step 5: Commit**
```bash
git add github_utils.py tests/test_feed_utils.py
git commit -m "feat: add GitHub API and feed.xml utilities"
```

---

### Task 6: Main Pipeline (`finance_pipeline.py`)

**Files:**
- Create: `finance_pipeline.py`
- Create: `tests/test_finance_pipeline.py`

- [ ] **Step 1: Write failing integration tests**
File: `tests/test_finance_pipeline.py`
```python
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch
import pytest

from finance_pipeline import run_pipeline, load_env_config


def test_load_env_config_raises_without_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        load_env_config()


def test_run_pipeline_aborts_when_no_content(tmp_path):
    """No GIR + no Alphaville → False."""
    gir_dir = tmp_path / "gir_emails"; gir_dir.mkdir()
    state_path = tmp_path / "state.json"
    with patch("finance_pipeline.fetch_alphaville_rss", return_value=None), \
         patch("finance_pipeline.GIR_EMAIL_DIR", gir_dir), \
         patch("finance_pipeline.STATE_PATH", state_path):
        assert run_pipeline(dry_run=True) is False


def test_run_pipeline_dry_run_both_sources(tmp_path):
    """GIR + new Alphaville → True."""
    gir_dir = tmp_path / "gir_emails"; gir_dir.mkdir()
    (gir_dir / f"{date.today().isoformat()}.txt").write_text("GS content")
    state_path = tmp_path / "state.json"
    alphaville = {"title": "Torque is cheap",
                  "url": "https://ftav.substack.com/p/torque-is-cheap",
                  "guid": "https://ftav.substack.com/p/torque-is-cheap"}
    with patch("finance_pipeline.fetch_alphaville_rss", return_value=alphaville), \
         patch("finance_pipeline.GIR_EMAIL_DIR", gir_dir), \
         patch("finance_pipeline.STATE_PATH", state_path):
        assert run_pipeline(dry_run=True) is True


def test_run_pipeline_dry_run_gir_only(tmp_path):
    """GIR + no Alphaville → True (GIR-only episode)."""
    gir_dir = tmp_path / "gir_emails"; gir_dir.mkdir()
    (gir_dir / f"{date.today().isoformat()}.txt").write_text("GS content")
    state_path = tmp_path / "state.json"
    with patch("finance_pipeline.fetch_alphaville_rss", return_value=None), \
         patch("finance_pipeline.GIR_EMAIL_DIR", gir_dir), \
         patch("finance_pipeline.STATE_PATH", state_path):
        assert run_pipeline(dry_run=True) is True
```

- [ ] **Step 2: Run tests to confirm they fail**
```bash
pytest tests/test_finance_pipeline.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement finance_pipeline.py**
File: `finance_pipeline.py`
```python
#!/usr/bin/env python3
"""
finance_pipeline.py — Weekly "The Carry" podcast pipeline.

1. Check FT Alphaville Substack RSS for a new post this week
2. Load this week's GIR email files
3. Create NotebookLM notebook with both sources (or GIR-only)
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
        episode_title = f"The Carry — GS Intelligence {date_str}"
        description = f"Goldman Sachs market intelligence. Week of {date_str}."

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
```

- [ ] **Step 4: Run full test suite**
```bash
pytest tests/ -v
```
Expected: all tests PASS, 0 failures.

- [ ] **Step 5: Commit**
```bash
git add finance_pipeline.py tests/test_finance_pipeline.py
git commit -m "feat: add main finance_pipeline.py orchestration"
```

---

### Task 7: Initial GitHub Repo + feed.xml

One-time infrastructure. No code to write.

- [ ] **Step 1: Create GitHub repo**
Go to https://github.com/new — Name: `the-carry-podcast`, Owner: `K-David-360`, Public, no README.

- [ ] **Step 2: Enable GitHub Pages**
Repo Settings → Pages → Source: `Deploy from a branch` → `main` / `/ (root)` → Save.

- [ ] **Step 3: Push local repo**
```bash
cd /Users/David/Documents/Claude/the-carry-podcast
git remote add origin https://github.com/K-David-360/the-carry-podcast.git
git branch -M main
git push -u origin main
```

- [ ] **Step 4: Create .env**
```bash
cp .env.example .env
# Fill in: GMAIL_USER, GMAIL_APP_PASSWORD, GITHUB_TOKEN
```

- [ ] **Step 5: Push initial feed.xml**
```bash
source .venv/bin/activate
python - << 'EOF'
import os; os.chdir("/Users/David/Documents/Claude/the-carry-podcast")
from dotenv import load_dotenv; load_dotenv(".env")
from github_utils import gh_put_file

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The Carry</title>
    <description>Goldman Sachs research intelligence meets FT Alphaville. Weekly financial analysis with a dry wit.</description>
    <link>https://k-david-360.github.io/the-carry-podcast/</link>
    <language>en-us</language>
    <atom:link href="https://k-david-360.github.io/the-carry-podcast/feed.xml" rel="self" type="application/rss+xml"/>
    <itunes:author>The Carry</itunes:author>
    <itunes:category text="Business">
      <itunes:category text="Investing"/>
    </itunes:category>
    <itunes:explicit>no</itunes:explicit>
  </channel>
</rss>"""

gh_put_file("feed.xml", FEED, "chore: initial feed.xml")
print("feed.xml pushed")
EOF
```

- [ ] **Step 6: Verify feed is live (allow 3–5 min for Pages to deploy)**
```bash
curl -s https://k-david-360.github.io/the-carry-podcast/feed.xml | head -5
```
Expected: `<?xml version="1.0" encoding="UTF-8"?>`

---

### Task 8: Pi Deployment + Cron

- [ ] **Step 1: SSH into Pi and clone**
```bash
ssh pi@192.168.1.136
git clone https://github.com/K-David-360/the-carry-podcast.git ~/the-carry-podcast
cd ~/the-carry-podcast
```

- [ ] **Step 2: Create venv and install deps**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 python-dotenv "notebooklm-py[browser]" mutagen anthropic pytest pytest-asyncio
```

- [ ] **Step 3: Copy .env from Mac**
```bash
# Run on Mac:
scp /Users/David/Documents/Claude/the-carry-podcast/.env pi@192.168.1.136:~/the-carry-podcast/.env
```

- [ ] **Step 4: Verify NotebookLM auth**
```bash
# On Pi:
/home/pi/the-carry-podcast/.venv/bin/notebooklm auth check --test --json
```
Expected: `{"status": "ok", ...}`
If it fails: re-run `notebooklm login` on Mac and re-copy per morning-brew SOP in `morning-brew-podcast/CLAUDE.md`.

- [ ] **Step 5: Test collect_gir.py**
(Ensure at least one GS email has been forwarded to the dedicated Gmail first.)
```bash
cd ~/the-carry-podcast && source .venv/bin/activate
python collect_gir.py
tail -10 pipeline.log
```
Expected: `Saved GIR email for YYYY-MM-DD (N chars)` or `Found 0 unseen GIR message(s)`

- [ ] **Step 6: Test finance_pipeline.py dry run**
```bash
python finance_pipeline.py --dry-run
tail -15 pipeline.log
```
Expected: log ends with `Dry-run — stopping here. Sources: GIR=True/False, Alphaville=...`

- [ ] **Step 7: Install cron jobs**
```bash
crontab -e
```
Add:
```
TZ=America/Chicago

# The Carry — daily GIR collection (Mon–Fri 6am Central)
0 6 * * 1-5 /home/pi/the-carry-podcast/.venv/bin/python3 /home/pi/the-carry-podcast/collect_gir.py >> /home/pi/the-carry-podcast/pipeline.log 2>&1

# The Carry — weekly pipeline (Friday 6:30am Central)
30 6 * * 5 /home/pi/the-carry-podcast/.venv/bin/python3 /home/pi/the-carry-podcast/finance_pipeline.py >> /home/pi/the-carry-podcast/pipeline.log 2>&1
```

- [ ] **Step 8: Verify cron**
```bash
crontab -l | grep the-carry
```
Expected: both lines appear.

- [ ] **Step 9: One-time Gmail + iCloud setup**
1. Create dedicated Gmail. Enable IMAP: Gmail Settings → Forwarding and POP/IMAP → Enable IMAP → Save.
2. Create App Password: Google Account → Security → App Passwords → name "GIR Pipeline Pi" → add to `.env` as `GMAIL_APP_PASSWORD`.
3. iCloud forwarding rule: icloud.com → Mail → Settings → Rules → Add Rule → From contains `alerts.publishing.gs.com` → Forward to `<dedicated-gmail>` → Done.

---

## Self-Review

**Spec coverage:**
- ✅ GIR emails collected via IMAP from dedicated Gmail (no main credentials touched)
- ✅ iCloud server-side rule forwards GS emails (no device needs to be on)
- ✅ FT Alphaville Substack RSS polled weekly, deduped via GUID in state.json
- ✅ GIR-only fallback when no new Alphaville post
- ✅ Abort cleanly when no content from either source
- ✅ NotebookLM: two sources, one `generate_audio()` call
- ✅ GitHub Pages RSS publish with 30-day retention
- ✅ Pi deployment, fully automated cron (no Mac required)
- ✅ Audio prompt: Bloomberg Odd Lots / FT Alphaville tone, data-literate, dry wit

**Placeholder scan:** None. All code is complete and runnable.

**Type consistency:** `generate_podcast_audio(gir_content, alphaville_url, title, output_path, client)` is consistent across `notebooklm_utils.py`, its tests, and calls in `finance_pipeline.py`. `build_item`/`remove_old_items` match between `github_utils.py` and `test_feed_utils.py`.

---

## Execution Handoff

- **Subagent-Driven (recommended):** Invoke `superpowers:subagent-driven-development` — fresh subagent per task, review between tasks.
- **Inline Execution:** Invoke `superpowers:executing-plans` — batch execution with checkpoints.
