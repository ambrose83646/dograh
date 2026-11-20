"""End-to-end check: the agent brings the user into a call, and listens.

Maria signs up with her phone and verifies it as her caller ID. Her assistant
then places three real calls to a "bank" (the second approved test number,
which plays a script). In each call the bank refuses to continue with an
assistant and asks for Maria herself.

Ways the feature can fail, and the call that shows it:

1. The agent does not phone the user, or phones a wrong number.      (call 1)
2. The user joins, but the two do not hear each other.               (call 1:
   each side's words must be in the other side's audio, which the service
   writes down per channel)
3. The agent does not hear the direct talk: a fact that is said only there
   is missing from its result.                                        (call 1)
4. The agent hears the direct talk as if it was spoken to it, or speaks
   during it.                                                         (call 1)
5. The user hangs up and the other party is left with a dead line.    (call 1)
6. A voicemail box "joins" the call.                                  (call 2)
7. The user does not join and the other party waits without end.      (call 2)
8. The user says "assistant, leave the call" and the agent listens on,
   or speaks again.                                                   (call 3)

Only the two approved test numbers are dialled. Run it with the same
environment as verify.py.
"""

import argparse
import asyncio
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from verify import (  # noqa: E402
    Assistant,
    Report,
    TestPhone,
    account_from,
    spoken_digits,
    transcript_turns,
    wait_for_call,
    write_report,
)

TASK = (
    "Call the card services of Riverside Bank for Maria Lopez. Her card was "
    "damaged. Ask them to send a replacement card, and bring back the day on "
    "which it ships and the reference number of the order."
)
BANK_OPENING = (
    '<Pause length="1"/><Say>Riverside Bank, card services, this is Dana '
    'speaking. How can I help you?</Say><Pause length="11"/>'
    "<Say>I am sorry. I can not order a card with an assistant. I must speak "
    "with Maria Lopez herself, to check her identity. Can you get her on the "
    "line? I will hold.</Say>"
)
# The user's phone answers, hears the summary, and presses 1 after 6 seconds.
JOIN = '<Pause length="6"/><Play digits="1"/>'


def said(lines: list[dict], speaker: str) -> str:
    return " ".join(line["text"] for line in lines if line["speaker"] == speaker)


async def run(args, report: Report) -> None:
    run_id = datetime.now(UTC).strftime("%m%d%H%M%S")
    card = f"{random.randint(1000, 9999)}"
    reference = f"{random.randint(1000, 9999)}"
    ship_day = random.choice(["Tuesday", "Wednesday", "Thursday"])
    callback = f"555{random.randint(1000, 9999)}"
    secret = random.choice(["pineapple", "lighthouse", "butterfly"])
    operator = {"X-Operator-Token": args.operator_token}
    report.evidence.update(
        run_id=run_id, base_url=args.base_url, started_at=datetime.now(UTC).isoformat(),
        card_digits=card, reference=reference, ship_day=ship_day,
        callback_number=callback, secret_word=secret,
    )  # fmt: skip
    user_phone = TestPhone(
        args.test_phone, args.twilio_account_sid, args.twilio_auth_token
    )
    bank = TestPhone(args.bank_phone, args.twilio_account_sid, args.twilio_auth_token)
    maria = None

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60) as http:
        try:
            # --- Maria signs up with her phone and verifies it ----------------
            info = (await http.get("/api/v1/platform/info")).json()
            invite = None if info["signup_open"] else operator
            me = {"phone_number": user_phone.number}
            (
                await http.post(
                    "/api/v1/platform/operator/phone-identities/release",
                    headers=operator, json=me,
                )
            ).raise_for_status()  # fmt: skip
            seen = set(await user_phone.texts())
            (
                await http.post(
                    "/api/v1/platform/auth/start", json=me, headers=invite or {}
                )
            ).raise_for_status()
            code = (await user_phone.new_codes(seen) or ["000000"])[0]
            signed_up = await http.post(
                "/api/v1/platform/auth/verify",
                json={**me, "code": code}, headers=invite or {},
            )  # fmt: skip
            signed_up.raise_for_status()
            maria = await account_from(http, "Maria Lopez", signed_up.json())
            maria_ai = Assistant(args.base_url.rstrip("/") + "/mcp/", maria["api_key"])
            (
                await http.put(
                    f"/api/v1/platform/operator/accounts/{maria['organization_id']}/allowance",
                    headers=operator, json={"free_seconds": 1800},
                )
            ).raise_for_status()  # fmt: skip
            started = await maria_ai.call(
                "start_caller_id_verification", phone_number=user_phone.number
            )
            await user_phone.answer_with_code(started["validation_code"])
            status: dict = {}
            for _ in range(18):
                await asyncio.sleep(5)
                status = await maria_ai.call("get_account_status")
                if status["caller_id"]:
                    break
            await user_phone.hang_up()
            schema = await maria_ai.tool_schema("place_call")
            report.check(
                "Maria has a verified phone, and place_call lets her assistant "
                "turn the join feature off",
                status.get("caller_id") == user_phone.number
                and schema["properties"].get("allow_user_to_join", {}).get("default")
                is True,
                f"caller ID {status.get('caller_id')}",
            )

            async def call_bank(bank_script: str, user_script: str, timeout=240):
                await bank.answer_with_script(bank_script)
                await user_phone.answer_with_script(user_script)
                since = datetime.now(UTC)
                placed = await maria_ai.call(
                    "place_call", phone_number=bank.number, task=TASK,
                    on_behalf_of="Maria Lopez", call_reason="about a damaged card",
                )  # fmt: skip
                result = await wait_for_call(maria_ai, placed["call_id"], timeout)
                for _ in range(4):
                    if (result.get("result") or {}).get("outcome_summary"):
                        break
                    await asyncio.sleep(10)
                    result = await maria_ai.call(
                        "get_call_result", call_id=placed["call_id"]
                    )
                # The calls that Twilio made to the user's phone meanwhile.
                found = await user_phone.twilio.get(
                    f"/Accounts/{user_phone.account_sid}/Calls.json",
                    params={"To": user_phone.number, "PageSize": 20},
                )
                found.raise_for_status()
                to_user = [
                    {"from": c["from"], "status": c["status"], "seconds": int(c["duration"] or 0)}
                    for c in found.json()["calls"]
                    if datetime.strptime(c["date_created"], "%a, %d %b %Y %H:%M:%S %z") >= since.replace(microsecond=0)
                    and c["direction"] == "outbound-api"
                ]  # fmt: skip
                return result, to_user

            # --- Call 1: the user joins, the two talk, the user leaves --------
            first, to_user = await call_bank(
                BANK_OPENING
                + '<Pause length="28"/><Say>Hello Maria, this is Dana at card '
                "services. Please tell me the last four digits of the damaged "
                'card.</Say><Pause length="22"/>'
                "<Say>Thank you, that is correct. The new card ships on "
                f"{ship_day}. The reference number of the order is "
                f"{' '.join(reference)}.</Say>"
                '<Pause length="30"/><Say>Yes, that is all correct. Thank you. '
                'Goodbye.</Say><Pause length="20"/>',
                JOIN + '<Pause length="24"/><Say>Hello Dana, this is Maria Lopez. The '
                f"last four digits are {' '.join(card)}.</Say>"
                '<Pause length="30"/><Say>Thank you Dana. That is all I need. '
                "Goodbye.</Say><Hangup/>",
            )
            report.evidence["joined_call"] = first
            report.evidence["joined_call_user_leg"] = to_user
            talk = (first.get("direct_talk") or [{}])[0]
            lines = talk.get("lines") or []
            turns = transcript_turns(first.get("transcript", ""))
            agent_said = " ".join(t for r, t in turns if r == "assistant")
            agent_heard = " ".join(t for r, t in turns if r == "user")
            summary = str((first.get("result") or {}).get("outcome_summary") or "")
            report.check(
                "The agent phones the user's verified number from the service "
                "line, and the user joins with key 1",
                talk.get("user_joined") is True
                and len(to_user) == 1
                and to_user[0]["from"] == args.line_number
                and to_user[0]["seconds"] >= 40,
                f"calls to the user's phone: {to_user}",
            )
            report.check(
                "The user and the other party talk directly: each side's words "
                "are in the audio of the correct channel",
                card in spoken_digits(said(lines, "user"))
                and reference in spoken_digits(said(lines, "other_party"))
                and card not in spoken_digits(said(lines, "other_party"))
                and reference not in spoken_digits(said(lines, "user")),
                f"{len(lines)} lines in {talk.get('seconds')} s: "
                + " / ".join(f"{line['speaker']}: {line['text']}" for line in lines)[:400],
            )  # fmt: skip
            report.check(
                "The agent heard the direct talk: its result has the reference "
                "and the day, which were said only there",
                reference in spoken_digits(summary)
                and ship_day.lower() in summary.lower(),
                f"summary: {summary[:260]!r}",
            )
            report.check(
                "The agent took no part in the direct talk: the words were not "
                "spoken to it, and it did not answer them",
                card not in spoken_digits(agent_heard)
                and card not in spoken_digits(agent_said)
                and talk.get("assistant_listened_to_the_end") is True,
                f"agent heard: {agent_heard[-200:]!r}",
            )
            after = agent_said.lower().split("hold")[-1]
            report.check(
                "When the user hangs up, the agent continues with the other "
                "party and closes the call",
                talk.get("result") == "user_left"
                and first.get("status") == "completed"
                and (
                    reference in spoken_digits(after)
                    or ship_day.lower() in after
                    or "goodbye" in after
                    or "thank" in after
                )
                and "all correct" in agent_heard.lower(),
                f"{first.get('duration_seconds')} s; agent after the talk: {after[-220:]!r}",
            )

            # --- Call 2: a voicemail box answers the user's phone -------------
            second, to_user = await call_bank(
                BANK_OPENING
                + '<Pause length="75"/><Say>Then please tell her to call card '
                f"services at {' '.join(callback)}, before Friday.</Say>"
                '<Pause length="14"/><Say>Thank you. Goodbye.</Say><Pause length="15"/>',
                "<Say>Hi, this is Maria. I can not take your call. Please leave "
                'a message after the tone.</Say><Pause length="60"/>',
            )
            report.evidence["not_joined_call"] = second
            talk = (second.get("direct_talk") or [{}])[0]
            turns = transcript_turns(second.get("transcript", ""))
            agent_heard = " ".join(t for r, t in turns if r == "user")
            result_text = " ".join(
                str(v) for v in (second.get("result") or {}).values()
            )
            report.check(
                "A voicemail box on the user's phone does not join the call; "
                "the other party waits less than a minute and the agent returns",
                talk.get("user_joined") is False
                and talk.get("result") == "user_not_reached"
                and not talk.get("lines")
                and callback in spoken_digits(agent_heard),
                f"{talk.get('result')}; calls to the user's phone: {to_user}",
            )
            report.check(
                "After the user did not join, the agent takes the message and "
                "the result tells the user what to do",
                second.get("status") == "completed"
                and callback in spoken_digits(result_text),
                f"result: {result_text[:260]!r}",
            )

            # --- Call 3: the user sends the assistant away --------------------
            third, to_user = await call_bank(
                BANK_OPENING
                + '<Pause length="40"/><Say>Thank you Maria. I have what I '
                'need. Goodbye.</Say><Pause length="40"/>',
                JOIN + '<Pause length="10"/><Say>Hello Dana, this is Maria Lopez.</Say>'
                '<Pause length="2"/><Say>Assistant, leave the call.</Say>'
                f'<Pause length="9"/><Say>Dana, my security word is {secret}.</Say>'
                '<Pause length="12"/><Hangup/>',
                timeout=200,
            )
            report.evidence["sent_away_call"] = third
            talk = (third.get("direct_talk") or [{}])[0]
            lines = talk.get("lines") or []
            everything = (
                str(lines) + third.get("transcript", "") + str(third.get("result"))
            ).lower()
            turns = transcript_turns(third.get("transcript", ""))
            report.check(
                'After "assistant, leave the call" the agent stops listening: '
                "the words that follow are not in the call record",
                talk.get("result") == "assistant_told_to_leave"
                and talk.get("assistant_listened_to_the_end") is False
                and "maria lopez" in said(lines, "user").lower()
                and secret not in everything,
                f"lines: {' / '.join(line['text'] for line in lines)[:260]!r}",
            )
            report.check(
                "The talk continues without the agent, and the call ends when "
                "the user hangs up; the agent does not speak again",
                third.get("status") == "completed"
                and talk.get("seconds", 0) >= 25
                and "i have what i need" not in everything
                and (not turns or "hold" in turns[-1][1].lower() or turns[-1][0] == "user"),
                f"direct talk {talk.get('seconds')} s, call {third.get('duration_seconds')} s",
            )  # fmt: skip
        finally:
            await user_phone.hang_up()
            await bank.hang_up()
            if maria:
                closed = await http.post(
                    f"/api/v1/platform/operator/accounts/{maria['organization_id']}/close",
                    headers=operator,
                )
                print(f"closed the account: HTTP {closed.status_code}")
            released = await http.post(
                "/api/v1/platform/operator/phone-identities/release",
                headers=operator, json={"phone_number": user_phone.number},
            )  # fmt: skip
            print(f"released the test phone: HTTP {released.status_code}")
            await user_phone.twilio.aclose()
            await bank.twilio.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.getenv("VERIFY_BASE_URL", "http://localhost:8000")
    )
    parser.add_argument(
        "--operator-token", default=os.getenv("PLATFORM_OPERATOR_TOKEN", "")
    )
    parser.add_argument("--test-phone", default=os.getenv("VERIFY_TEST_PHONE", ""))
    parser.add_argument(
        "--bank-phone",
        default=os.getenv("VERIFY_BANK_PHONE", ""),
        help="The second approved test number. It plays the called party. It "
        "must be in the main Twilio account, not assigned to an account.",
    )
    parser.add_argument(
        "--line-number",
        default=os.getenv("VERIFY_LINE_NUMBER", ""),
        help="The service's PLATFORM_CONFERENCE_FROM.",
    )
    parser.add_argument(
        "--twilio-account-sid", default=os.getenv("PLATFORM_TWILIO_ACCOUNT_SID", "")
    )
    parser.add_argument(
        "--twilio-auth-token", default=os.getenv("PLATFORM_TWILIO_AUTH_TOKEN", "")
    )
    parser.add_argument("--out", default="platform_verification/results/conference")
    args = parser.parse_args()
    required = (
        args.operator_token, args.test_phone, args.bank_phone, args.line_number,
        args.twilio_account_sid, args.twilio_auth_token,
    )  # fmt: skip
    if not all(required):
        print("Set the operator token, the two test numbers, the line number, "
              "and the Twilio credentials. See --help.")  # fmt: skip
        return 2
    report = Report()
    started = time.monotonic()
    try:
        asyncio.run(run(args, report))
    finally:
        report.evidence["seconds"] = round(time.monotonic() - started)
        write_report(report, Path(args.out))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
