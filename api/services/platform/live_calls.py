"""Calls that run now, for the progress that get_call_result shows.

The record of a call is written when the call ends. Until then, the facts
about the call are in the memory of this process. The service runs one web
process, so a request for a call finds it here.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _LiveCall:
    transcript: Callable[[], str]
    connected_at: float = field(default_factory=time.monotonic)
    direct_talks: list[dict[str, Any]] = field(default_factory=list)


_live: dict[int, _LiveCall] = {}


def register(workflow_run_id: int, transcript: Callable[[], str]) -> None:
    """The call is connected. ``transcript`` gives the words so far."""
    _live[workflow_run_id] = _LiveCall(transcript)


def unregister(workflow_run_id: int) -> None:
    _live.pop(workflow_run_id, None)


def add_direct_talk(workflow_run_id: int, talk: dict[str, Any]) -> None:
    """A direct talk between the user and the other party is over."""
    call = _live.get(workflow_run_id)
    if call is not None:
        call.direct_talks.append(talk)


def progress(workflow_run_id: int) -> dict[str, Any] | None:
    """The call so far, or None when the call does not run in this process."""
    call = _live.get(workflow_run_id)
    if call is None:
        return None
    try:
        transcript = call.transcript()
    except Exception:  # noqa: BLE001 - progress must not break the call record
        transcript = ""
    return {
        "seconds": round(time.monotonic() - call.connected_at),
        "transcript": transcript,
        "direct_talks": list(call.direct_talks),
    }
