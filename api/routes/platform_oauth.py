"""The consent page of the OAuth sign-in (platform mode only)."""

from datetime import timedelta
from html import escape
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from api.db import db_client
from api.routes.platform import _client_address, _require_operator
from api.services.platform import oauth_accounts, transcript_retention
from api.services.platform.oauth import (
    PlatformOAuthProvider,
    TooManyAccounts,
    reset_account_limits,
)
from api.services.platform.settings import get_platform_settings

router = APIRouter()
provider = PlatformOAuthProvider()

_HEADERS = {
    "Cache-Control": "no-store",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
    "form-action *; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
}

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DanaDial</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;margin:0;background:#f4f5f7;color:#16181d}}
main{{max-width:30rem;margin:8vh auto;padding:2rem;background:#fff;border-radius:12px;
box-shadow:0 1px 4px rgba(0,0,0,.12)}}
h1{{font-size:1.35rem;margin:0 0 1rem}}
ul{{padding-left:1.2rem}} li{{margin:.35rem 0}}
.who{{font-weight:600;overflow-wrap:anywhere}}
.to{{color:#5b6270;font-size:.85rem;overflow-wrap:anywhere}}
.row{{display:flex;gap:.75rem;margin-top:1.5rem}}
button{{flex:1;font:inherit;padding:.75rem;border-radius:8px;border:1px solid #c5cad3;
background:#fff;cursor:pointer}}
button.allow{{background:#1456d9;border-color:#1456d9;color:#fff;font-weight:600}}
</style></head><body><main>
{body}
</main></body></html>"""

_CONSENT = """<h1>Give your assistant a phone</h1>
<p><span class="who">{client}</span> asks to use DanaDial for you.</p>
<p>If you allow this, your assistant can:</p>
<ul>
<li>Make phone calls for you with an AI voice. The voice says that it is an
AI assistant if a person asks.</li>
<li>Show your own phone number on those calls, after you prove that the
number is yours.</li>
<li>Read what was said on your calls. DanaDial writes down the words of
each call.</li>
<li>Phone you to bring you into a call.</li>
</ul>
<p>You get 10 free call minutes. You are not asked to pay on this page.</p>
<p class="to">After this step you go back to: {target}</p>
<form method="post" action="/oauth/consent">
<input type="hidden" name="request" value="{request}">
<div class="row">
<button type="submit" name="decision" value="cancel">Cancel</button>
<button type="submit" name="decision" value="allow" class="allow">Allow</button>
</div></form>"""

_TOO_MANY = """<h1>Too many new accounts</h1>
<p>Too many new DanaDial accounts were made from your network today. No
account was made for you. Try again tomorrow.</p>"""

_EXPIRED = """<h1>This step is not valid now</h1>
<p>Go back to your assistant and connect DanaDial again.</p>"""


def _page(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(body=body), status_code=status, headers=_HEADERS)


@router.get("/oauth/consent", include_in_schema=False)
async def consent_page(request: str = "") -> HTMLResponse:
    saved = await provider.consent_request(request) if request else None
    if saved is None:
        return _page(_EXPIRED, 400)
    target = urlsplit(saved["redirect_uri"])
    return _page(
        _CONSENT.format(
            client=escape(saved["client_name"][:80] or "An assistant"),
            target=escape(f"{target.scheme}://{target.netloc}"),
            request=escape(request),
        )
    )


@router.post("/oauth/consent", include_in_schema=False)
async def consent_decision(
    http_request: Request,
    request: str = Form(default=""),
    decision: str = Form(default=""),
) -> Response:
    try:
        where = await provider.decide(
            request,
            allow=decision == "allow",
            client_address=_client_address(http_request),
        )
    except TooManyAccounts:
        return _page(_TOO_MANY, 429)
    if where is None:
        return _page(_EXPIRED, 400)
    return RedirectResponse(
        where, status_code=303, headers={"Cache-Control": "no-store"}
    )


@router.post(
    "/api/v1/platform/operator/oauth/reset-limits",
    dependencies=[Depends(_require_operator)],
    include_in_schema=False,
)
async def reset_oauth_limits() -> dict:
    return {"reset": await reset_account_limits()}


@router.get(
    "/api/v1/platform/operator/oauth/summary",
    dependencies=[Depends(_require_operator)],
    include_in_schema=False,
)
async def oauth_summary() -> dict:
    """Accounts that came from an OAuth consent and have no phone yet."""
    organization_ids = await db_client.list_platform_oauth_accounts()
    return {"accounts": len(organization_ids), "organization_ids": organization_ids}


class CleanUpRequest(BaseModel):
    # None: the age from the settings, as in the timed clean-up.
    older_than_hours: float | None = Field(default=None, ge=0)


@router.post(
    "/api/v1/platform/operator/oauth/clean-up",
    dependencies=[Depends(_require_operator)],
    include_in_schema=False,
)
async def clean_up_oauth_accounts(request: CleanUpRequest | None = None) -> dict:
    """Close OAuth accounts that joined an account or never proved a phone."""
    hours = request.older_than_hours if request else None
    if hours is None:
        hours = get_platform_settings().oauth_unverified_hours
    return await oauth_accounts.clean_up(timedelta(hours=hours))


class DeleteOldTranscriptsRequest(BaseModel):
    # None: the age from the settings, as in the timed deletion.
    older_than_seconds: float | None = Field(default=None, ge=0)


@router.post(
    "/api/v1/platform/operator/transcripts/delete-old",
    dependencies=[Depends(_require_operator)],
    include_in_schema=False,
)
async def delete_old_transcripts(
    request: DeleteOldTranscriptsRequest | None = None,
) -> dict:
    """Delete the words of the calls that are older than the storage time."""
    seconds = request.older_than_seconds if request else None
    if seconds is None:
        seconds = get_platform_settings().transcript_days * 86400
    return await transcript_retention.delete_old(timedelta(seconds=seconds))
