"""What a platform account can do: place a call, read results, set inbound rules.

The MCP tools and the account REST route are thin wrappers over this module.
Every function takes the caller's ``organization_id`` and reads or writes only
through it; ids that arrive from a client are never trusted on their own.
"""

import re
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException
from loguru import logger

from api.db import db_client
from api.services.platform import caller_id as caller_id_service
from api.services.platform import conference, live_calls, packs
from api.services.platform.agent_definitions import (
    DEFAULT_INBOUND_RULES,
    inbound_agent_definition,
    inbound_rules_from_definition,
)
from api.services.platform.allowance import get_allowance_status
from api.services.platform.destinations import assert_destination_allowed
from api.services.platform.provisioning import (
    VOICES,
    ensure_platform_account,
    get_platform_account,
    get_voice,
    set_voice,
    update_platform_account,
    upgrade_outbound_agent,
)
from api.services.platform.settings import get_platform_settings
from api.services.telephony.factory import get_telephony_provider_for_run
from api.services.telephony.providers.twilio.strategies import TwilioHangupStrategy
from api.services.workflow_run_artifacts import (
    TranscriptDownloadError,
    download_run_transcript_text,
)

MAX_TASK_CHARS = 4000
MAX_BACKGROUND_CHARS = 6000
MAX_RULES_CHARS = 6000
MAX_NAME_CHARS = 120
MAX_REASON_CHARS = 200
MAX_VOICEMAIL_CHARS = 600
BRING_USER_INSTRUCTIONS = (
    "You can phone your client and connect them with the other person, with "
    "the bring_user_on_line tool. Use it when the other person will continue "
    "only with your client in person (an identity check, or a decision or a "
    "payment that only your client can make), or asks to speak with your "
    "client, or refuses to speak with an assistant. Such a refusal is not "
    "the end of the call: first try to get your client on the line. When the "
    "other person says that they can speak with your client now, do not ask "
    "again: use the tool. Do not "
    "use it for a question that you can answer from the task "
    "or the background. First say that you will get your client on the line "
    "and ask the other person to hold; say this in the same turn in which "
    "you use the tool. While the two talk, you cannot speak. When your "
    "client leaves, you get what was said and you continue the call."
)
MAX_GREETING_CHARS = 300


async def _ready_account(organization_id: int) -> dict[str, Any]:
    account = await get_platform_account(organization_id)
    if not account.get("outbound_workflow_id") or not account.get(
        "inbound_workflow_id"
    ):
        await ensure_platform_account(organization_id)
        account = await get_platform_account(organization_id)
    if not account.get("outbound_workflow_id") or not account.get(
        "inbound_workflow_id"
    ):
        raise HTTPException(
            status_code=503,
            detail="This account is still being set up. Try again in a minute.",
        )
    return await upgrade_outbound_agent(organization_id, account)


async def _checked_account(organization_id: int) -> tuple[int, dict[str, Any]]:
    """The account after a pending phone check. A check can join this account
    to the account that has the phone already; the answer is then for that one.
    """
    account = await _ready_account(organization_id)
    account = await caller_id_service.refresh(organization_id, account)
    if account.get("joined_to"):
        organization_id = account["joined_to"]
        account = await _ready_account(organization_id)
    return organization_id, account


def _from_number(account: dict[str, Any]) -> tuple[int | None, str | None]:
    """The number outbound calls show: the user's own, else the service number."""
    if account.get("caller_id_phone_number_id"):
        return account["caller_id_phone_number_id"], account.get("caller_id")
    if account.get("phone_number_id"):
        return account["phone_number_id"], account.get("phone_number")
    return None, None


def _setup(account: dict[str, Any], allowance, from_id: int | None) -> dict[str, Any]:
    """Where the user is in the first-run steps, and the one next step.

    The assistant leads the setup from this: it does not guess the order.
    """
    pending = account.get("caller_id_pending")
    if not account.get("caller_id"):
        if pending:
            return {
                "state": "waiting_for_code",
                "done": False,
                "next_step": (
                    f"The phone {pending['phone_number']} rings. The user must "
                    "answer and enter the code on the keypad. Then call "
                    "get_account_status again. If the user did not get the "
                    "call, call start_caller_id_verification again."
                ),
            }
        return {
            "state": "verify_phone",
            "done": False,
            "next_step": (
                "Ask the user for their own mobile number (United States or "
                "Canada). Call start_caller_id_verification with it and tell "
                "the user the code before their phone rings. This one check "
                "is the full setup: no web page and no other step."
            ),
        }
    if allowance.blocked_code is not None or from_id is None:
        return {
            "state": "blocked",
            "done": True,
            "next_step": allowance.blocked_message
            or "This account cannot call now. Try again in a minute.",
        }
    return {
        "state": "ready",
        "done": True,
        "next_step": "Setup is complete. Ask the user which call to make.",
    }


async def get_account_status(organization_id: int) -> dict[str, Any]:
    organization_id, account = await _checked_account(organization_id)
    allowance = await get_allowance_status(organization_id)
    await packs.request_pack_if_low(organization_id, allowance)
    settings = get_platform_settings()
    phone_number = account.get("phone_number")
    from_id, from_number = _from_number(account)
    pending = account.get("caller_id_pending")
    voice = await get_voice(organization_id, account)
    if account.get("caller_id"):
        caller_id_status = "verified"
    elif pending:
        caller_id_status = (
            f"Waiting for the code to be entered on {pending['phone_number']}."
        )
    else:
        caller_id_status = (
            "Not set. Use start_caller_id_verification with a phone number "
            "the user owns. Outbound calls then show that number."
        )
    return {
        "setup": _setup(account, allowance, from_id),
        "caller_id": account.get("caller_id"),
        "caller_id_status": caller_id_status,
        "outbound_calls_from": from_number,
        "phone_number": phone_number,
        "phone_number_status": (
            "ready"
            if phone_number and account.get("inbound_routed")
            else "This account has no number for inbound calls. The operator "
            "adds one on request."
        ),
        # None: the account is on its free minutes, which do not renew.
        "plan": allowance.plan_name,
        "plan_period_end": (
            allowance.period_end.isoformat() if allowance.period_end else None
        ),
        "minutes_total": round(allowance.allowed_seconds / 60, 1),
        "minutes_used": round(allowance.used_seconds / 60, 1),
        "minutes_remaining": round(allowance.remaining_seconds / 60, 1),
        # None unless under 20% of the minutes remain.
        "minutes_note": allowance.low_minutes_note,
        # Paid packs of more minutes that are added when the minutes run low.
        "automatic_packs": {
            "limit": allowance.pack_limit,
            "added_this_period": allowance.packs_added,
        },
        "calls_in_last_24_hours": allowance.calls_last_24h,
        "daily_call_limit": allowance.daily_call_limit,
        "max_call_minutes": round(settings.max_call_seconds / 60, 1),
        "can_call": allowance.blocked_code is None and from_id is not None,
        "blocked_reason": allowance.blocked_message,
        "test_period": bool(settings.destination_allowlist),
        "voice": voice,
        "voice_options": list(VOICES) if voice else [],
    }


async def update_settings(
    organization_id: int, *, voice: str | None = None
) -> dict[str, Any]:
    account = await _ready_account(organization_id)
    current = await get_voice(organization_id, account)
    if voice is not None:
        voice = voice.strip().lower()
        if current is None:
            raise HTTPException(
                status_code=409, detail="This service has one voice only."
            )
        if voice not in VOICES:
            raise HTTPException(
                status_code=400,
                detail="Unknown voice. The voices are: " + ", ".join(VOICES) + ".",
            )
        await set_voice(organization_id, account, voice)
        current = voice
    return {
        "voice": current,
        "voice_options": list(VOICES) if current else [],
        "note": "The voice applies to the next call.",
    }


_VOICEMAIL_INSTRUCTIONS = """You write the message that an AI phone assistant \
leaves when a voicemail box answers its call. You get the task of the call.
Write the exact words to speak, and nothing else.
- Start with: "Hello. This is an AI assistant calling for <the person or \
business the call is for>."
- If the task names the person to reach, say that the message is for that person.
- Give the reason for the call in one short sentence of general words. Other \
people can hear a voicemail: give no details about health, money, accounts, \
legal matters or family matters, and no numbers, codes, results or addresses. \
If the task says to confirm who answers before sharing something, do not share it.
- Ask the listener to contact the person or business the call is for. Do not \
promise a second call. Do not give a phone number unless the task says to.
- End with "Thank you. Goodbye."
- Plain spoken sentences. At most 60 words. Use the language of the task."""


async def _write_voicemail_message(task: str, principal: str, reason: str) -> str:
    """The words for a voicemail box when the client gave none.

    A message that does not say why the call was made is of no use to the
    person who hears it, so it is written from the task. The call must not
    fail or wait long for this: on any error a short message that needs no
    model is used.
    """
    fallback = (
        f"Hello. This is an AI assistant calling for {principal}"
        + (f", {reason}" if reason else "")
        + f". Please contact {principal} when you can. Thank you. Goodbye."
    )
    settings = get_platform_settings()
    if not settings.openai_api_key:
        return fallback
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            response = await http.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": _VOICEMAIL_INSTRUCTIONS},
                        {
                            "role": "user",
                            "content": (
                                f"The call is for: {principal}\n"
                                f"Reason given for the call: {reason or 'none'}\n"
                                f"Task of the call:\n{task}"
                            ),
                        },
                    ],
                },
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
        text = " ".join((text or "").split()).strip('"')
        if len(text) < 20:
            return fallback
        return text[:MAX_VOICEMAIL_CHARS]
    except Exception as e:
        logger.warning(f"Voicemail message not written ({type(e).__name__})")
        return fallback


async def place_call(
    organization_id: int,
    *,
    phone_number: str,
    task: str,
    background: str | None = None,
    on_behalf_of: str | None = None,
    call_reason: str | None = None,
    voicemail_message: str | None = None,
    allow_user_to_join: bool = True,
    api_key_id: int | None = None,
    api_key_created_by: int | None = None,
) -> dict[str, Any]:
    task = (task or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="Give a task for the call.")
    if len(task) > MAX_TASK_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"The task is too long. The limit is {MAX_TASK_CHARS} characters.",
        )
    if background and len(background) > MAX_BACKGROUND_CHARS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The background is too long. The limit is "
                f"{MAX_BACKGROUND_CHARS} characters."
            ),
        )
    phone_number = (phone_number or "").strip()
    assert_destination_allowed(phone_number)

    organization_id, account = await _checked_account(organization_id)
    from_id, from_number = _from_number(account)
    if from_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This account has no caller ID yet. Use "
                "start_caller_id_verification with a phone number the user "
                "owns, then place the call."
            ),
        )
    if phone_number in (account.get("phone_number"), account.get("caller_id")):
        raise HTTPException(
            status_code=400, detail="An account cannot call its own number."
        )

    # Checked again inside start_outbound_call; this early check refuses
    # without leaving a failed call record behind.
    allowance = await get_allowance_status(organization_id)
    await packs.request_pack_if_low(organization_id, allowance)
    if allowance.blocked_code is not None:
        raise HTTPException(status_code=402, detail=allowance.blocked_message)

    workflow = await db_client.get_workflow(
        account["outbound_workflow_id"], organization_id=organization_id
    )
    if workflow is None:
        raise HTTPException(status_code=503, detail="Calling is not set up yet.")

    context = {
        "task": task,
        "platform_call": True,
    }
    if background and background.strip():
        context["background"] = background.strip()
    if allow_user_to_join and await conference.available(organization_id, phone_number):
        context["bring_user"] = True
        context["bring_user_instructions"] = BRING_USER_INSTRUCTIONS
    if on_behalf_of and on_behalf_of.strip():
        context["principal_name"] = on_behalf_of.strip()[:MAX_NAME_CHARS]
    # Spoken by the answer handling, before the agent's own conversation:
    # the first to a call screener, the second to a voicemail box.
    principal = context.get("principal_name", "a client")
    reason = (call_reason or "").strip().rstrip(".")[:MAX_REASON_CHARS]
    introduction = f"This is an AI assistant calling for {principal}" + (
        f", {reason}." if reason else "."
    )
    context["screening_introduction"] = introduction
    context["voicemail_message"] = (voicemail_message or "").strip()[
        :MAX_VOICEMAIL_CHARS
    ] or await _write_voicemail_message(task, principal, reason)

    # The public agent route owns Dograh's one outbound dial path (concurrency
    # slot, quota, provider call). It is reused as-is so platform calls cannot
    # drift from it; the import is local because routes sit above services.
    from api.routes.public_agent import (
        ResolvedAgentTarget,
        TriggerCallRequest,
        _execute_resolved_target,
    )

    response = await _execute_resolved_target(
        ResolvedAgentTarget(
            workflow=workflow,
            organization_id=organization_id,
            identifier_type="workflow_uuid",
            identifier_value=workflow.workflow_uuid,
        ),
        TriggerCallRequest(
            phone_number=phone_number,
            initial_context=context,
            telephony_configuration_id=account["telephony_configuration_id"],
            from_phone_number_id=from_id,
        ),
        use_draft=False,
        api_key_id=api_key_id,
        api_key_created_by=api_key_created_by,
    )
    return {
        "call_id": response.workflow_run_id,
        "status": "ringing",
        "to": phone_number,
        "from": from_number,
        # Measured before this call; the call ends when they are used.
        "minutes_remaining": round(allowance.remaining_seconds / 60, 1),
        "max_minutes_this_call": round(
            (
                get_platform_settings().max_call_seconds
                if allowance.pack_available
                else min(
                    get_platform_settings().max_call_seconds,
                    allowance.remaining_seconds,
                )
            )
            / 60,
            1,
        ),
        "minutes_note": allowance.low_minutes_note,
        "next_step": (
            "The call is in progress. Call get_call_result with this call_id "
            "after about 30 seconds, and again until status is 'completed'."
        ),
    }


def _answered_by(gathered: dict[str, Any]) -> dict[str, Any]:
    """What picked up an outbound call, from the answer handling's verdicts."""
    verdicts = [
        v for v in gathered.get("answer_supervisor") or [] if isinstance(v, dict)
    ]
    if not verdicts:
        return {}
    subtypes = [v.get("subtype") for v in verdicts]
    final = verdicts[-1]
    if "VOICEMAIL" in subtypes or "NO_MESSAGE" in subtypes:
        answered_by = "voicemail"
    elif "IVR" in subtypes:
        answered_by = "phone_menu"
    elif final.get("reason") == "screening_timeout":
        # A recording asked to wait and no person spoke in the first seconds.
        answered_by = "hold_line"
    elif final.get("action") == "release":
        answered_by = "person"
    elif "SCREENER" in subtypes or "SCREENING_WAIT" in subtypes:
        # The screener answered and the person did not pick up.
        answered_by = "call_screener"
    else:
        answered_by = "unknown"
    result: dict[str, Any] = {"answered_by": answered_by}
    if "SCREENER" in subtypes or "SCREENING_WAIT" in subtypes:
        result["call_screener_detected"] = True
    if answered_by == "voicemail":
        result["voicemail_message_left"] = (
            final.get("action") == "leave_message"
            and final.get("reason") != "answer_message_failed"
            and gathered.get("call_disposition") != "answer_message_failed"
        )
    return result


def _direction(run, account: dict[str, Any]) -> str:
    if run.workflow_id == account.get("inbound_workflow_id"):
        return "inbound"
    return "outbound"


def _summarize(run, account: dict[str, Any]) -> dict[str, Any]:
    initial = run.initial_context or {}
    gathered = run.gathered_context or {}
    usage = run.usage_info or {}
    direction = _direction(run, account)
    error = gathered.get("error") or (run.annotations or {}).get("error")
    if run.is_completed:
        status = (
            "failed"
            if error and not usage.get("call_duration_seconds")
            else ("completed")
        )
    elif run.state == "running":
        status = "in_progress"
    else:
        status = "ringing"
    summary = {
        "call_id": run.id,
        "direction": direction,
        "status": status,
        "started_at": run.created_at.isoformat() if run.created_at else None,
        "duration_seconds": round(float(usage.get("call_duration_seconds") or 0)),
        "to": initial.get("called_number"),
        "from": initial.get("caller_number"),
        "disposition": gathered.get("mapped_call_disposition")
        or gathered.get("call_disposition"),
    }
    live = None if run.is_completed else live_calls.progress(run.id)
    if live is not None:
        # The call is connected. Its record is written when it ends.
        summary["status"] = "in_progress"
        summary["duration_seconds"] = live["seconds"]
    if direction == "outbound":
        summary.update(_answered_by(gathered))
        keys = [k for k in gathered.get("keys_pressed") or [] if isinstance(k, str)]
        if keys:
            summary["keys_pressed"] = keys
    if direction == "outbound":
        summary["task"] = initial.get("task")
    if gathered.get("ended_by"):
        summary["ended_by"] = gathered["ended_by"]
    if error:
        summary["error"] = str(error)
    return summary


_ENTRY_START = re.compile(r"(?m)^(?=\[\d{4}-\d\d-\d\dT)")
_DIRECT_TALK_LABELS = {
    "user": "direct talk, your user",
    "other_party": "direct talk, other person",
}


def _time_of(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _with_direct_talk(transcript: str, lines: list[dict[str, Any]]) -> str:
    """Put the lines of the direct talks into the transcript, in time order.

    The transcript has what the agent said and heard. In a direct talk the
    agent says and hears nothing, so the transcript has a hole there.
    """
    timed = [
        (at, line)
        for line in lines
        if isinstance(line, dict) and (at := _time_of(str(line.get("at") or "")))
    ]
    if not timed:
        return transcript
    timed.sort(key=lambda pair: pair[0])
    merged: list[str] = []

    def add_lines_before(limit: datetime | None) -> None:
        while timed and (limit is None or timed[0][0] < limit):
            at, line = timed.pop(0)
            label = _DIRECT_TALK_LABELS.get(line.get("speaker"), "direct talk")
            merged.append(f"[{line['at']}] {label}: {line.get('text', '')}\n")

    for entry in _ENTRY_START.split(transcript):
        if not entry:
            continue
        add_lines_before(_time_of(entry[1:].split("]")[0].split(" ")[0]))
        merged.append(entry if entry.endswith("\n") else entry + "\n")
    add_lines_before(None)
    return "".join(merged)


async def get_call_result(organization_id: int, call_id: int) -> dict[str, Any]:
    account = await _ready_account(organization_id)
    run = await db_client.get_workflow_run(
        run_id=call_id, organization_id=organization_id
    )
    if run is None:
        # Same answer for "does not exist" and "belongs to someone else".
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")

    result = _summarize(run, account)
    live = None if run.is_completed else live_calls.progress(run.id)
    talks = (
        live["direct_talks"]
        if live is not None
        else (run.gathered_context or {}).get("direct_talk") or []
    )
    direct_talk = [
        {
            "result": talk.get("status"),
            "user_joined": bool(talk.get("user_joined")),
            "seconds": talk.get("direct_talk_seconds", 0),
            "assistant_listened_to_the_end": talk.get(
                "assistant_listened_to_the_end", False
            ),
            "lines": talk.get("lines") or [],
        }
        for talk in talks
        if isinstance(talk, dict)
    ]
    if direct_talk:
        # The user joined the call, or the agent tried to get them.
        result["direct_talk"] = direct_talk
    result["result"] = (run.gathered_context or {}).get("extracted_variables") or {}
    result["transcript"] = ""
    talk_lines = [line for talk in direct_talk for line in talk["lines"]]
    if live is not None:
        now = conference.direct_talk_now(run.id)
        if now is not None:
            result["direct_talk_now"] = now
            talk_lines = talk_lines + (now.get("lines") or [])
        result["transcript"] = _with_direct_talk(live["transcript"], talk_lines)
        result["next_step"] = (
            "The call is in progress. duration_seconds and transcript show "
            "the call so far. Ask again in 20 seconds."
        )
        return result
    if run.transcript_url:
        try:
            result["transcript"] = await download_run_transcript_text(
                transcript_url=run.transcript_url,
                storage_backend=run.storage_backend,
            )
            result["transcript"] = _with_direct_talk(result["transcript"], talk_lines)
        except (TranscriptDownloadError, ValueError) as exc:
            logger.warning(f"Transcript for call {call_id} could not be read: {exc}")
            result["transcript_error"] = (
                "The transcript exists but could not be read. Try again."
            )
    if result["status"] in ("ringing", "in_progress"):
        result["next_step"] = "The call has not ended. Ask again in 20 seconds."
    elif not result["transcript"] and "transcript_error" not in result:
        result["next_step"] = (
            "The call ended. If it was answered, the transcript appears within "
            "a minute; ask again once."
        )
    return result


async def end_call(organization_id: int, call_id: int) -> dict[str, Any]:
    """Hang up one call of this account now. A call that is over stays as it is."""
    account = await _ready_account(organization_id)
    run = await db_client.get_workflow_run(
        run_id=call_id, organization_id=organization_id
    )
    if run is None:
        # Same answer for "does not exist" and "belongs to someone else".
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    if run.is_completed:
        summary = _summarize(run, account)
        return {
            "call_id": run.id,
            "ended_now": False,
            "status": summary["status"],
            "next_step": "This call was over already. Nothing changed.",
        }
    call_sid = (run.gathered_context or {}).get("call_id")
    if not call_sid:
        raise HTTPException(
            status_code=409,
            detail="This call has not reached the phone network yet. "
            "Try again in a few seconds.",
        )
    provider = await get_telephony_provider_for_run(run, organization_id)
    hung_up = await TwilioHangupStrategy().execute_hangup(
        {
            "account_sid": provider.account_sid,
            "auth_token": provider.auth_token,
            "call_sid": call_sid,
        }
    )
    if not hung_up:
        raise HTTPException(
            status_code=502,
            detail="The phone network did not end the call. Try again.",
        )
    await db_client.update_workflow_run(
        run.id, gathered_context={"ended_by": "assistant"}
    )
    return {
        "call_id": run.id,
        "ended_now": True,
        "next_step": (
            "The call is ending. Call get_call_result in about 10 seconds for "
            "the record of what was said before the end."
        ),
    }


async def get_billing_link(organization_id: int) -> dict[str, Any]:
    """The page where the user starts or changes the monthly plan."""
    organization_id, account = await _checked_account(organization_id)
    allowance = await get_allowance_status(organization_id)
    url = get_platform_settings().billing_url
    if not url:
        raise HTTPException(
            status_code=503, detail="The billing page is not available now."
        )
    phone = account.get("caller_id")
    return {
        "url": url,
        "sign_in": (
            f"The user signs in on that page with the phone {phone}: the page "
            "sends a code by text message. No password."
            if phone
            else "The user must verify a phone number first "
            "(start_caller_id_verification). The page signs in with that phone."
        ),
        "plan": allowance.plan_name,
        "minutes_remaining": round(allowance.remaining_seconds / 60, 1),
        "next_step": (
            "Give the user this address as a link. Payment needs the user: "
            "you cannot pay for them. After the payment, call "
            "get_account_status to see the new minutes."
        ),
    }


async def list_calls(organization_id: int, limit: int = 20) -> list[dict[str, Any]]:
    account = await _ready_account(organization_id)
    runs = await db_client.list_platform_calls(
        organization_id, limit=max(1, min(limit, 50))
    )
    return [_summarize(run, account) for run in runs]


async def get_inbound_rules(organization_id: int) -> dict[str, Any]:
    account = await _ready_account(organization_id)
    workflow = await db_client.get_workflow(
        account["inbound_workflow_id"], organization_id=organization_id
    )
    rules = None
    if workflow is not None and workflow.released_definition is not None:
        rules = inbound_rules_from_definition(
            workflow.released_definition.workflow_json
        )
    return {
        "phone_number": account.get("phone_number"),
        "rules": rules if rules is not None else DEFAULT_INBOUND_RULES,
        "answer_as": account.get("inbound_answer_as") or "",
        "greeting": account.get("inbound_greeting") or "",
        "is_default": not account.get("inbound_rules_saved"),
    }


async def set_inbound_rules(
    organization_id: int,
    *,
    rules: str,
    answer_as: str | None = None,
    greeting: str | None = None,
) -> dict[str, Any]:
    rules = (rules or "").strip()
    if not rules:
        raise HTTPException(status_code=400, detail="Give the rules text.")
    if len(rules) > MAX_RULES_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"The rules are too long. The limit is {MAX_RULES_CHARS} characters.",
        )
    answer_as = (answer_as or "").strip()[:MAX_NAME_CHARS]
    greeting = (greeting or "").strip()[:MAX_GREETING_CHARS]

    account = await _ready_account(organization_id)
    workflow = await db_client.get_workflow(
        account["inbound_workflow_id"], organization_id=organization_id
    )
    if workflow is None:
        raise HTTPException(status_code=503, detail="Calling is not set up yet.")

    definition = inbound_agent_definition(
        rules, principal_name=answer_as, greeting=greeting or None
    )
    await db_client.save_workflow_draft(
        workflow.id,
        workflow_definition=definition,
        workflow_configurations={
            "max_call_duration": get_platform_settings().max_call_seconds
        },
    )
    await db_client.publish_workflow_draft(
        workflow.id, change_description="Inbound rules updated"
    )
    await update_platform_account(
        organization_id,
        inbound_rules_saved=True,
        inbound_answer_as=answer_as,
        inbound_greeting=greeting,
    )
    return {
        "saved": True,
        "phone_number": account.get("phone_number"),
        "note": (
            "The next call to this number is answered with these rules. No "
            "assistant has to be connected at that time."
            if account.get("phone_number")
            else "The rules are saved. They apply when this account gets a "
            "phone number."
        ),
    }
