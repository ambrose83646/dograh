# Calling platform verification

- Result: **PASS** (29 of 29 checks)
- Service: http://localhost:8000
- Run: 1119231210 (2026-11-19T23:12:10.556598+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 9 and 10; subaccounts ...f261ba and ...dcb2ea; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 19, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 151 s, 13 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-3888; digits heard: 299845938883888138888954 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 13 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 20 not found' / 'Call 19 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/20": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 19 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 4 3 1. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 59 s, price 160; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling on behalf of dana reyes. dana wanted to ask if the bike in your advertisement is still for sale, and what the price is. t' |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.5 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 19: completed, 151 s, +12085050523 to +12088864742

```
[2026-11-19T23:12:36.499+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-19T23:12:41.165+00:00] assistant: Hello, I’m calling on behalf of Maria Lopez to book a teeth cleaning appointment. She’s a new patient and would prefer a Wednesday morning.
[2026-11-19T23:12:51.176+00:00] user: Thank you for calling. We're closed on Wednesday mornings for staff training, so I can't offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T23:13:06.128+00:00] assistant: Thank you for letting me know. Maria is only available in the mornings, so Thursday at nine in the morning would be perfect. Could you please book that appointment for her?
[2026-11-19T23:13:16.813+00:00] user: Absolutely. I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I'll need Maria's full name and date of birth, please.
[2026-11-19T23:13:25.848+00:00] assistant: Of course. Her full name is Maria Lopez, and her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-19T23:13:34.693+00:00] user: Thank you. Just to confirm, I have Maria Lopez with a date of birth of March fourteen, nineteen eighty eight. Is that correct?
[2026-11-19T23:13:42.969+00:00] assistant: Yes, that’s correct—Maria Lopez, date of birth March fourteen, nineteen eighty-eight.
[2026-11-19T23:13:50.693+00:00] user: Great. Thank you. As Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, cancellations with less than twenty four hours notice will have a thirty five dollar fee. Her cleaning appointment is booked for Thursday at nine in the morning. The confirmation code is r d three eight eight eight. That's r as in river, d as in dental, three eight eight eight. Could you please repeat that code back to me, one character at a time?
[2026-11-19T23:14:19.710+00:00] assistant: Sure, the confirmation code is: r as in river, d as in dental, three, eight, eight, eight. Is that correct?
[2026-11-19T23:14:29.493+00:00] user: Yes. That's correct. R as in river, d as in dental, three eight eight eight. So I have Maria Lopez, date of birth March fourteenth nineteen eighty eight, booked for a cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card, and there's a thirty five dollar fee for cancellations with less than twenty four hours notice. Is there anything else I can help you with today?
[2026-11-19T23:14:54.791+00:00] assistant: No, that covers everything. Thank you for your help and for confirming all the details. Have a great day!
[2026-11-19T23:15:02.192+00:00] assistant: Thank you so much—goodbye!
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "The assistant called Riverside Dental to book a teeth cleaning appointment for Maria Lopez, a new patient, requesting a Wednesday morning slot. The front desk explained Wednesday mornings are unavailable and offered Thursday at 9 AM, which was accepted. The appointment was booked for Maria Lopez (DOB: March 14, 1988) on Thursday at 9 AM, with confirmation code RD3888, and instructions were given to bring a photo ID and insurance card.",
  "follow_up_needed": ""
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 20: completed, 153 s, +12085050523 to +12088864742

```
[2026-11-19T23:12:35.640+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-19T23:12:41.575+00:00] user: Hello. I'm calling on behalf of Maria Lopez to book a teeth cleaning appointment. She's a new patient and would prefer a Wednesday morning.
[2026-11-19T23:12:50.681+00:00] assistant: Thank you for calling. We’re closed on Wednesday mornings for staff training, so I can’t offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T23:13:06.774+00:00] user: Thank you for letting me know. Maria is only available in the mornings, so Thursday at nine in the morning would be perfect. Could you please book that appointment for her?
[2026-11-19T23:13:16.121+00:00] assistant: Absolutely, I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I’ll need Maria’s full name and date of birth, please.
[2026-11-19T23:13:26.455+00:00] user: Of course. Her full name is Maria Lopez, and her date of birth is March fourteenth nineteen eighty eight.
[2026-11-19T23:13:34.123+00:00] assistant: Thank you. Just to confirm, I have Maria Lopez with a date of birth of March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-19T23:13:43.814+00:00] user: Yes. That's correct. Maria Lopez, date of birth March fourteenth nineteen eighty eight.
[2026-11-19T23:13:49.844+00:00] assistant: Great, thank you. As Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, cancellations with less than twenty-four hours’ notice will have a thirty-five dollar fee.

Her cleaning appointment is booked for Thursday at nine in the morning. The confirmation code is R D 3 8 8 8. That’s R as in River, D as in Dental, three, eight, eight, eight. Could you please repeat that code back to me, one character at a time?
[2026-11-19T23:14:20.536+00:00] user: Sure. The confirmation code is r as in river, d as in dental, three eight eight eight. Is that correct?
[2026-11-19T23:14:28.794+00:00] assistant: Yes, that’s correct—R as in River, D as in Dental, three, eight, eight, eight. So, I have Maria Lopez, date of birth March fourteenth, nineteen eighty-eight, booked for a cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card, and there’s a thirty-five dollar fee for cancellations with less than twenty-four hours’ notice. Is there anything else I can help you with today?
[2026-11-19T23:14:55.257+00:00] user: No. That covers everything.
Thank you for your help and for confirming all the details. Have a great day.
[2026-11-19T23:15:02.756+00:00] assistant: Thank you for calling, and have a wonderful day. Goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller phoned on behalf of Maria Lopez to book a new patient teeth cleaning appointment, requesting a Wednesday morning slot. The assistant explained that Wednesday mornings are unavailable and offered alternatives; the caller chose Thursday at 9 a.m. and provided Maria's full name and date of birth. The assistant confirmed the booking, gave instructions for the appointment, and provided a confirmation code; no callback number or additional message was left."
}
```

## Call answered by a voicemail box

Call 21: completed, 19 s, +12088864742 to +12085050523

```
[2026-11-19T23:15:29.945+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-19T23:15:36.135+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 4 3 1. Goodbye.
```

## Call answered by a call screener, then a person

Call 22: completed, 59 s, +12088864742 to +12085050523

```
[2026-11-19T23:15:59.641+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-19T23:16:04.444+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-19T23:16:13.321+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-19T23:16:25.029+00:00] assistant: Hi Sam, I’m calling on behalf of Dana Reyes. Dana wanted to ask if the bike in your advertisement is still for sale, and what the price is.
[2026-11-19T23:16:37.321+00:00] user: Yes. The bike is still for sale.
The price is one hundred sixty dollars. That is all I can tell you. Goodbye.
[2026-11-19T23:16:45.792+00:00] assistant: Thank you, Sam. I’ll let Dana know the bike is still for sale and the price is one hundred sixty dollars. Have a great day. Goodbye.
[2026-11-19T23:16:53.831+00:00] assistant: Thank you, Sam. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes wanted to know if the bike in Sam Carter's advertisement was still for sale and the price. Sam confirmed that the bike is still for sale and the price is one hundred sixty dollars. No further information was provided and the call ended.",
  "follow_up_needed": ""
}
```
