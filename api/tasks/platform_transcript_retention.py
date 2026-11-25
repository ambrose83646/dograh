"""Timed deletion of the words of old calls (platform mode only)."""

from datetime import timedelta

from api.services.platform import transcript_retention
from api.services.platform.settings import get_platform_settings


async def sweep_old_transcripts(_ctx) -> None:
    settings = get_platform_settings()
    if settings.enabled:
        await transcript_retention.delete_old(timedelta(days=settings.transcript_days))
