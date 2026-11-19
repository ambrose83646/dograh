# Calling platform verification

- Result: **PASS** (26 of 26 checks)
- Service: https://app.danadial.com
- Run: 1119213417 (2026-11-19T21:34:17.048063+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| While public signup is closed, a person without the operator secret cannot sign up | PASS | HTTP 403 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 10 and 11; subaccounts ...5d2150 and ...b9331c; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 19, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 155 s, 14 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-2896; digits heard: 29989452896289612896954 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 13 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 20 not found' / 'Call 19 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/20": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user at the free allowance cannot start another call | PASS | used 2.6 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 19: completed, 155 s, +12085050523 to +12088864742

```
[2026-11-19T21:34:46.179+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-19T21:34:50.459+00:00] assistant: Hello, I’m calling on behalf of Maria Lopez to book a teeth cleaning appointment. She’s a new patient and would prefer a Wednesday morning slot if possible.
[2026-11-19T21:35:01.340+00:00] user: Thank you for calling. We closed on Wednesday mornings for staff training, so I can't offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T21:35:16.186+00:00] assistant: Thank you for letting me know. Maria is only available in the mornings, so Thursday at nine in the morning would be perfect. Could you please book that appointment for her?
[2026-11-19T21:35:26.858+00:00] user: I can book Maria for Thursday at nine in the morning since she's a new patient. I'll need her full name and date of birth to complete the booking. Could you please provide those details?
[2026-11-19T21:35:36.943+00:00] assistant: Sure, her full name is Maria Lopez, and her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-19T21:35:45.178+00:00] user: Thank you. Just to confirm, that's Maria Lopez. Date of birth, March fourteenth nineteen eighty eight. Is that correct?
[2026-11-19T21:35:53.305+00:00] assistant: Yes, that's correct—Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Thank you.
[2026-11-19T21:36:01.624+00:00] user: Great. I've booked Maria Lopez for a cleaning on Thursday at nine in the morning. As a new patient, please remind her to bring a photo ID and her insurance card. If she needs to cancel, please give us at least twenty four hours notice to avoid a forty five dollar fee. Your confirmation code is r d two eight nine six. That's r as in river, d as in dental, two eight nine six. Could you please repeat that code back to me, one character at a time, so I know you have it correctly?
Is there anything else I can help you with today?
[2026-11-19T21:36:34.108+00:00] assistant: Thank you. Let me repeat the confirmation code back to you, one character at a time: r as in river, d as in dental, two, eight, nine, six. Is that correct?
[2026-11-19T21:36:46.658+00:00] user: Yes. That's correct.
[2026-11-19T21:36:48.697+00:00] user: r as in river, d as in dental, two eight nine six.
I have Maria Lopez booked for Thursday at nine in the morning for a cleaning. She should bring a photo ID and her insurance card, and there's a forty five dollar fee for cancellations with less than twenty four hours notice. Is there anything else I can help you with today?
[2026-11-19T21:37:07.196+00:00] assistant: No, that’s everything I needed. Thank you for your help and for confirming all the details. Have a great day!
[2026-11-19T21:37:14.476+00:00] assistant: Thank you so much for your help—goodbye!
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "The assistant called Riverside Dental to book a teeth cleaning appointment for Maria Lopez, a new patient, requesting a Wednesday morning slot. The office was closed Wednesday mornings, so Thursday at 9 a.m. was booked instead. The appointment was confirmed for Maria Lopez (DOB: March 14, 1988) with confirmation code RD2896, and instructions were given to bring a photo ID and insurance card, with a $45 fee for late cancellations.",
  "follow_up_needed": ""
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 20: completed, 157 s, +12085050523 to +12088864742

```
[2026-11-19T21:34:45.305+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-19T21:34:50.871+00:00] user: Hello. I'm calling on behalf of Maria Lopez to book a teeth cleaning appointment. She's a new patient and would prefer a Wednesday morning slot if possible.
[2026-11-19T21:35:00.943+00:00] assistant: Thank you for calling. We’re closed on Wednesday mornings for staff training, so I can’t offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon, or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T21:35:16.631+00:00] user: Thank you for letting me know. Maria is only available in the mornings, so Thursday at nine in the morning would be perfect. Could you please book that appointment for her?
[2026-11-19T21:35:26.226+00:00] assistant: I can book Maria for Thursday at nine in the morning. Since she’s a new patient, I’ll need her full name and date of birth to complete the booking. Could you please provide those details?
[2026-11-19T21:35:37.351+00:00] user: Sure. Her full name is Maria Lopez, and her date of birth is March fourteenth nineteen eighty eight.
[2026-11-19T21:35:44.791+00:00] assistant: Thank you. Just to confirm, that’s Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-19T21:35:53.673+00:00] user: Yes. That's correct. Maria Lopez, date of birth March fourteenth nineteen eighty eight.
Thank you.
[2026-11-19T21:36:01.195+00:00] assistant: Great, I’ve booked Maria Lopez for a cleaning on Thursday at nine in the morning. As a new patient, please remind her to bring a photo ID and her insurance card. If she needs to cancel, please give us at least twenty-four hours’ notice to avoid a forty-five dollar fee. Your confirmation code is R D 2 8 9 6. That’s R as in River, D as in Dental, two, eight, nine, six. Could you please repeat that code back to me, one character at a time, so I know you have it correctly? Is there anything else I can help you with today?
[2026-11-19T21:36:34.555+00:00] user: Thank you. Let me repeat the confirmation code back to you, one character at a time, r as in river, d as in dental, two eight nine six. Is that correct?
[2026-11-19T21:36:46.277+00:00] assistant: Yes, that’s correct—R as in River, D as in Dental, two, eight, nine, six. I have Maria Lopez booked for Thursday at nine in the morning for a cleaning. She should bring a photo ID and her insurance card, and there’s a forty-five dollar fee for cancellations with less than twenty-four hours’ notice. Is there anything else I can help you with today?
[2026-11-19T21:37:07.591+00:00] user: No. That's everything I needed.
Thank you for your help and for confirming all the details. Have a great day.
[2026-11-19T21:37:15.606+00:00] assistant: Thank you for calling—have a great day! Goodbye.
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller phoned on behalf of Maria Lopez to book a new patient teeth cleaning appointment, requesting a Wednesday morning slot. The assistant explained that Wednesday mornings are unavailable and offered alternative times; the caller chose Thursday at 9 a.m. and provided Maria's full name and date of birth. The assistant confirmed the booking, provided a confirmation code, and reminded the caller of the required documents and cancellation policy; no callback number or additional message was left."
}
```
