#!/usr/bin/env python3
"""
collect_gir.py — Daily research email collector.

Polls a dedicated Gmail inbox via IMAP for unread messages from
the configured research sender domain, extracts the text body, and saves each as
research_emails/YYYY-MM-DD.txt (appending if multiple arrive on the same day).

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
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GIR_SENDER_DOMAIN = "alerts.publishing.gs.com"
GIR_EMAIL_DIR = Path(__file__).parent / "gir_emails"
STATE_FILE = Path(__file__).parent / "state.json"
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


def _load_seen_ids() -> set:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text())
        return set(data.get("seen_gir_message_ids", []))
    return set()


def _save_seen_ids(seen: set) -> None:
    data = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    data["seen_gir_message_ids"] = sorted(seen)
    STATE_FILE.write_text(json.dumps(data, indent=2))


def _get_consecutive_failures() -> int:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("gir_consecutive_failures", 0)
    return 0


def _set_consecutive_failures(n: int) -> None:
    data = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    data["gir_consecutive_failures"] = n
    STATE_FILE.write_text(json.dumps(data, indent=2))


def collect_gir_emails(
    imap_host: str = IMAP_HOST,
    imap_port: int = IMAP_PORT,
    gmail_user: str = GMAIL_USER,
    gmail_password: str = GMAIL_APP_PASSWORD,
    gir_dir: Path = GIR_EMAIL_DIR,
) -> int:
    """Connect to Gmail IMAP, fetch new research emails, save to gir_dir. Returns count saved."""
    if not gmail_user or not gmail_password:
        raise RuntimeError("GMAIL_USER and GMAIL_APP_PASSWORD must be set in .env")

    seen_ids = _load_seen_ids()

    log.info("Connecting to %s:%d as %s", imap_host, imap_port, gmail_user)
    mail = imaplib.IMAP4_SSL(imap_host, imap_port)
    mail.login(gmail_user, gmail_password)

    try:
        mail.select("INBOX")
        # Search only the past 7 days — Gmail marks auto-forwarded emails as read so
        # we can't use UNSEEN; seen_ids deduplication handles skipping already-processed mail.
        since = (datetime.now(tz=timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
        status, message_ids = mail.search(None, f'(FROM "{GIR_SENDER_DOMAIN}" SINCE {since})')
        if status != "OK":
            log.warning("IMAP search returned non-OK status: %s", status)
            return 0

        ids = [i for i in message_ids[0].split() if i]
        log.info("Found %d total GIR message(s) in inbox", len(ids))

        saved = 0
        for msg_id in ids:
            fetch_status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if fetch_status != "OK" or not msg_data or not msg_data[0]:
                log.warning("Failed to fetch message %s", msg_id)
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            message_id = msg.get("Message-ID", "").strip()

            if message_id and message_id in seen_ids:
                log.info("Already processed Message-ID %s, skipping", message_id[:60])
                continue

            body = extract_body(msg)

            if not body:
                log.warning("Empty body for message %s, skipping", msg_id)
                if message_id:
                    seen_ids.add(message_id)
                continue

            date_str = get_email_date(msg)
            subject = msg.get("Subject", "(no subject)")
            log.info("Processing: %s [%s]", subject[:80], date_str)

            save_email(date_str, body, gir_dir)
            if message_id:
                seen_ids.add(message_id)
            saved += 1

        _save_seen_ids(seen_ids)
        return saved

    finally:
        mail.logout()


def main() -> None:
    log.info("=" * 50)
    log.info("collect_gir.py starting")
    log.info("=" * 50)
    try:
        count = collect_gir_emails()
        _set_consecutive_failures(0)
        log.info("Done. Saved %d GIR email(s).", count)
    except Exception as exc:
        failures = _get_consecutive_failures() + 1
        _set_consecutive_failures(failures)
        log.error("collect_gir failed: %s", exc, exc_info=True)
        if failures >= 3:
            log.critical(
                "ACTION REQUIRED: collect_gir has failed %d consecutive times. "
                "Check that the Gmail App Password for %s is still valid — "
                "it may need to be regenerated at myaccount.google.com.",
                failures,
                GMAIL_USER,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
