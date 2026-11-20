# Calling platform verification

- Result: **PASS** (29 of 29 checks)
- Service: http://localhost:8000
- Run: 1120011114 (2026-11-20T01:11:14.755204+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500001 and 500002; subaccounts ...69695f and ...3d1460; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 43, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 154 s, 24 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-4279; digits heard: 2991419889942794599 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 23 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 44 not found' / 'Call 43 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/44": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 1 9 7. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 69 s, price 140; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling for dana reyes about the bike in your ad. is it still for sale? thanks. i heard one hundred forty dollars. is that correc' |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.6 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 43: completed, 154 s, +12085050523 to +12088864742

```
[2026-11-20T01:11:40.936+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T01:11:46.246+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T01:11:55.575+00:00] user: We're closed Wednesday mornings for staff training. We have a cleaning opening Tuesday at two thirty or Thursday at nine. Which works better for Maria?
[2026-11-20T01:12:04.967+00:00] assistant: Thursday morning works for Maria. Was that nine o’clock?
[2026-11-20T01:12:10.175+00:00] user: Yes. Thursday at nine o'clock.
Is that correct?
[2026-11-20T01:12:13.888+00:00] assistant: Yes, Thursday at nine o’clock is correct. Is that appointment still available?
[2026-11-20T01:12:20.535+00:00] user: Yes. It's still available.
Before I book it, may I have Maria's full name?
[2026-11-20T01:12:25.690+00:00] assistant: Maria Lopez.
[2026-11-20T01:12:29.175+00:00] user: Thank you. What is Maria's date of birth?
[2026-11-20T01:12:32.491+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T01:12:37.334+00:00] user: I heard March one four one nine eight eight. Is that correct?
[2026-11-20T01:12:41.372+00:00] assistant: Yes, that’s correct.
[2026-11-20T01:12:44.456+00:00] user: Thank you. Shall I book Maria for Thursday at nine o'clock
[2026-11-20T01:12:48.652+00:00] assistant: Yes, please book her for Thursday at nine o’clock.
[2026-11-20T01:12:55.335+00:00] user: Maria is booked for Thursday at nine o'clock. Her confirmation code is r d four two seven nine. Could you repeat that code back to me?
[2026-11-20T01:13:04.693+00:00] assistant: I heard R, D, four, two, seven, nine. Is that correct?
[2026-11-20T01:13:11.816+00:00] user: Yes. That's correct.
Since Maria is a new patient, she'll need to bring a photo ID and her insurance card. Cancellations with less than twenty four hours notice cost thirty five dollars. Is that clear?
[2026-11-20T01:13:24.454+00:00] assistant: Yes. I heard the cancellation fee is three, five dollars for less than two, four hours’ notice. Is that correct?
[2026-11-20T01:13:33.335+00:00] user: Yes. That's correct.
I've noted Maria Lopez for a new patient cleaning Thursday at nine o'clock. Is there anything else I can help with
[2026-11-20T01:13:42.096+00:00] assistant: Just to confirm, Thursday at nine is the appointment for this week, and she needs to bring a photo ID and her insurance card. Is that right?
[2026-11-20T01:13:51.656+00:00] user: Yes. That's right.
Thursday at nine o'clock this week. She should bring a photo ID and her insurance card. Does she need anything else?
[2026-11-20T01:14:00.259+00:00] assistant: That covers everything. Thank you for your help.
[2026-11-20T01:14:05.902+00:00] user: Thank you for calling Riverside Dental. Goodbye.
[2026-11-20T01:14:09.900+00:00] assistant: Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental booked Maria Lopez for a new-patient teeth cleaning Thursday at 9:00 a.m. this week; Wednesday morning was unavailable. The confirmation code is RD4279. She needs to bring a photo ID and insurance card, and cancellations with less than 24 hours\u2019 notice incur a $35 fee.",
  "follow_up_needed": "Maria should bring a photo ID and her insurance card to the appointment."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 44: completed, 151 s, +12085050523 to +12088864742

```
[2026-11-20T01:11:40.122+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T01:11:46.859+00:00] user: Hi. I'm calling from Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T01:11:55.083+00:00] assistant: We’re closed Wednesday mornings for staff training. We have a cleaning opening Tuesday at two thirty or Thursday at nine. Which works better for Maria?
[2026-11-20T01:12:05.494+00:00] user: Thursday morning works for Maria. Was that nine o'clock?
[2026-11-20T01:12:09.723+00:00] assistant: Yes, Thursday at nine o’clock. Is that correct?
[2026-11-20T01:12:14.294+00:00] user: Yes. Thursday at nine o'clock is correct. Is that appointment still available?
[2026-11-20T01:12:19.644+00:00] assistant: Yes, it’s still available. Before I book it, may I have Maria’s full name?
[2026-11-20T01:12:26.215+00:00] user: Maria Lopez.
[2026-11-20T01:12:28.525+00:00] assistant: Thank you. What is Maria’s date of birth?
[2026-11-20T01:12:33.014+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T01:12:36.486+00:00] assistant: I heard March one four, one nine eight eight. Is that correct?
[2026-11-20T01:12:42.134+00:00] user: Yes. That's correct.
[2026-11-20T01:12:43.887+00:00] assistant: Thank you. Shall I book Maria for Thursday at nine o’clock?
[2026-11-20T01:12:49.095+00:00] user: Yes. Please book her for Thursday at nine o'clock.
[2026-11-20T01:12:54.728+00:00] assistant: Maria is booked for Thursday at nine o’clock. Her confirmation code is R, D, four, two, seven, nine. Could you repeat that code back to me?
[2026-11-20T01:13:05.255+00:00] user: I heard r d four two seven nine. Is that correct?
[2026-11-20T01:13:11.369+00:00] assistant: Yes, that’s correct. Since Maria is a new patient, she’ll need to bring a photo ID and her insurance card. Cancellations with less than twenty-four hours’ notice cost thirty-five dollars. Is that clear?
[2026-11-20T01:13:24.934+00:00] user: Yes. I heard the cancellation fee is three five dollars for less than two four hours notice. Is that correct?
[2026-11-20T01:13:32.930+00:00] assistant: Yes, that’s correct. I’ve noted Maria Lopez for a new-patient cleaning Thursday at nine o’clock. Is there anything else I can help with?
[2026-11-20T01:13:42.695+00:00] user: Just to confirm, Thursday at nine is the appointment for this week, and she needs to bring a photo ID and her insurance card. Is that right?
[2026-11-20T01:13:51.210+00:00] assistant: Yes, that’s right: Thursday at nine o’clock this week. She should bring a photo ID and her insurance card. Does she need anything else?
[2026-11-20T01:14:00.855+00:00] user: That covers everything. Thank you for your help.
[2026-11-20T01:14:05.331+00:00] assistant: Thank you for calling Riverside Dental—goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller booked a new-patient teeth cleaning for Maria Lopez on Thursday at 9 a.m. this week. The assistant confirmed the appointment, provided confirmation code RD4279, and advised that Maria bring a photo ID and insurance card and that cancellations with less than 24 hours\u2019 notice incur a $35 fee. No callback number or message was left."
}
```

## Call answered by a voicemail box

Call 45: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T01:14:32.891+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T01:14:39.443+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 1 9 7. Goodbye.
```

## Call answered by a call screener, then a person

Call 46: completed, 69 s, +12088864742 to +12085050523

```
[2026-11-20T01:15:02.926+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T01:15:07.769+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T01:15:16.407+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking.
Go ahead.
[2026-11-20T01:15:27.756+00:00] assistant: Hi Sam, I’m calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T01:15:40.327+00:00] user: Yes. The bike is still for sale.
The price is one hundred forty dollars. That is all I can tell you. Goodbye.
[2026-11-20T01:15:48.958+00:00] assistant: Thanks. I heard one hundred forty dollars. Is that correct?
[2026-11-20T01:16:03.558+00:00] assistant: Sam, are you still there?
```
