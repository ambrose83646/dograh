"""Keypad presses (DTMF) the agent sends to get through a phone menu.

On Twilio the carrier sends real presses (see ``twilio/native_keys.py``). On
other transports the tones go into the call audio, which only works for menus
that listen to the audio.
"""

import re
from typing import Any, Dict

KEYPAD_FUNCTION_NAME = "press_keys"
KEYPAD_CONTEXT_KEY = "keys_pressed"
LISTEN_FUNCTION_NAME = "keep_listening"
MAX_KEYS_PER_PRESS = 32
# A menu that loops can make a model press keys without end. Each key is half
# a second of call time, so the total for one call has a ceiling.
MAX_KEYS_PER_CALL = 200

_KEYS = re.compile(r"[0-9*#]+")
_SEPARATORS = re.compile(r"[\s\-.,()]")


class KeypadError(ValueError):
    """The requested keys cannot be sent. The text is for the model."""


def normalize_keys(raw: Any) -> str:
    """Return the keys to send, or raise with a reason the model can act on."""
    if not isinstance(raw, str):
        raise KeypadError("Give the keys as text, for example '2' or '4471#'.")
    keys = _SEPARATORS.sub("", raw)
    if not keys:
        raise KeypadError("No keys were given. Nothing was pressed.")
    if not _KEYS.fullmatch(keys):
        raise KeypadError(
            "Only the keys 0-9, * and # exist on a phone keypad. Nothing was "
            "pressed. Say words and letters aloud instead."
        )
    if len(keys) > MAX_KEYS_PER_PRESS:
        raise KeypadError(
            f"At most {MAX_KEYS_PER_PRESS} keys can be pressed at one time. "
            "Nothing was pressed."
        )
    return keys


def get_keypad_tool() -> Dict[str, Any]:
    return {
        "name": KEYPAD_FUNCTION_NAME,
        "description": (
            "Press keys on the phone keypad. Use it only when an automated "
            "phone menu or recording asks for a key press, for example "
            "'press 2 for appointments' or 'enter your account number, then "
            "pound'. Never use it when a person is talking to you. Send all "
            "keys of one answer in one call, in order. After the keys are "
            "pressed, stay silent and listen to what the menu says next."
        ),
        "properties": {
            "keys": {
                "type": "string",
                "description": (
                    "The keys to press, in order. Digits 0-9, * and # only. "
                    "Example: '2' or '4471#'."
                ),
            }
        },
        "required": ["keys"],
    }


def get_listen_tool() -> Dict[str, Any]:
    """A silent turn.

    Each thing the agent hears asks the model for an answer. With the keypad
    as the only silent action, a model that hears "one moment, please" presses
    a key again (measured). This gives it a correct way to do nothing.
    """
    return {
        "name": LISTEN_FUNCTION_NAME,
        "description": (
            "Say nothing, press nothing, and listen. Use it when a recording "
            "says to wait or to hold, when it confirms your keys ('thank "
            "you', 'one moment, please'), when hold music plays, or when the "
            "menu has not yet given the option you need. Never use it when a "
            "person waits for your answer."
        ),
        "properties": {},
        "required": [],
    }
