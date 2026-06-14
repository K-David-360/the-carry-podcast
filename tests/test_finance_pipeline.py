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
