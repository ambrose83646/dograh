"""Bring the account's user into a running outbound call.

The agent is on a call for the user. The other party asks for something that
the agent cannot do. The agent then calls the user's verified phone, says what
the matter is, and connects the user with the other party. The two talk
directly; the agent says nothing, listens, and writes down what is said. When
the user hangs up, the agent continues the call with the other party.

How the audio goes. Each Twilio subaccount has its own conferences, and an
account's subaccount has no number that can call the user (its only caller ID
is the user's own number). So the user is called from the operator's main
account, and this server carries the audio between the two calls: what the
other party says goes to the user's call, and the reverse. The other party's
call stays on the agent's media stream the whole time, so nothing has to be
handed over and taken back.

Only the account's verified number can be called. A number from the model or
from the task would make the service a free phone relay.

Ways this can fail, and what happens:

- The user does not answer, or does not press 1 (a voicemail box cannot press
  a key). The other party hears a ringing tone for at most
  ``JOIN_WAIT_SECONDS``; then the agent continues with "not reached".
- The other party ends the call while it waits, or during the direct talk.
  The user's call is ended too. The words so far are in the call result.
- The user ends the call. The agent continues with the other party and knows
  what was said.
- The user says "assistant, leave the call". The listening stops and nothing
  more is written down. The two talk on; when the user hangs up, the call ends.
- The time limit passes. The user's call is ended and the agent closes the call.
- Twilio refuses the call to the user. The agent continues with "failed".
- The transcription fails. The direct talk still works; the words are missing
  from the result.
- The server restarts. The state is in memory and is lost, as the call is.
"""

import asyncio
import base64
import json
import math
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable
from xml.sax.saxutils import escape

import websockets
from loguru import logger
from starlette.websockets import WebSocket

from api.db import db_client
from api.services.platform import twilio_accounts
from api.services.platform.provisioning import get_platform_account
from api.services.platform.settings import get_platform_settings
from api.services.telephony.providers.twilio.native_keys import (
    ResumableTwilioStream,
    stream_for_run,
)
from api.utils.common import get_backend_endpoints

# How long the other party waits for the user to join.
JOIN_WAIT_SECONDS = 45
# A call that the user joined can run this long in total.
MAX_CALL_SECONDS = 1800
RING_DELAY_SECONDS = 4
MAX_SUMMARY_CHARS = 400
MAX_TALK_CHARS = 12000

_LEAVE = re.compile(
    r"\b(?:assistant|a\.?i\.?)\b[^?!]{0,40}\b(?:leave|drop off|hang up|disconnect"
    r"|stop listening|you can go|go now)\b",
    re.IGNORECASE,
)
_FRAME = 160  # 20 ms of 8 kHz mu-law
_SILENCE = b"\xff" * _FRAME
_DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen?model=nova-3&language=multi"
    "&encoding=mulaw&sample_rate=8000&channels=2&multichannel=true"
    "&smart_format=true&interim_results=false"
)

_conferences: dict[str, "Conference"] = {}
_by_run: dict[int, "Conference"] = {}


def _mulaw(sample: int) -> int:
    """One 16-bit sample as G.711 mu-law."""
    sign = 0x80 if sample < 0 else 0
    sample = min(abs(sample), 32635) + 0x84
    exponent, mask = 7, 0x4000
    while exponent > 0 and not sample & mask:
        exponent -= 1
        mask >>= 1
    return ~(sign | (exponent << 4) | ((sample >> (exponent + 3)) & 0x0F)) & 0xFF


def _ringing_tone() -> list[str]:
    """The North American ringing tone, in one-second pieces: 2 s on, 4 s off."""
    tone = bytes(
        _mulaw(
            int(
                2500
                * (
                    math.sin(2 * math.pi * 440 * n / 8000)
                    + math.sin(2 * math.pi * 480 * n / 8000)
                )
            )
        )
        for n in range(8000)
    )
    on = base64.b64encode(tone).decode()
    off = base64.b64encode(b"\xff" * 8000).decode()
    return [on, on, off, off, off, off]


_RINGING: list[str] = []


class _Transcriber:
    """Two-channel transcription: channel 0 the other party, channel 1 the user."""

    def __init__(self, conference: "Conference"):
        self._conference = conference
        self._buffers = (bytearray(), bytearray())
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=500)
        self._task: asyncio.Task | None = None
        self.stopped = False
        self._chars = 0

    def feed(self, channel: int, audio: bytes) -> None:
        if self.stopped:
            return
        if self._task is None:
            self._task = asyncio.create_task(self._run())
        mine, other = self._buffers[channel], self._buffers[1 - channel]
        mine += audio
        # One side of the audio stopped: the other side must not wait for it.
        if len(mine) > len(other) + 20 * _FRAME:
            other += _SILENCE * ((len(mine) - len(other)) // _FRAME)
        first, second = self._buffers
        size = min(len(first), len(second)) // _FRAME * _FRAME
        if not size:
            return
        pair = bytearray(size * 2)
        pair[0::2] = first[:size]
        pair[1::2] = second[:size]
        del first[:size], second[:size]
        try:
            self._queue.put_nowait(bytes(pair))
        except asyncio.QueueFull:
            self.stopped = True

    async def _run(self) -> None:
        conference = self._conference
        try:
            async with websockets.connect(
                _DEEPGRAM_URL,
                additional_headers={
                    "Authorization": f"Token {get_platform_settings().deepgram_api_key}"
                },
                open_timeout=10,
            ) as socket:
                reader = asyncio.create_task(self._read(socket))
                try:
                    while (audio := await self._queue.get()) is not None:
                        await socket.send(audio)
                    await socket.send(json.dumps({"type": "CloseStream"}))
                    # The last words arrive after the audio ends.
                    await asyncio.wait_for(asyncio.shield(reader), 4)
                finally:
                    reader.cancel()
        except Exception as e:
            self.stopped = True
            logger.warning(
                f"Conference {conference.token[:8]}: transcription ended "
                f"({type(e).__name__})"
            )

    async def _read(self, socket) -> None:
        conference = self._conference
        recent, recent_at = "", 0.0
        async for raw in socket:
            message = json.loads(raw)
            if message.get("type") != "Results" or not message.get("is_final"):
                continue
            text = message["channel"]["alternatives"][0]["transcript"].strip()
            if not text:
                continue
            speaker = "other_party" if message["channel_index"][0] == 0 else "user"
            if self._chars < MAX_TALK_CHARS:
                self._chars += len(text)
                conference.lines.append(
                    {
                        "speaker": speaker,
                        "text": text,
                        "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                    }
                )
            if speaker != "user":
                continue
            # The transcription can split one sentence: "Assistant," and
            # "leave the call." So the last words count too, for a short time.
            now = time.monotonic()
            if now - recent_at > 4:
                recent = ""
            recent, recent_at = f"{recent} {text}"[-200:], now
            if _LEAVE.search(recent):
                conference.assistant_left = True
                self.stopped = True
                return

    async def close(self) -> None:
        self.stopped = True
        if self._task is not None:
            await self._queue.put(None)
            try:
                await asyncio.wait_for(self._task, 6)
            except Exception:
                self._task.cancel()


@dataclass
class Conference:
    token: str
    stream: ResumableTwilioStream
    summary: str
    user_call_sid: str | None = None
    # Why the user did not join: no_answer, declined.
    not_joined_reason: str = "no_answer"
    assistant_left: bool = False
    person_present: bool = True
    joined_at: float | None = None
    ended_at: float | None = None
    lines: list[dict[str, str]] = field(default_factory=list)
    joined: asyncio.Event = field(default_factory=asyncio.Event)
    # The user's call is over, or the other party's call is.
    over: asyncio.Event = field(default_factory=asyncio.Event)
    to_user: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=250))
    transcriber: _Transcriber | None = None

    def end(self) -> None:
        if self.joined_at is not None and self.ended_at is None:
            self.ended_at = time.monotonic()
        self.over.set()

    def person_audio(self, payload: str) -> None:
        """What the other party says: to the user, and to the transcription."""
        if not self.joined.is_set() or self.over.is_set():
            return
        try:
            self.to_user.put_nowait(payload)
        except asyncio.QueueFull:
            pass
        if self.transcriber is not None:
            self.transcriber.feed(0, base64.b64decode(payload))

    def person_gone(self) -> None:
        self.person_present = False
        self.end()


async def user_number(
    organization_id: int, account: dict[str, Any] | None
) -> str | None:
    """The phone the user proved to own: the caller ID, else the sign-in phone."""
    if account and account.get("caller_id"):
        return account["caller_id"]
    organization = await db_client.get_organization_by_id(organization_id)
    provider_id = getattr(organization, "provider_id", "") or ""
    prefix = "org_phone_"
    return provider_id[len(prefix) :] if provider_id.startswith(prefix) else None


def _line_number() -> str | None:
    """The operator's number that calls the user."""
    return get_platform_settings().conference_from or None


async def available(organization_id: int, called_number: str | None) -> bool:
    """True when this account's user can be brought into a call to this number."""
    number = await user_number(
        organization_id, await get_platform_account(organization_id)
    )
    line = _line_number()
    return bool(line and number and number not in (called_number, line))


async def _ring(conference: Conference) -> None:
    if not _RINGING:
        _RINGING.extend(_ringing_tone())
    # The agent's "please hold" is still playing.
    await asyncio.sleep(RING_DELAY_SECONDS)
    second = 0
    while True:
        await conference.stream.send_audio(_RINGING[second % len(_RINGING)])
        second += 1
        await asyncio.sleep(1)


async def _either(first: asyncio.Event, second: asyncio.Event, seconds: float) -> None:
    waits = [asyncio.ensure_future(e.wait()) for e in (first, second)]
    try:
        await asyncio.wait(waits, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for wait in waits:
            wait.cancel()


async def bring_in_user(
    *,
    workflow_run_id: int,
    organization_id: int,
    called_number: str | None,
    summary: str,
    max_seconds: float,
    on_join: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Run one direct talk. Returns when the agent has the call again, or it is over.

    The result has ``status``: ``not_available``, ``failed``,
    ``user_not_reached``, ``user_left``, ``assistant_told_to_leave``,
    ``time_limit``, or ``call_ended``.
    """
    stream = stream_for_run(workflow_run_id)
    number = await user_number(
        organization_id, await get_platform_account(organization_id)
    )
    line = _line_number()
    if stream is None or not line or not number or number in (called_number, line):
        return {"status": "not_available"}

    conference = Conference(
        token=secrets.token_urlsafe(32),
        stream=stream,
        summary=" ".join((summary or "").split())[:MAX_SUMMARY_CHARS],
    )
    conference.transcriber = _Transcriber(conference)
    _conferences[conference.token] = conference
    _by_run[workflow_run_id] = conference
    backend, _ = await get_backend_endpoints()
    path = f"{backend}/api/v1/platform/conference/{conference.token}"
    ringing = None
    time_limit = False
    stream.on_audio = conference.person_audio
    stream.on_gone = conference.person_gone
    try:
        try:
            conference.user_call_sid = await twilio_accounts.create_call(
                to=number,
                from_=line,
                url=f"{path}/user",
                status_callback=f"{path}/status",
                timeout=25,
            )
        except Exception as e:
            logger.warning(f"Conference: the user was not called ({e})")
            return {"status": "failed"}
        ringing = asyncio.create_task(_ring(conference))
        await _either(conference.joined, conference.over, JOIN_WAIT_SECONDS)
        ringing.cancel()
        await stream.clear_audio()
        if conference.joined.is_set():
            if on_join is not None:
                on_join()
            try:
                await asyncio.wait_for(conference.over.wait(), max_seconds)
            except asyncio.TimeoutError:
                time_limit = True
    finally:
        if ringing is not None:
            ringing.cancel()
        stream.on_audio = None
        stream.on_gone = None
        stream.pipeline_muted = False
        conference.end()
        _conferences.pop(conference.token, None)
        _by_run.pop(workflow_run_id, None)
        await conference.transcriber.close()
        if conference.user_call_sid:
            # Never leave the user's phone connected to nothing.
            try:
                await twilio_accounts.end_call(conference.user_call_sid)
            except Exception as e:
                logger.info(f"Conference: the user's call was not ended ({e})")

    if not conference.person_present:
        status = "call_ended"
    elif not conference.joined.is_set():
        status = "user_not_reached"
    elif time_limit:
        status = "time_limit"
    elif conference.assistant_left:
        status = "assistant_told_to_leave"
    else:
        status = "user_left"
    result: dict[str, Any] = {
        "status": status,
        "user_joined": conference.joined.is_set(),
    }
    if status == "user_not_reached":
        result["reason"] = conference.not_joined_reason
    if conference.joined_at is not None:
        result["direct_talk_seconds"] = round(
            (conference.ended_at or time.monotonic()) - conference.joined_at
        )
        result["assistant_listened_to_the_end"] = not conference.assistant_left
        result["direct_talk"] = conference.lines
    return result


def direct_talk_now(workflow_run_id: int) -> dict[str, Any] | None:
    """The direct talk that runs now in this call, for a progress report."""
    conference = _by_run.get(workflow_run_id)
    if conference is None:
        return None
    if conference.joined_at is None:
        return {"state": "calling_the_user"}
    return {
        "state": "user_on_the_line",
        "seconds": round(time.monotonic() - conference.joined_at),
        "assistant_is_listening": not conference.assistant_left,
        "lines": list(conference.lines),
    }


# --- Twilio's requests for the user's call ----------------------------------


def _say_and_hang_up(words: str) -> str:
    return f"<Response><Say>{escape(words)}</Say><Hangup/></Response>"


def _waiting(token: str) -> Conference | None:
    conference = _conferences.get(token)
    if conference is None or conference.over.is_set() or conference.joined.is_set():
        return None
    return conference


def user_answer_twiml(token: str, backend: str) -> str:
    """Spoken to the user's phone when it answers. A key press joins the call."""
    conference = _waiting(token)
    if conference is None:
        return _say_and_hang_up(
            "This is your AI assistant. The other person ended the call. Goodbye."
        )
    words = escape(
        "Hello. This is your AI assistant. I am on a call for you, and I need "
        f"you on the line. {conference.summary} To join the call now, press 1. "
        "After you join, I listen and do not speak. To make me stop listening, "
        "say: assistant, leave the call."
    )
    action = f"{backend}/api/v1/platform/conference/{token}/join"
    gather = (
        f'<Gather numDigits="1" timeout="6" action="{action}" method="POST">'
        f"<Say>{words}</Say></Gather>"
    )
    return (
        f"<Response>{gather}{gather}"
        "<Say>No key was pressed. Goodbye.</Say><Hangup/></Response>"
    )


def user_join_twiml(token: str, digits: str, wss_backend: str) -> str:
    conference = _waiting(token)
    if conference is None:
        return _say_and_hang_up("The other person ended the call. Goodbye.")
    if digits != "1":
        conference.not_joined_reason = "declined"
        conference.end()
        return _say_and_hang_up("You did not join the call. Goodbye.")
    url = f"{wss_backend}/api/v1/platform/conference/{token}/media"
    return f'<Response><Connect><Stream url="{url}"></Stream></Connect></Response>'


def user_call_completed(token: str) -> None:
    conference = _conferences.get(token)
    if conference is not None:
        conference.end()


async def user_media(token: str, websocket: WebSocket) -> None:
    """The media stream of the user's call: one side of the direct talk."""
    conference = _waiting(token)
    if conference is None:
        await websocket.close(code=4404, reason="No such call")
        return
    await websocket.accept()
    sender = None
    try:
        while True:
            message = json.loads(await websocket.receive_text())
            event = message.get("event")
            if event == "start":
                if message["start"].get("callSid") != conference.user_call_sid:
                    await websocket.close(code=4403, reason="Not this call")
                    return
                stream_sid = message["start"]["streamSid"]
                conference.joined_at = time.monotonic()
                # From here the agent neither hears the call nor speaks in it.
                conference.stream.pipeline_muted = True
                await conference.stream.clear_audio()
                conference.joined.set()
                sender = asyncio.create_task(
                    _send_to_user(conference, websocket, stream_sid)
                )
            elif event == "media" and sender is not None:
                if conference.over.is_set():
                    break
                payload = message["media"]["payload"]
                await conference.stream.send_audio(payload)
                conference.transcriber.feed(1, base64.b64decode(payload))
            elif event == "stop":
                break
    except Exception as e:
        logger.debug(f"Conference: the user's audio ended ({type(e).__name__})")
    finally:
        if sender is not None:
            sender.cancel()
        conference.end()


async def _send_to_user(
    conference: Conference, websocket: WebSocket, stream_sid: str
) -> None:
    while True:
        payload = await conference.to_user.get()
        await websocket.send_text(
            json.dumps(
                {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": payload},
                }
            )
        )
