"""Check the day limit of sign-in codes, the exempt numbers, and the operator reset.

The ways in which this can fail, written before the code:

1. An exempt number is stopped by the day limit.
2. An exempt number also loses the one-minute wait.
3. The exemption applies to a number that is not in the list.
4. The reset works without the operator token.
5. The reset clears the day count but not the wait, or the reverse.
6. The reset removes a code that the phone already has.
7. The reset disconnects the phone from its account, as "release" does.

The service must run with PLATFORM_OTP_DAILY_PER_NUMBER=2 and with
PLATFORM_OTP_EXEMPT_NUMBERS set to the exempt test number. The run sends
six texts and takes about three minutes.
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from verify import Report, TestPhone, account_from, write_report  # noqa: E402

START = "/api/v1/platform/auth/start"
VERIFY = "/api/v1/platform/auth/verify"
RELEASE = "/api/v1/platform/operator/phone-identities/release"
RESET = "/api/v1/platform/operator/phone-identities/reset-code-limit"
TOO_MANY = "Too many codes"
WAIT = "Wait one minute"


async def run(args, report: Report) -> None:
    operator = {"X-Operator-Token": args.operator_token}
    phone = TestPhone(args.test_phone, args.twilio_account_sid, args.twilio_auth_token)
    limited = {"phone_number": args.test_phone}
    exempt = {"phone_number": args.exempt_phone}
    report.evidence.update(
        base_url=args.base_url, started_at=datetime.now(UTC).isoformat(),
        limited_number=args.test_phone, exempt_number=args.exempt_phone,
    )  # fmt: skip
    account = None

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60) as http:

        async def start(body: dict) -> tuple[int, str]:
            response = await http.post(START, json=body, headers=operator)
            return response.status_code, response.json().get("detail", "")

        async def sign_in(code: str) -> httpx.Response:
            return await http.post(
                VERIFY, json={**limited, "code": code}, headers=operator
            )

        try:
            # A clean start: both counts are empty and the phone has no account.
            for body in (limited, exempt):
                (await http.post(RELEASE, headers=operator, json=body)).raise_for_status()  # fmt: skip
            seen = set(await phone.texts())

            # --- Minute 0: the first code for each number ---------------------
            first = await start(limited)
            exempt_first = await start(exempt)
            exempt_at_once = await start(exempt)
            code = (await phone.new_codes(seen) or ["000000"])[0]
            seen = set(await phone.texts())
            signed_up = await sign_in(code)
            signed_up.raise_for_status()
            account = await account_from(http, "Limit Test", signed_up.json())
            report.check(
                "An exempt number keeps the one-minute wait between codes",
                exempt_first[0] == 200
                and exempt_at_once[0] == 429
                and WAIT in exempt_at_once[1],
                f"first {exempt_first[0]}; at once: {exempt_at_once}",
            )

            # --- Minute 1: the second code, the last one of the day -----------
            await asyncio.sleep(62)
            second = await start(limited)
            exempt_second = await start(exempt)

            # --- Minute 2: the third request is over the limit of two ---------
            await asyncio.sleep(62)
            third = await start(limited)
            exempt_third = await start(exempt)
            report.check(
                "A number that is not exempt gets two codes, then the day limit stops it",
                first[0] == 200
                and second[0] == 200
                and third[0] == 429
                and TOO_MANY in third[1],
                f"codes: {first[0]}, {second[0]}; third: {third}",
            )
            report.check(
                "The exempt number gets a third code on the same day",
                exempt_second[0] == 200 and exempt_third[0] == 200,
                f"second {exempt_second[0]}, third {exempt_third}",
            )

            # --- The reset needs the operator token ---------------------------
            stranger = await http.post(RESET, json=limited)
            wrong = await http.post(
                RESET, json=limited, headers={"X-Operator-Token": "not-the-token"}
            )
            still = await start(limited)
            report.check(
                "The reset does nothing without the operator token",
                stranger.status_code == 404
                and wrong.status_code == 404
                and still[0] == 429,
                f"no token {stranger.status_code}, wrong token {wrong.status_code}, "
                f"next request {still}",
            )

            # --- The operator resets the number -------------------------------
            # The refused request above started a new one-minute wait. A code
            # at once shows that the reset cleared the wait and the day count.
            seen = set(await phone.texts())
            reset = await http.post(RESET, json=limited, headers=operator)
            after = await start(limited)
            fresh = (await phone.new_codes(seen) or ["000000"])[0]
            report.check(
                "After the operator reset, the number gets a code at once: "
                "the day count and the wait are both clear",
                reset.status_code == 200
                and reset.json() == {"phone_number": args.test_phone, "reset": True}
                and after[0] == 200
                and fresh != "000000",
                f"reset {reset.status_code} {reset.text[:80]}; next request {after}",
            )

            # --- A second reset while that code waits in the phone ------------
            (await http.post(RESET, json=limited, headers=operator)).raise_for_status()
            back = await sign_in(fresh)
            same_account = (
                back.status_code == 200
                and back.json()["user"]["organization_id"] == account["organization_id"]
            )
            key_works = await http.get(
                "/api/v1/platform/account", headers={"X-API-Key": account["api_key"]}
            )
            report.check(
                "The reset keeps the code that the phone has, and the phone "
                "stays connected to its account and its access key",
                same_account and key_works.status_code == 200,
                f"sign-in {back.status_code}; account before "
                f"{account['organization_id']}, after "
                f"{back.json().get('user', {}).get('organization_id') if back.status_code == 200 else None}; "
                f"key {key_works.status_code}",
            )
        finally:
            if account:
                closed = await http.post(
                    f"/api/v1/platform/operator/accounts/{account['organization_id']}/close",
                    headers=operator,
                )
                print(f"closed the account: HTTP {closed.status_code}")
            for body in (limited, exempt):
                released = await http.post(RELEASE, headers=operator, json=body)
                print(f"released {body['phone_number']}: HTTP {released.status_code}")
            await phone.twilio.aclose()


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
        "--exempt-phone",
        default=os.getenv("VERIFY_EXEMPT_PHONE", ""),
        help="The second approved test number. It must be in the service's "
        "PLATFORM_OTP_EXEMPT_NUMBERS.",
    )
    parser.add_argument(
        "--twilio-account-sid", default=os.getenv("PLATFORM_TWILIO_ACCOUNT_SID", "")
    )
    parser.add_argument(
        "--twilio-auth-token", default=os.getenv("PLATFORM_TWILIO_AUTH_TOKEN", "")
    )
    parser.add_argument("--out", default="platform_verification/results/sign-in-limit")
    args = parser.parse_args()
    required = (
        args.operator_token, args.test_phone, args.exempt_phone,
        args.twilio_account_sid, args.twilio_auth_token,
    )  # fmt: skip
    if not all(required):
        print("Set the operator token, the two test numbers, and the Twilio "
              "credentials. See --help.")  # fmt: skip
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
    raise SystemExit(main())
