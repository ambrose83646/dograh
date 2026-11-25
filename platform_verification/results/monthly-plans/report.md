# Calling platform verification

- Result: **FAIL** (35 of 36 checks)
- Service: http://localhost:8000
- Run: 1120052213 (2026-11-20T05:22:13.932481+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500005 and 500006; subaccounts ...b7b4b0 and ...65cdda; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | FAIL | abroad: 'This service is in a test period and can call approved test numbers only.'; premium: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 55, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 158 s, 20 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-6194; digits heard: 29989961944561949461946196194 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 19 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 56 not found' / 'Call 55 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/56": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 1 4 7. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 66 s, price 140; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m an ai assistant calling for dana reyes about your bike ad. is the bike still for sale? sam, are you still there? thanks, sam. i’l' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by end_call; summary: 'Dana Reyes asked whether Sam Carter’s advertised bike was still for sale. Sam confirmed it was available for $140 and then ended the call.' |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.6 min of 1; refusal: 'The 1 free call minutes are used. The user must choose a monthly plan before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The 1 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. Until then this account cannot make or answer calls.'; after renewal used 0.0 |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must choose a monthly plan before this account can make or answer more calls.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 59, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 55: completed, 158 s, +12085050523 to +12088864742

```
[2026-11-20T05:22:42.493+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T05:22:47.750+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning. Do you have a Wednesday morning appointment available?
[2026-11-20T05:22:56.454+00:00] user: I'm sorry. We closed Wednesday morning. Next week, we have Tuesday at two thirty or Thursday at nine. Which works for you?
[2026-11-20T05:23:04.551+00:00] assistant: Thursday at nine works for Maria. Could you book that for her?
[2026-11-20T05:23:09.814+00:00] user: Thursday at nine. I can book it once I have Maria's full name and date of birth. I have Maria Lopez as her name. What's her date of birth?
[2026-11-20T05:23:18.432+00:00] assistant: Her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-20T05:23:23.654+00:00] user: March fourteenth nineteen eighty eight. Does Maria agree to the cleaning appointment next Thursday at nine?
[2026-11-20T05:23:30.593+00:00] assistant: Yes, please book Maria for next Thursday at nine in the morning.
[2026-11-20T05:23:35.973+00:00] user: Maria Lopez is booked for a cleaning next Thursday at nine in the morning. Her confirmation code is r d six one nine four. As a new patient, she'll need to bring a photo ID and her insurance card. Cancellations with less than twenty four hours notice cost thirty five dollars. Is there anything else I can help with?
[2026-11-20T05:23:56.278+00:00] assistant: Thank you. I have Thursday at nine in the morning, a photo ID and insurance card, and a thirty-five-dollar fee for cancellations with less than twenty-four hours’ notice. Is the confirmation code R, D, six, one, nine, four?
[2026-11-20T05:24:13.013+00:00] user: Yes. That's correct. a d six one nine four.
I have Maria Lopez booked for next Thursday at nine in the morning. Does she need anything else?
[2026-11-20T05:24:22.441+00:00] assistant: I’m sorry, I heard “A, D, six, one, nine, four” that time. Is the first letter R or A?
[2026-11-20T05:24:30.094+00:00] user: The first letter is r as in Riverside. The four code is r d six one nine four. Did you get that?
[2026-11-20T05:24:38.881+00:00] assistant: Yes, I have R, D, six, one, nine, four. Is that correct?
[2026-11-20T05:24:44.974+00:00] user: Yes. That's correct.
[2026-11-20T05:24:46.607+00:00] assistant: Thank
[2026-11-20T05:24:47.173+00:00] user: a d six one -- You're welcome. I have Maria Lopez booked for next Thursday at nine with confirmation code r d six one nine four. Does she need anything else?
[2026-11-20T05:25:00.567+00:00] assistant: Thank you. I have Maria booked for next Thursday at nine, and I have the new-patient requirements and cancellation fee. Goodbye.
[2026-11-20T05:25:10.974+00:00] user: Thank you for calling, and goodbye.
[2026-11-20T05:25:14.729+00:00] assistant: Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental booked Maria Lopez for a new-patient cleaning next Thursday at 9:00 a.m.; Wednesday morning was unavailable. The front desk confirmed code RD6194 and said to bring a photo ID and insurance card; cancellations with less than 24 hours\u2019 notice cost $35.",
  "follow_up_needed": "Maria needs to bring a photo ID and insurance card."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 56: completed, 155 s, +12085050523 to +12088864742

```
[2026-11-20T05:22:41.124+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T05:22:48.494+00:00] user: Hi. I'm calling from Maria Lopez to book a new patient teeth cleaning. Do you have a Wednesday morning appointment available?
[2026-11-20T05:22:55.750+00:00] assistant: I’m sorry, we’re closed Wednesday mornings. Next week, we have Tuesday at two thirty or Thursday at nine. Which works for you?
[2026-11-20T05:23:05.134+00:00] user: Thursday at nine works for Maria.
Could you book that for her?
[2026-11-20T05:23:09.351+00:00] assistant: Thursday at nine. I can book it once I have Maria’s full name and date of birth. I have Maria Lopez as her name. What’s her date of birth?
[2026-11-20T05:23:18.894+00:00] user: Her date of birth is March fourteenth nineteen eighty eight.
[2026-11-20T05:23:23.233+00:00] assistant: March fourteenth, nineteen eighty-eight. Does Maria agree to the cleaning appointment next Thursday at nine?
[2026-11-20T05:23:31.294+00:00] user: Yes. Please book Maria for next Thursday at nine in the morning.
[2026-11-20T05:23:35.474+00:00] assistant: Maria Lopez is booked for a cleaning next Thursday at nine in the morning. Her confirmation code is R, D, six, one, nine, four. As a new patient, she’ll need to bring a photo ID and her insurance card. Cancellations with less than twenty-four hours’ notice cost thirty-five dollars. Is there anything else I can help with?
[2026-11-20T05:23:56.814+00:00] user: Thank you. I have Thursday at nine in the morning, a photo ID, an insurance card, and a thirty five dollar fee for cancellations with less than twenty four hours notice. Is the confirmation code r d six one nine four
[2026-11-20T05:24:12.276+00:00] assistant: Yes, that’s correct: R, D, six, one, nine, four. I have Maria Lopez booked for next Thursday at nine in the morning. Does she need anything else?
[2026-11-20T05:24:23.294+00:00] user: I'm sorry. I heard a d six one nine four that time. Is the first letter r or a?
[2026-11-20T05:24:29.597+00:00] assistant: The first letter is R, as in Riverside. The full code is R, D, six, one, nine, four. Did you get that?
[2026-11-20T05:24:39.614+00:00] user: Yes. I have r d six one nine four.
Is that correct?
[2026-11-20T05:24:44.239+00:00] assistant: Yes, that’s correct: R, D, six, one, nine,
[2026-11-20T05:24:47.294+00:00] user: Thank you.
[2026-11-20T05:24:49.721+00:00] assistant: You’re welcome. I have Maria Lopez booked for next Thursday at nine, with confirmation code R, D, six, one, nine, four. Does she need anything else?
[2026-11-20T05:25:01.134+00:00] user: Thank you. I have Maria booked for next Thursday at nine, and I have the new patient requirements and cancellation fee. Goodbye.
[2026-11-20T05:25:10.480+00:00] assistant: Thank you for calling, and goodbye.
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller booked a new-patient cleaning for Maria Lopez next Thursday at 9 a.m. The assistant confirmed the appointment with code RD6194 and explained the photo ID, insurance card, and $35 fee for cancellations with less than 24 hours\u2019 notice. No callback number was left."
}
```

## Call answered by a voicemail box

Call 57: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T05:25:35.537+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T05:25:42.087+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 1 4 7. Goodbye.
```

## Call answered by a call screener, then a person

Call 58: completed, 66 s, +12088864742 to +12085050523

```
[2026-11-20T05:26:05.692+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T05:26:10.536+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T05:26:19.413+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T05:26:31.281+00:00] assistant: Hi Sam, I’m an AI assistant calling for Dana Reyes about your bike ad. Is the bike still for sale?
[2026-11-20T05:26:41.321+00:00] assistant: Sam, are you still there?
[2026-11-20T05:26:43.254+00:00] user: Yes. The bike is still for sale.
The price is one hundred forty dollars. That is all I can tell you. Goodbye.
[2026-11-20T05:26:51.614+00:00] assistant: Thanks, Sam. I’ll let Dana know the bike is still for sale for one hundred forty dollars. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes asked whether Sam Carter\u2019s advertised bike was still for sale. Sam confirmed it was available for $140 and then ended the call.",
  "follow_up_needed": ""
}
```
