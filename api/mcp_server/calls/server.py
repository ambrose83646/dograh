"""MCP tools that let an AI assistant make and take phone calls for its user.

A separate server from the workflow-authoring one: an assistant that only wants
to phone someone should see five small tools, not a workflow builder.
"""

from functools import wraps
from typing import Annotated

from fastapi import HTTPException
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from api.mcp_server.auth import authenticate_mcp_request
from api.mcp_server.tracing import traced_tool
from api.services.auth.depends import _handle_api_key_auth
from api.services.platform import caller_id, calls

INSTRUCTIONS = """\
This server gives you a phone. You can call a number to carry out a spoken task
for the user, read what was said, and decide how calls to the user's own number
are answered when you are not there.

The user manages everything through you. Do not send the user to a web page
for a setting: caller ID, voice, and inbound rules all have tools here.

Before the first call: calls show the user's own phone number. If
get_account_status shows no caller_id, ask the user for a phone number they
own, call start_caller_id_verification, and tell the user the code. Their
phone rings; they answer and enter the code on the keypad. This is done once.

How to make a call:
1. Call place_call with the number in international format (+14155550123) and
   a task that stands on its own. The voice agent on the call knows only what
   you put in `task` and `background`; it cannot see this conversation.
2. place_call returns at once with a call_id. The call takes minutes.
3. Call get_call_result with that call_id after about 30 seconds, and repeat
   until status is "completed" or "failed". Then tell the user the result.

Write the task the way you would brief a human assistant: who to ask for, what
to ask, which facts to give, which answers to bring back, and what to do when
the first choice is not possible.

Rules:
- Call only numbers the user asked you to call. Never place sales, survey, or
  bulk calls.
- Each account starts with free call minutes. They do not renew. After them
  the user needs the monthly plan, which gives minutes for each period. When
  fewer than 5 minutes remain, a paid pack of more minutes is added
  automatically, up to a limit that the user sets on the billing page.
  get_account_status and each place_call result show the minutes that are
  left. When `minutes_note` has text, tell the user what it says. When a call
  is refused for minutes, the refusal says what the user must do: give the
  user that message, with the page address if it has one.
- The voice agent tells people it is an AI assistant if they ask.
"""

calls_mcp = FastMCP("phone-calls", instructions=INSTRUCTIONS)


def _tool(fn):
    """Authenticate, then turn service errors into clean tool errors."""

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except HTTPException as exc:
            raise ToolError(str(exc.detail)) from exc

    return traced_tool(wrapper)


async def _organization_id() -> int:
    user = await authenticate_mcp_request()
    if not user.selected_organization_id:
        raise HTTPException(status_code=401, detail="This key has no account.")
    return user.selected_organization_id


@_tool
async def place_call(
    phone_number: Annotated[
        str,
        Field(
            description=(
                "Number to call, in international format: plus sign, country "
                "code, number, no spaces. Example: +14155550123."
            )
        ),
    ],
    task: Annotated[
        str,
        Field(
            description=(
                "What the voice agent must achieve on this call, written as a "
                "complete brief. The agent knows nothing else. Include who to "
                "ask for, what to ask or say, the answers to bring back, and "
                "the fallback when the first choice is not possible."
            )
        ),
    ],
    background: Annotated[
        str | None,
        Field(
            description=(
                "Facts the agent may need if asked: names, dates, account or "
                "booking details, preferences. Give only what the other party "
                "is allowed to hear."
            )
        ),
    ] = None,
    on_behalf_of: Annotated[
        str | None,
        Field(
            description=(
                "The name the agent gives for the person it calls for, e.g. "
                "'Maria Lopez'."
            )
        ),
    ] = None,
    call_reason: Annotated[
        str | None,
        Field(
            description=(
                "Why you call, as the end of the sentence 'This is an AI "
                "assistant calling for Maria Lopez, ...'. Example: 'about "
                "Friday's delivery'. Spoken when a call screener asks for the "
                "caller's name and reason, and at the start of a voicemail "
                "message."
            )
        ),
    ] = None,
    voicemail_message: Annotated[
        str | None,
        Field(
            description=(
                "The exact words to leave if a voicemail box answers. Say who "
                "calls, why, and how to reply. You know the user and the "
                "task, so write it yourself for each call. If it is empty, "
                "the service writes a short general message from the task."
            )
        ),
    ] = None,
    allow_user_to_join: Annotated[
        bool,
        Field(
            description=(
                "True: when the other party will continue only with the user "
                "in person, the agent phones the user's verified number and "
                "connects the two. The user presses 1 to join. Tell the user "
                "before the call that their phone can ring. False: the agent "
                "never phones the user."
            )
        ),
    ] = True,
) -> dict:
    """Start a phone call. A voice agent phones the number and carries out the task.

    Returns immediately with a call_id while the phone rings. The call is not
    finished when this returns: read the outcome with get_call_result.

    The service detects what answers. A person: the agent does the task. A
    voicemail box: it leaves voicemail_message and ends the call. A call
    screener that asks who calls: it gives the name and call_reason, then
    waits for the person. An automated phone menu: it presses the keys the
    menu asks for to reach the right department or person; put numbers the
    menu can ask for (account number, extension) in the task or background.
    get_call_result reports this in `answered_by` and `keys_pressed`.

    The agent can bring the user into the call (allow_user_to_join). The user
    and the other party then talk directly. The agent does not speak; it
    listens and writes down what is said, until the user says "assistant,
    leave the call". When the user hangs up, the agent continues the call.
    The time counts as call minutes. get_call_result gives the words in
    `direct_talk`; `user_joined` false means the user did not answer or did
    not press 1.
    """
    return await calls.place_call(
        await _organization_id(),
        phone_number=phone_number,
        task=task,
        background=background,
        on_behalf_of=on_behalf_of,
        call_reason=call_reason,
        voicemail_message=voicemail_message,
        allow_user_to_join=allow_user_to_join,
    )


@_tool
async def get_call_result(
    call_id: Annotated[
        int, Field(description="The call_id from place_call or list_calls.")
    ],
) -> dict:
    """Read the status, outcome, and full transcript of one call.

    status is "ringing", "in_progress", "completed", or "failed". While the
    call is not finished, wait about 20 seconds and ask again. During a call,
    `duration_seconds` and `transcript` show the call so far, and
    `direct_talk_now` shows a direct talk between the user and the other
    party that is in progress: a call with the user on the line is not
    stuck. `result` holds
    the agent's own summary when the call reached its closing step; always
    check it against `transcript`, which is the record of what was said.
    For an outbound call, `answered_by` is "person", "voicemail",
    "call_screener" (the screener answered and the person did not pick up),
    "phone_menu", or "hold_line" (a recording said to wait; the transcript
    shows if a person answered later); `keys_pressed` lists the keys the agent pressed in a
    menu, in order. With "voicemail" the task was not done: tell the user,
    and say if a message was left (`voicemail_message_left`).
    Works for outbound calls and for inbound calls to the user's number.
    """
    return await calls.get_call_result(await _organization_id(), call_id)


@_tool
async def list_calls(
    limit: Annotated[
        int, Field(description="How many calls to return, newest first. Maximum 50.")
    ] = 10,
) -> list[dict]:
    """List the user's recent calls, outbound and inbound, newest first.

    Use this to find calls that came in to the user's number while no
    assistant was connected, then read each one with get_call_result.
    """
    return await calls.list_calls(await _organization_id(), limit)


@_tool
async def set_inbound_rules(
    rules: Annotated[
        str,
        Field(
            description=(
                "Plain-language instructions for the agent that answers the "
                "user's number: what to say, what to ask, which facts it may "
                "give, when to take a message. This replaces the earlier rules."
            )
        ),
    ],
    answer_as: Annotated[
        str | None,
        Field(
            description="Whose phone this is, e.g. 'Maria Lopez' or 'Lopez Plumbing'."
        ),
    ] = None,
    greeting: Annotated[
        str | None,
        Field(
            description=(
                "The exact first sentence spoken when the call is answered. "
                "Leave empty to let the agent greet in its own words."
            )
        ),
    ] = None,
) -> dict:
    """Save how calls to the user's phone number are answered.

    The rules are stored on the service. Later calls are answered with them
    even when no assistant or chat is open.
    """
    return await calls.set_inbound_rules(
        await _organization_id(), rules=rules, answer_as=answer_as, greeting=greeting
    )


@_tool
async def get_inbound_rules() -> dict:
    """Read the saved rules for answering calls to the user's phone number."""
    return await calls.get_inbound_rules(await _organization_id())


@_tool
async def get_account_status() -> dict:
    """Read the user's caller ID, voice, free call minutes left, and call limits.

    Also completes a caller ID check: after the user entered the code,
    `caller_id` shows the verified number.
    """
    return await calls.get_account_status(await _organization_id())


@_tool
async def start_caller_id_verification(
    phone_number: Annotated[
        str,
        Field(
            description=(
                "A phone number the user owns and can answer now, in "
                "international format. Example: +14155550123."
            )
        ),
    ],
) -> dict:
    """Verify a phone number the user owns so outbound calls show that number.

    The user's phone rings within seconds. Tell the user the returned
    validation_code first: they must answer and enter it on the keypad. Then
    call get_account_status to confirm. Needed once, before the first call.
    """
    return await caller_id.start_verification(await _organization_id(), phone_number)


@_tool
async def update_settings(
    voice: Annotated[
        str | None,
        Field(
            description=(
                "The voice the agent speaks with on the user's calls. "
                "get_account_status lists the choices in `voice_options`."
            )
        ),
    ] = None,
) -> dict:
    """Change how the user's voice agent sounds. Returns the settings in use.

    Applies to the next call, outbound and inbound. Call it with no arguments
    to read the settings.
    """
    return await calls.update_settings(await _organization_id(), voice=voice)


_READ = ToolAnnotations(
    readOnlyHint=True, idempotentHint=True, destructiveHint=False, openWorldHint=False
)

calls_mcp.tool(
    place_call,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=False,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
calls_mcp.tool(
    update_settings,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False,
    ),
)
calls_mcp.tool(
    set_inbound_rules,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=True,
        destructiveHint=True,
        openWorldHint=False,
    ),
)
calls_mcp.tool(
    start_caller_id_verification,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=False,
        destructiveHint=False,
        openWorldHint=True,
    ),
)
for _read_tool in (get_call_result, list_calls, get_inbound_rules, get_account_status):
    calls_mcp.tool(_read_tool, annotations=_READ)


class RequireApiKey:
    """Answer 401 at the HTTP layer when a request carries no valid API key.

    MCP clients decide whether a server needs credentials from the HTTP status,
    so an unauthenticated client must not get as far as the tool list.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        api_key = headers.get("x-api-key", "")
        authorization = headers.get("authorization", "")
        if not api_key and authorization.lower().startswith("bearer "):
            api_key = authorization.split(" ", 1)[1].strip()
        detail = "Send your API key as 'Authorization: Bearer <key>'."
        if api_key:
            try:
                await _handle_api_key_auth(api_key)
            except HTTPException as exc:
                api_key, detail = "", str(exc.detail)
        if api_key:
            await self.app(scope, receive, send)
            return
        from starlette.responses import JSONResponse

        response = JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "detail": detail},
            headers={"WWW-Authenticate": 'Bearer realm="phone-calls"'},
        )
        await response(scope, receive, send)
