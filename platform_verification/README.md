# Calling platform verification

`verify.py` tests a running calling service from the outside, the way two users
and their AI assistants use it. It makes real phone calls.

## What one run does

1. Confirms the MCP endpoint refuses a client with no key and with a made-up key.
2. Signs up two new users through the public signup API: a dental clinic and
   a patient, Maria.
3. Connects to `/mcp` with a standard MCP client (FastMCP) and each user's key.
4. The clinic saves rules for its number: opening hours, two free
   appointments, a cancellation fee, and a confirmation code. The fee and the
   code are random for each run.
5. Maria's assistant calls `place_call` to book a cleaning. She wants a time
   the clinic does not have, so the two voice agents must negotiate.
6. Maria's assistant polls `get_call_result` and reads the transcript.
7. The clinic's assistant connects after the call and reads the inbound call.
   The confirmation code in both transcripts proves the call was answered with
   the clinic's saved rules, with no assistant connected.
8. Each user tries to read the other's calls, rules, and keys, and tries the
   closed Dograh API.
9. The operator sets Maria's allowance below her used time. Her next call is
   refused, and a call to her number is not answered.
10. The numbers go back to the pool, so the run can be repeated.

## Which numbers are called

Only the two platform numbers that the two test accounts receive. While the
service has a destination allowlist, the run also asks for one call to a
fictional number (`+1 202 555 0143`) and requires the service to refuse it.

## Run it

You need Python 3.12 or later with `httpx` and `fastmcp` (both are in the API
virtual environment), two free numbers in the pool, and the operator token.

```bash
export PLATFORM_OPERATOR_TOKEN=...   # same value as on the service
python platform_verification/verify.py \
  --base-url https://your-service.example.com \
  --out platform_verification/results/$(date +%Y%m%d-%H%M)
```

The run takes about five minutes and uses about four minutes of call time.
The exit code is 0 only when every check passes.

## Output

- `results.json`: every check, both call records, and the allowance evidence.
- `report.md`: the same as a table, with both transcripts.

Access keys and passwords are not written to either file.
