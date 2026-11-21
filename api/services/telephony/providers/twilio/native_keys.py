"""Real keypad presses (DTMF) on a Twilio call that runs on a media stream.

A media stream carries audio only. Tones that are mixed into the audio are not
keypad presses for the far end: a Twilio ``<Gather>`` ignores them (measured),
and so do carrier menus that take presses as signalling events. Only Twilio
itself can send a press, with ``<Play digits>``, and that needs the call's
TwiML. So a press replaces the call's TwiML with "play these digits, then
connect the stream again". Twilio closes the media socket, plays the digits and
dials the same socket URL again. ``ResumableTwilioStream`` hides this from the
pipeline: it holds the pipeline's side of the socket open across the gap and
continues on the new socket.

Ways this can fail, and what happens:

- The other side ends the call during the press. No new socket arrives; after
  ``RECONNECT_TIMEOUT`` the pipeline sees the disconnect and the call ends as a
  normal remote hang-up.
- Twilio refuses the TwiML update (the call is already over). The press raises,
  the stream is not waiting for a socket, and a later disconnect ends the call
  at once.
- A second press starts before the first is done. It is refused; the digits of
  two presses must not interleave.
- Someone else opens the socket URL of a running call. It is adopted only while
  a press waits for it and only if its ``start`` names this call's SID.
- The new socket lands on a different server process. This registry is
  per-process, so the press fails after the timeout and the call ends. The
  platform deployment runs one web process.
- Audio that the far end says while the digits play (about 0.5 s per digit plus
  the reconnect) is not heard.

The stream can also give the call's audio to another listener (``on_audio``):
the platform uses it to connect the call with the account's user for a direct
talk (``api.services.platform.conference``). The pipeline then gets silence.
"""

import asyncio
import base64
import json
from typing import Any, Awaitable, Callable

from loguru import logger
from starlette.websockets import WebSocket, WebSocketState

RECONNECT_TIMEOUT = 15.0
# Twilio plays a digit for about half a second.
SECONDS_PER_DIGIT = 0.5

_streams: dict[int, "ResumableTwilioStream"] = {}


class KeyPressFailed(RuntimeError):
    """The digits were not sent, or the call did not come back after them."""


class ResumableTwilioStream:
    """The media socket of one call, as the pipeline sees it.

    It has the part of the Starlette ``WebSocket`` interface that the pipecat
    websocket transport uses.
    """

    def __init__(
        self,
        websocket: WebSocket,
        *,
        workflow_run_id: int,
        stream_sid: str,
        call_sid: str,
        redirect: Callable[[str], Awaitable[None]],
    ):
        self._ws = websocket
        self._workflow_run_id = workflow_run_id
        # The serializer writes this SID into every message it sends.
        self._first_stream_sid = stream_sid
        self._stream_sid = stream_sid
        self._call_sid = call_sid
        self._redirect = redirect
        self._next_socket: asyncio.Future | None = None
        self._digits_seconds = 0.0
        self._resumed = asyncio.Event()
        self._released: list[asyncio.Event] = []
        # While set, the far end's audio goes here and the pipeline gets silence.
        self.on_audio: Callable[[str], None] | None = None
        # Called one time when the far end is gone.
        self.on_gone: Callable[[], None] | None = None
        # While set, nothing from the pipeline reaches the call.
        self.pipeline_muted = False

    # --- pipeline side -----------------------------------------------------

    @property
    def client_state(self) -> WebSocketState:
        if self._next_socket is not None:
            return WebSocketState.CONNECTED
        return self._ws.client_state

    @property
    def application_state(self) -> WebSocketState:
        if self._next_socket is not None:
            return WebSocketState.CONNECTED
        return self._ws.application_state

    async def receive(self) -> dict[str, Any]:
        while True:
            message = await self._ws.receive()
            if message["type"] != "websocket.disconnect":
                if self.on_audio is not None and message.get("text"):
                    return self._divert(message)
                return message
            waiting = self._next_socket
            if waiting is None:
                self._report_gone()
                return message
            try:
                self._ws, self._stream_sid = await asyncio.wait_for(
                    waiting, RECONNECT_TIMEOUT + self._digits_seconds
                )
            except (asyncio.TimeoutError, asyncio.CancelledError, KeyPressFailed):
                self._next_socket = None
                logger.warning(
                    f"[run {self._workflow_run_id}] the call did not come back "
                    "after a key press"
                )
                self._report_gone()
                return message
            self._next_socket = None
            self._resumed.set()

    def _report_gone(self) -> None:
        on_gone, self.on_gone = self.on_gone, None
        if on_gone is not None:
            on_gone()

    def _divert(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            event = json.loads(message["text"])
            if event.get("event") != "media":
                return message
            payload = event["media"]["payload"]
            self.on_audio(payload)
            event["media"]["payload"] = base64.b64encode(
                b"\xff" * (len(payload) * 3 // 4 - payload.count("="))
            ).decode()
            return {**message, "text": json.dumps(event)}
        except Exception as e:
            logger.warning(f"[run {self._workflow_run_id}] audio not diverted: {e}")
            return message

    async def send_audio(self, payload: str) -> None:
        """Send mu-law audio (base64) to the far end, not from the pipeline."""
        await self._send_event({"event": "media", "media": {"payload": payload}})

    async def clear_audio(self) -> None:
        """Drop the audio that the far end has not heard yet."""
        await self._send_event({"event": "clear"})

    async def _send_event(self, event: dict[str, Any]) -> None:
        if self._next_socket is not None:
            return
        try:
            await self._ws.send_text(
                json.dumps({**event, "streamSid": self._stream_sid})
            )
        except Exception as e:
            logger.debug(f"[run {self._workflow_run_id}] audio not sent: {e}")

    async def send_text(self, data: str) -> None:
        if self._next_socket is not None or self.pipeline_muted:
            return
        if self._stream_sid != self._first_stream_sid:
            data = data.replace(self._first_stream_sid, self._stream_sid)
        await self._ws.send_text(data)

    async def send_bytes(self, data: bytes) -> None:
        if self._next_socket is None:
            await self._ws.send_bytes(data)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        if self._next_socket is not None and not self._next_socket.done():
            self._next_socket.cancel()
        await self._ws.close(code=code, reason=reason)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ws, name)

    # --- key presses -------------------------------------------------------

    async def press(self, keys: str) -> None:
        """Send the keys as real presses. Returns when the audio is back."""
        if self._next_socket is not None:
            raise KeyPressFailed("An earlier key press is not finished.")
        self._digits_seconds = len(keys) * SECONDS_PER_DIGIT
        self._resumed.clear()
        self._next_socket = asyncio.get_running_loop().create_future()
        try:
            await self._redirect(keys)
        except Exception as e:
            self._next_socket = None
            raise KeyPressFailed(str(e)) from e
        try:
            await asyncio.wait_for(
                self._resumed.wait(), RECONNECT_TIMEOUT + self._digits_seconds
            )
        except asyncio.TimeoutError as e:
            raise KeyPressFailed("The call did not come back.") from e

    # --- route side --------------------------------------------------------

    def _adopt(self, websocket: WebSocket, stream_sid: str) -> asyncio.Event:
        released = asyncio.Event()
        self._released.append(released)
        self._next_socket.set_result((websocket, stream_sid))
        return released

    def _finish(self) -> None:
        for released in self._released:
            released.set()


async def run_with_native_keys(
    stream: ResumableTwilioStream, run: Callable[[], Awaitable[None]]
) -> None:
    """Run the call's pipeline with key presses available for its run id."""
    _streams[stream._workflow_run_id] = stream
    try:
        await run()
    finally:
        _streams.pop(stream._workflow_run_id, None)
        # A direct talk must not continue when the call's pipeline is over.
        stream._report_gone()
        stream._finish()


def stream_for_run(workflow_run_id: int) -> ResumableTwilioStream | None:
    return _streams.get(workflow_run_id)


def presser_for_run(workflow_run_id: int) -> Callable[[str], Awaitable[None]] | None:
    stream = _streams.get(workflow_run_id)
    return stream.press if stream else None


async def adopt_reconnect(workflow_run_id: int, websocket: WebSocket) -> bool:
    """Give a new media socket to the running call that waits for it.

    Returns False when no call of this run waits for a socket; the caller then
    handles the socket as a new call. Returns True when the socket was used
    (or refused) here; it then stays open until the call is over.
    """
    stream = _streams.get(workflow_run_id)
    if stream is None or stream._next_socket is None or stream._next_socket.done():
        return False
    try:
        connected = json.loads(await asyncio.wait_for(websocket.receive_text(), 10))
        start = json.loads(await asyncio.wait_for(websocket.receive_text(), 10))
        stream_sid = start["start"]["streamSid"]
        call_sid = start["start"]["callSid"]
    except Exception as e:
        logger.warning(
            f"[run {workflow_run_id}] bad media socket after a key press: {e}"
        )
        await websocket.close(code=4400, reason="Expected stream start")
        return True
    if connected.get("event") != "connected" or call_sid != stream._call_sid:
        logger.warning(
            f"[run {workflow_run_id}] media socket after a key press is not this call"
        )
        await websocket.close(code=4403, reason="Not this call")
        return True
    if stream._next_socket is None or stream._next_socket.done():
        await websocket.close(code=4409, reason="Call not waiting")
        return True
    released = stream._adopt(websocket, stream_sid)
    await released.wait()
    return True
