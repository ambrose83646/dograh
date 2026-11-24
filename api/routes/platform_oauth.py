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
    # The two font hosts are the ones that danadial.com uses.
    "Content-Security-Policy": "default-src 'none'; "
    "style-src 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "form-action *; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
}

# The look of danadial.com: paper background, ink text, serif headings, the
# dial mark, and one red accent.
_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f3eee4">
<title>DanaDial</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&amp;family=Instrument+Serif:ital@0;1&amp;family=JetBrains+Mono:wght@500&amp;display=swap">
<style>
*{{box-sizing:border-box}}
body{{font:16px/1.55 "Geist","DM Sans",system-ui,sans-serif;margin:0;
background:#f3eee4;color:#161b27;-webkit-font-smoothing:antialiased;
background-image:repeating-linear-gradient(#f3eee4 0 33px,#ece6da 33px 34px)}}
.wrap{{max-width:32rem;margin:0 auto;padding:6vh 1.25rem 3rem}}
.brand{{display:flex;align-items:center;gap:.6rem;margin:0 0 1.5rem .25rem;
font:1.5rem/1 "Instrument Serif",Georgia,serif}}
.brand svg{{width:30px;height:30px}}
main{{padding:2.25rem 2rem 2rem;background:#faf8f3;border:1px solid #d8d1c4;
border-radius:10px;box-shadow:0 14px 30px -12px rgba(22,27,39,.2)}}
.eyebrow{{font:500 .7rem/1 "JetBrains Mono",ui-monospace,monospace;
letter-spacing:.2em;text-transform:uppercase;color:#2c6360;margin:0 0 1rem}}
h1{{font:400 2.5rem/1.05 "Instrument Serif",Georgia,serif;
letter-spacing:-.01em;margin:0 0 1.25rem}}
h1 em{{color:#ea3a14;white-space:nowrap}}
p{{margin:0 0 1rem}}
ul{{list-style:none;padding:0;margin:0 0 1.25rem;border-top:1px solid #e3ddd1}}
li{{position:relative;padding:.7rem 0 .7rem 1.4rem;border-bottom:1px solid #e3ddd1}}
li::before{{content:"";position:absolute;left:.15rem;top:1.25rem;width:7px;
height:7px;border-radius:50%;background:#ea3a14}}
.who{{font-weight:600;overflow-wrap:anywhere}}
.free{{display:inline-block;background:#e9e3d7;border-radius:6px;
padding:.45rem .7rem;font-size:.92rem}}
.to{{color:#5c6270;font-size:.82rem;overflow-wrap:anywhere;margin:1.25rem 0 0}}
.row{{display:flex;gap:.75rem;margin-top:1.25rem}}
button{{flex:1;font:inherit;font-weight:500;line-height:1;padding:.95rem;
border-radius:6px;border:1px solid #c9c2b4;background:transparent;color:#161b27;
cursor:pointer}}
button:hover{{background:#eee9de}}
button.allow{{flex:2;background:#1c2230;border-color:#1c2230;color:#faf8f3;
font-weight:600}}
button.allow:hover{{background:#2a3244}}
button:focus-visible{{outline:2px solid #ea3a14;outline-offset:2px}}
.foot{{margin:1.25rem .25rem 0;color:#5c6270;font-size:.82rem}}
.foot a{{color:inherit}}
@media (max-width:420px){{.wrap{{padding-top:1.25rem}}
.brand{{margin-bottom:1rem}}li{{padding-top:.5rem;padding-bottom:.5rem}}
li::before{{top:1.05rem}}main{{padding:1.5rem 1.25rem 1.25rem}}
h1{{font-size:2.1rem}}}}
</style></head><body><div class="wrap">
<div class="brand"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"
aria-hidden="true"><circle cx="16" cy="16" r="15" fill="#1c2230"/>
<g fill="#f3eee4"><circle cx="21" cy="7.3" r="2.3"/><circle cx="25.4" cy="12" r="2.3"/>
<circle cx="25.8" cy="18.3" r="2.3"/><circle cx="22.4" cy="23.6" r="2.3"/>
<circle cx="16.6" cy="26" r="2.3"/><circle cx="10.6" cy="24.4" r="2.3"/>
<circle cx="6.6" cy="19.6" r="2.3"/><circle cx="6.3" cy="13.4" r="2.3"/>
<circle cx="9.6" cy="8.2" r="2.3"/></g><circle cx="16" cy="16" r="4" fill="#ea3e1c"/>
</svg>DanaDial</div>
<main>
{body}
</main>
<p class="foot"><a href="https://danadial.com/terms">Terms</a> ·
<a href="https://danadial.com/privacy">Privacy</a> ·
<a href="https://danadial.com">danadial.com</a></p>
</div></body></html>"""

_CONSENT = """<p class="eyebrow">Permission</p>
<h1>Give your assistant <em>a phone.</em></h1>
<p><span class="who">{client}</span> asks to use DanaDial for you.
If you allow this, your assistant can:</p>
<ul>
<li>Make phone calls for you with an AI voice. The voice says that it is
Dana Dial, an AI assistant.</li>
<li>Show your own phone number on those calls, after you prove that the
number is yours.</li>
<li>Read what was said on your calls. DanaDial writes down the words of
each call and deletes them after 30 days.</li>
<li>Phone you to bring you into a call.</li>
</ul>
<p class="free">You get 10 free call minutes. You are not asked to pay on
this page.</p>
<form method="post" action="/oauth/consent">
<input type="hidden" name="request" value="{request}">
<div class="row">
<button type="submit" name="decision" value="cancel">Cancel</button>
<button type="submit" name="decision" value="allow" class="allow">Allow</button>
</div></form>
<p class="to">After this step you go back to: {target}</p>"""

_TOO_MANY = """<p class="eyebrow">Not now</p>
<h1>Too many new accounts <em>today.</em></h1>
<p>Too many new DanaDial accounts were made from your network today. No
account was made for you. Try again tomorrow.</p>"""

_EXPIRED = """<p class="eyebrow">Expired</p>
<h1>This step is <em>not valid now.</em></h1>
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
