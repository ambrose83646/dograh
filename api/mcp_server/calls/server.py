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
from api.services.platform import calls

INSTRUCTIONS = """\
This server gives you a phone. You can call a number to carry out a spoken task
for the user, read what was said, and decide how calls to the user's own number
are answered when you are not there.

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
- Each account has a free allowance of call minutes. get_account_status shows
  what is left. When it is used, calls are refused.
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
) -> dict:
    """Start a phone call. A voice agent phones the number and carries out the task.

    Returns immediately with a call_id while the phone rings. The call is not
    finished when this returns: read the outcome with get_call_result.
    """
    return await calls.place_call(
        await _organization_id(),
        phone_number=phone_number,
        task=task,
        background=background,
        on_behalf_of=on_behalf_of,
    )


@_tool
async def get_call_result(
    call_id: Annotated[
        int, Field(description="The call_id from place_call or list_calls.")
    ],
) -> dict:
    """Read the status, outcome, and full transcript of one call.

    status is "ringing", "in_progress", "completed", or "failed". While the
    call is not finished, wait about 20 seconds and ask again. `result` holds
    the agent's own summary when the call reached its closing step; always
    check it against `transcript`, which is the record of what was said.
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
    """Read the user's phone number, free call minutes left, and call limits."""
    return await calls.get_account_status(await _organization_id())


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
    set_inbound_rules,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        idempotentHint=True,
        destructiveHint=True,
        openWorldHint=False,
    ),
)
for _read_tool in (get_call_result, list_calls, get_inbound_rules, get_account_status):
    calls_mcp.tool(_read_tool, annotations=_READ)
