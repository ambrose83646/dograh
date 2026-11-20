"""Twilio account operations the platform runs on the operator's main account.

Each platform user gets a Twilio subaccount, so calls, caller IDs, and numbers
are separated by Twilio itself and one user can be suspended alone. Usage on
a subaccount is billed to the operator's main account.
"""

from typing import Any

import aiohttp

from api.services.platform.settings import get_platform_settings

_BASE = "https://api.twilio.com/2010-04-01"
_TIMEOUT = aiohttp.ClientTimeout(total=20)


class TwilioAccountError(RuntimeError):
    def __init__(self, status: int, code: int | None, message: str) -> None:
        super().__init__(f"Twilio API {status} (code {code}): {message}")
        self.status = status
        self.code = code
        self.message = message


async def _request(
    method: str,
    path: str,
    *,
    data: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Call Twilio as the main account, which may act on its subaccounts."""
    settings = get_platform_settings()
    auth = aiohttp.BasicAuth(settings.twilio_account_sid, settings.twilio_auth_token)
    async with (
        aiohttp.ClientSession(timeout=_TIMEOUT) as session,
        session.request(
            method, f"{_BASE}{path}", data=data, params=params, auth=auth
        ) as response,
    ):
        if response.status == 204:
            return {}
        body = await response.json(content_type=None)
        if response.status >= 400:
            body = body if isinstance(body, dict) else {}
            raise TwilioAccountError(
                response.status, body.get("code"), str(body.get("message", ""))
            )
        return body


async def send_text(to: str, body: str) -> None:
    """Send a text message from the operator's registered sender."""
    settings = get_platform_settings()
    sender = settings.sms_from
    sender_field = "MessagingServiceSid" if sender.startswith("MG") else "From"
    await _request(
        "POST",
        f"/Accounts/{settings.twilio_account_sid}/Messages.json",
        data={sender_field: sender, "To": to, "Body": body},
    )


async def create_subaccount(friendly_name: str) -> tuple[str, str]:
    """Create a subaccount. Returns its (account_sid, auth_token)."""
    body = await _request(
        "POST", "/Accounts.json", data={"FriendlyName": friendly_name[:64]}
    )
    return body["sid"], body["auth_token"]


async def set_subaccount_status(account_sid: str, status: str) -> None:
    """``active``, ``suspended``, or ``closed``. Closing cannot be undone."""
    if status not in ("active", "suspended", "closed"):
        raise ValueError(f"Unsupported subaccount status: {status}")
    await _request("POST", f"/Accounts/{account_sid}.json", data={"Status": status})


async def start_caller_id_validation(
    account_sid: str, phone_number: str, friendly_name: str
) -> str:
    """Ask Twilio to phone ``phone_number`` and wait for a code.

    Returns the six-digit code the person must key in on that call.
    """
    body = await _request(
        "POST",
        f"/Accounts/{account_sid}/OutgoingCallerIds.json",
        data={
            "PhoneNumber": phone_number,
            "FriendlyName": friendly_name[:64],
            "CallDelay": "5",
        },
    )
    return str(body["validation_code"])


async def find_caller_id(account_sid: str, phone_number: str) -> str | None:
    """The sid of the verified caller ID for ``phone_number``, when it exists."""
    body = await _request(
        "GET",
        f"/Accounts/{account_sid}/OutgoingCallerIds.json",
        params={"PhoneNumber": phone_number},
    )
    rows = body.get("outgoing_caller_ids") or []
    return rows[0]["sid"] if rows else None


async def delete_caller_id(account_sid: str, caller_id_sid: str) -> None:
    await _request(
        "DELETE", f"/Accounts/{account_sid}/OutgoingCallerIds/{caller_id_sid}.json"
    )


async def move_number(phone_number: str, *, from_sid: str, to_sid: str) -> None:
    """Move an owned phone number between the main account and a subaccount."""
    body = await _request(
        "GET",
        f"/Accounts/{from_sid}/IncomingPhoneNumbers.json",
        params={"PhoneNumber": phone_number},
    )
    rows = body.get("incoming_phone_numbers") or []
    if not rows:
        raise TwilioAccountError(
            404, None, f"{phone_number} is not in Twilio account {from_sid}"
        )
    await _request(
        "POST",
        f"/Accounts/{from_sid}/IncomingPhoneNumbers/{rows[0]['sid']}.json",
        # Clear the webhook so a number in transit never reaches an old route.
        data={"AccountSid": to_sid, "VoiceUrl": ""},
    )
