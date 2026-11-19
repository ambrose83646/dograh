# Calling platform verification

`verify.py` tests a running calling service from the outside, the way two users
and their AI assistants use it. It makes real phone calls.

## What one run does

1. Confirms the MCP endpoint refuses a client with no key and with a made-up key.
2. Signs up two new users through the public signup API: a dental clinic and
   a patient, Maria.
3. Connects to `/mcp` with a standard MCP client (FastMCP) and each user's key.
4. Reads Twilio to confirm that each user has a separate, active subaccount
   and no bought number.
5. The operator gives the clinic a number for inbound calls. Maria tries the
   same operator call and is refused.
6. Maria's assistant tries `place_call` and is refused, because she has no
   caller ID. It then calls `start_caller_id_verification` for her phone.
   Twilio calls the test phone, the test phone keys in the code, and the phone
   becomes her caller ID.
7. The clinic saves rules for its number: opening hours, two free
   appointments, a cancellation fee, and a confirmation code. The fee and the
   code are random for each run.
8. Maria's assistant calls `place_call` to book a cleaning. She wants a time
   the clinic does not have, so the two voice agents must negotiate.
9. Maria's assistant polls `get_call_result` and reads the transcript.
10. The clinic's assistant connects after the call and reads the inbound call.
    The confirmation code in both transcripts proves the call was answered
    with the clinic's saved rules, with no assistant connected.
11. Reads Twilio again: the outbound leg is in Maria's subaccount and the
    inbound leg is in the clinic's subaccount.
12. Each user tries to read the other's calls, rules, and keys, and tries the
    closed Dograh API.
13. The operator sets Maria's allowance below her used time, and her next call
    is refused. The operator does the same to the clinic, and a call to the
    clinic's number is not answered.
14. Both test accounts are closed. The clinic's number goes back to the pool
    and both subaccounts are closed in Twilio, so the run can be repeated.

## Which numbers are called

Two numbers, and both must be approved test numbers in the operator's main
Twilio account:

- The pool number that the clinic receives.
- The test phone (`VERIFY_TEST_PHONE`), which plays Maria's own phone. It must
  not be in the pool. During the run, its voice address is set to TwiML that
  keys in the code, and it is cleared at the end.

While the service has a destination allowlist, the run also asks for one call
and one caller ID check to a fictional number (`+1 202 555 0143`) and requires
the service to refuse both.

## Run it

You need Python 3.12 or later with `httpx` and `fastmcp` (both are in the API
virtual environment), one free number in the pool, the operator token, and the
main Twilio account credentials.

```bash
export PLATFORM_OPERATOR_TOKEN=...       # same value as on the service
export PLATFORM_TWILIO_ACCOUNT_SID=...   # main account, same as on the service
export PLATFORM_TWILIO_AUTH_TOKEN=...
export VERIFY_TEST_PHONE=+1...           # approved test number, not in the pool
python platform_verification/verify.py \
  --base-url https://your-service.example.com \
  --out platform_verification/results/$(date +%Y%m%d-%H%M)
```

The run takes about seven minutes and uses about five minutes of call time.
The exit code is 0 only when every check passes.

## Output

- `results.json`: every check, both call records, and the allowance evidence.
- `report.md`: the same as a table, with both transcripts.

Access keys and passwords are not written to either file.
