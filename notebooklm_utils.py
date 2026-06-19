"""
notebooklm_utils.py — NotebookLM audio generation for The Carry podcast.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from notebooklm import NotebookLMClient, AudioFormat, AudioLength
from notebooklm.exceptions import NetworkError

log = logging.getLogger(__name__)

AUDIO_PROMPT = """\
Host format: Two hosts — one speaks from the institutional analyst lens (data, positioning, \
model-driven views), the other from FT Alphaville's tradition (wry, skeptical of consensus, \
comfortable calling out when something is strange or overdone). Tone is dry and intelligent — \
Bloomberg Odd Lots, not CNBC. Assume a financially literate audience.

Structure:

1. Cold open (30 sec): Open with "Welcome to The Carry. We read the research so you don't have \
to — and then argue about it anyway." Then drop immediately into the most interesting tension or \
data point from this week's material — a number that surprises, a narrative that doesn't hold \
together, or a call that deserves scrutiny.

2. Research intelligence layer (3–4 min): Walk through key themes from the institutional research. \
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

        if gir_content:
            log.info("Adding GIR content (%d chars)", len(gir_content))
            await c.sources.add_text(notebook_id, "Institutional Research", gir_content, wait=True)
            log.info("GIR source added")

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

        if final is None or not final.is_complete:
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
