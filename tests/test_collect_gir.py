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
