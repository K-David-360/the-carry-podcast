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
