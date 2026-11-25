# Calling platform verification

- Result: **PASS** (30 of 30 checks)
- Service: https://app.danadial.com
- Run: 1119234248 (2026-11-19T23:42:48.568724+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| While public signup is closed, a person without the operator secret cannot sign up | PASS | HTTP 403 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 16 and 17; subaccounts ...96db1a and ...ddf473; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'skipped: the service is past its test period' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 29, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 176 s, 14 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-6715; digits heard: 29984596715671516715967156715 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 15 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 30 not found' / 'Call 29 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/30": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 7 0 7. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 60 s, price 140; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling on behalf of dana reyes. dana saw your advertisement and wanted to ask if the bike you listed is still for sale. hi sam, ' |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.9 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 29: completed, 176 s, +12085050523 to +12088864742

```
[2026-11-19T23:43:15.767+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-19T23:43:20.413+00:00] assistant: Hello, I’m calling on behalf of Maria Lopez to book a teeth cleaning appointment. She’s a new patient and would prefer a Wednesday morning.
[2026-11-19T23:43:30.489+00:00] user: Thank you for calling. We're closed on Wednesday mornings for staff training, so I can't offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T23:43:45.416+00:00] assistant: Thank you for letting me know. Maria can only come in the morning, so Thursday at nine in the morning would be perfect. Could you please book that appointment for her?
[2026-11-19T23:43:55.930+00:00] user: Great. I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I'll need Maria's full name and date of birth since she's a new patient. Could you please provide those details?
[2026-11-19T23:44:07.258+00:00] assistant: Of course. Her full name is Maria Lopez, and her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-19T23:44:16.089+00:00] user: Thank you. Just to confirm, that's Maria Lopez. Date of birth, March fourteenth nineteen eighty eight. Is that correct?
[2026-11-19T23:44:24.584+00:00] assistant: Yes, that’s correct—Maria Lopez, date of birth March fourteenth, nineteen eighty-eight.
[2026-11-19T23:44:32.008+00:00] user: Perfect. Thank you for confirming. Since Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, if she needs to cancel, please let us know at least twenty four hours in advance. Otherwise, there's a twenty five dollar cancellation fee. Her cleaning appointment is booked for Thursday at nine in the morning. Here's her confirmation code, r as in river, d as in dental, six seven one five. That's r d six seven one five. Could you please repeat that code back to me one character at a time?
[2026-11-19T23:45:07.466+00:00] assistant: Sure, the confirmation code is: r as in river, d as in dental, six, seven, one, five. Is that correct?
[2026-11-19T23:45:17.290+00:00] user: Yes. That's correct. a d six seven one five. I have Maria Lopez booked for a cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card. Is there anything else I can help you with today?
[2026-11-19T23:45:30.749+00:00] assistant: Thank you for confirming. Just to clarify, the confirmation code is r as in river, d as in dental, six, seven, one, five—not a d six seven one five. Could you please confirm that the code is r d six seven one five?
[2026-11-19T23:45:49.210+00:00] user: Absolutely. Let me confirm. The code is r as in river, d as in dental, six seven one five. That's r d six seven one five. You have it correct. Is there anything else I can help you with today?
[2026-11-19T23:46:05.629+00:00] assistant: Thank you so much for your help—goodbye!
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "The assistant called Riverside Dental to book a teeth cleaning appointment for Maria Lopez, a new patient, requesting a Wednesday morning slot. The office was unavailable then but offered Thursday at 9 a.m., which was accepted. The appointment was booked for Maria Lopez (DOB: March 14, 1988), with confirmation code RD6715. The office reminded Maria to bring a photo ID and insurance card and mentioned a $25 cancellation fee if not canceled 24 hours in advance.",
  "follow_up_needed": ""
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 30: completed, 179 s, +12085050523 to +12088864742

```
[2026-11-19T23:43:14.913+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-19T23:43:20.874+00:00] user: Hello. I'm calling on behalf of Maria Lopez to book a teeth cleaning appointment. She's a new patient and would prefer a Wednesday morning.
[2026-11-19T23:43:29.906+00:00] assistant: Thank you for calling. We’re closed on Wednesday mornings for staff training, so I can’t offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon, or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T23:43:45.993+00:00] user: Thank you for letting me know. Maria can only come in the morning, so Thursday at nine in the morning would be perfect. Could you please book that appointment for her?
[2026-11-19T23:43:55.548+00:00] assistant: Great, I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I’ll need Maria’s full name and date of birth, since she’s a new patient. Could you please provide those details?
[2026-11-19T23:44:07.995+00:00] user: Of course. Her full name is Maria Lopez, and her date of birth is March fourteenth nineteen eighty eight.
[2026-11-19T23:44:15.711+00:00] assistant: Thank you. Just to confirm, that’s Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-19T23:44:25.274+00:00] user: Yes. That's correct.
Maria Lopez. Date of birth, March fourteenth nineteen eighty eight.
[2026-11-19T23:44:31.640+00:00] assistant: Perfect, thank you for confirming. Since Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, if she needs to cancel, please let us know at least twenty-four hours in advance—otherwise, there’s a twenty-five dollar cancellation fee.

Her cleaning appointment is booked for Thursday at nine in the morning. Here’s her confirmation code: R as in River, D as in Dental, six, seven, one, five. That’s R... D... six... seven... one... five. Could you please repeat that code back to me, one character at a time?
[2026-11-19T23:45:08.392+00:00] user: Sure. The confirmation code is r as in river, d as in dental, six seven one five. Is that correct?
[2026-11-19T23:45:16.919+00:00] assistant: Yes, that’s correct—R, D, six, seven, one, five.

I have Maria Lopez booked for a cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card. Is there anything else I can help you with today?
[2026-11-19T23:45:31.275+00:00] user: Thank you for confirming. Just to clarify, the confirmation code is r as in river, d as in dental, six seven one five, not a d six seven one five. Could you please confirm that the code is r d six seven one five
[2026-11-19T23:45:48.720+00:00] assistant: Absolutely, let me confirm: the code is R as in River, D as in Dental, six, seven, one, five. That’s R... D... six... seven... one... five. You have it correct. Is there anything else I can help you with today?
[2026-11-19T23:46:06.078+00:00] user: Thank you so much for your help. Goodbye.
[2026-11-19T23:46:09.921+00:00] assistant: Thank you for calling, and have a great day. Goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller phoned on behalf of Maria Lopez to book a new patient teeth cleaning appointment, requesting a Wednesday morning slot. The assistant explained that Wednesday mornings are unavailable and offered alternative times; the caller chose Thursday at 9 a.m. and provided Maria's full name and date of birth. The assistant confirmed the booking, gave a confirmation code, and reminded the caller about bringing ID and insurance, as well as the cancellation policy. No callback number or additional message was left."
}
```

## Call answered by a voicemail box

Call 31: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-19T23:46:23.803+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-19T23:46:30.484+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 7 0 7. Goodbye.
```

## Call answered by a call screener, then a person

Call 32: completed, 60 s, +12088864742 to +12085050523

```
[2026-11-19T23:46:54.193+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-19T23:46:59.036+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-19T23:47:07.669+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-19T23:47:19.380+00:00] assistant: Hi Sam, I’m calling on behalf of Dana Reyes. Dana saw your advertisement and wanted to ask if the bike you listed is still for sale.
[2026-11-19T23:47:31.181+00:00] assistant: Hi Sam, are you still
[2026-11-19T23:47:32.308+00:00] user: Yes. The bike is still for sale.
The price is one hundred forty dollars. That is all I can tell you. Goodbye.
[2026-11-19T23:47:40.625+00:00] assistant: Thank you, Sam. Just to confirm, the price is one hundred forty dollars and the bike is still for sale. Have a great day. Goodbye.
[2026-11-19T23:47:48.986+00:00] assistant: Thank you, Sam. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes wanted to know if the bike Sam Carter listed was still for sale. Sam confirmed that the bike is still available and the price is one hundred forty dollars. No further information was provided and the call ended.",
  "follow_up_needed": ""
}
```
