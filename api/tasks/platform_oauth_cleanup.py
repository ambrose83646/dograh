"""Timed clean-up of OAuth accounts that nobody uses (platform mode only)."""

from datetime import timedelta

from api.services.platform import oauth_accounts
from api.services.platform.settings import get_platform_settings


async def sweep_unused_oauth_accounts(_ctx) -> None:
    settings = get_platform_settings()
    if settings.enabled:
        await oauth_accounts.clean_up(timedelta(hours=settings.oauth_unverified_hours))
