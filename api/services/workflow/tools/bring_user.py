"""The tool that brings the account's user into a running call.

The work is in ``api.services.platform.conference``.
"""

from typing import Any, Dict

BRING_USER_FUNCTION_NAME = "bring_user_on_line"
BRING_USER_CONTEXT_KEY = "direct_talk"


def get_bring_user_tool() -> Dict[str, Any]:
    return {
        "name": BRING_USER_FUNCTION_NAME,
        "description": (
            "Phone the person you call for and connect them with the person "
            "on this call, so that the two talk directly. Use it only when "
            "the other person will continue only with your client in person "
            "(an identity check, a decision or a payment that only the client "
            "can make), or asks to speak with your client. Before you use "
            "it, tell the other person that you will get your client on the "
            "line and ask them to hold. The other person hears a ringing "
            "tone while your client's phone rings. During the direct talk "
            "you cannot speak; you hear it, and the tool gives you what was "
            "said. The tool returns when your client has left the call or "
            "did not answer."
        ),
        "properties": {
            "summary": {
                "type": "string",
                "description": (
                    "One or two short sentences, spoken to your client before "
                    "they join: who is on the line and what they need from "
                    "the client. Example: 'Riverside Dental is on the line. "
                    "They need you to confirm your date of birth.'"
                ),
            }
        },
        "required": ["summary"],
    }
