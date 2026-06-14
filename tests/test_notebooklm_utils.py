from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from notebooklm_utils import generate_podcast_audio, delete_notebook


def make_mock_client(audio_title="The Carry Trade"):
    client = AsyncMock()
    nb = MagicMock(); nb.id = "nb-test-id"
    client.notebooks.create = AsyncMock(return_value=nb)
    client.sources.add_url = AsyncMock(return_value=None)
    client.sources.add_text = AsyncMock(return_value=None)
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
        gir_content="institutional market intelligence",
        alphaville_url="https://ftav.substack.com/p/test",
        title="The Carry — Test",
        output_path=output_path,
        client=client,
    )

    assert notebook_id == "nb-test-id"
    assert audio_title == "The Carry Trade"
    client.sources.add_text.assert_called_once()
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
        gir_content="research content only",
        alphaville_url=None,
        title="The Carry — GIR Only",
        output_path=output_path,
        client=client,
    )

    client.sources.add_url.assert_not_called()
    client.sources.add_text.assert_called_once()
    client.artifacts.generate_audio.assert_called_once()


@pytest.mark.asyncio
async def test_delete_notebook_calls_delete():
    client = make_mock_client()
    await delete_notebook("nb-test-id", client=client)
    client.notebooks.delete.assert_called_once_with("nb-test-id")
