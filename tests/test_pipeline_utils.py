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
