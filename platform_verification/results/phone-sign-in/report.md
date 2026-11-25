# Calling platform verification

- Result: **FAIL** (40 of 41 checks)
- Service: http://localhost:8000
- Run: 1120053427 (2026-11-20T05:34:27.914046+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A person without the operator secret cannot make an email account | PASS | HTTP 403 |
| A sign-in request sends one text with a code; a second request in the same minute, a number abroad, and a stranger while signup is closed get no text | PASS | first 200, second 429, abroad 403, closed n/a, texts 1 |
| Only the right code for the right number signs in, and a code works one time | PASS | wrong 401, other number 401, right 200, replay 401 |
| After five wrong guesses the code is dead, and the same phone signs in to the same account, not a new one | PASS | guesses [401, 401, 401, 401, 401], right code after them 401, same account True |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500007 and 500008; subaccounts ...2b3c20 and ...f6cd3e; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| A phone number that belongs to one account cannot be the caller ID of a different account | PASS | refusal: 'This phone number belongs to another account. One phone number can be used on one account only.' |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | FAIL | abroad: 'This service is in a test period and can call approved test numbers only.'; premium: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 61, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 144 s, 18 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-9650; digits heard: 2998999650459650945 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 18 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 62 not found' / 'Call 61 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/62": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 8 4 8. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 69 s, price 160; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m an ai assistant calling for dana reyes about the bike in your ad. is it still for sale? thank you, sam. i’ll let dana know the bi' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by user_hangup; summary: 'Dana Reyes asked whether Sam Carter’s advertised bike was still for sale. Sam confirmed it is available for $160, then ended the call.' |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.4 min of 1; refusal: 'The 1 free call minutes are used. The user must choose a monthly plan before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The 1 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. Until then this account cannot make or answer calls.'; after renewal used 0.0 |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must choose a monthly plan before this account can make or answer more calls.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 65, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 61: completed, 144 s, +12085050523 to +12088864742

```
[2026-11-20T05:37:23.435+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T05:37:29.426+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T05:37:39.554+00:00] user: Hi. We closed Wednesday mornings. Next week, we have a cleaning appointment Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T05:37:49.308+00:00] assistant: Thursday at nine works for Maria. Could you book that appointment?
[2026-11-20T05:37:54.754+00:00] user: Thursday at nine works. I can book it once I have Maria's full name and date of birth.
What's her full name?
[2026-11-20T05:38:01.790+00:00] assistant: Maria Lopez.
[2026-11-20T05:38:05.234+00:00] user: Thank you. What's Maria's date of birth?
[2026-11-20T05:38:08.511+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T05:38:12.915+00:00] user: March fourteenth nineteen eighty eight. Is that correct?
[2026-11-20T05:38:16.912+00:00] assistant: Yes, that’s correct.
[2026-11-20T05:38:20.514+00:00] user: I have Maria Lopez's details. Shall I book her cleaning for next Thursday at nine?
[2026-11-20T05:38:25.875+00:00] assistant: Yes, please book Maria for next Thursday at nine in the morning.
[2026-11-20T05:38:31.554+00:00] user: Maria is booked for next Thursday at nine in the morning. Her confirmation code is r d nine six five zero. As a new patient, she should bring a photo ID and her insurance card. Cancellations with less than twenty four hours notice cost twenty five dollars. Do you need anything else?
[2026-11-20T05:38:50.834+00:00] assistant: Thank you. I have Thursday at nine in the morning, a photo ID and insurance card, and a late-cancellation fee of twenty-five dollars. I heard the confirmation code as R, D, nine, six, five, zero. Is that correct?
[2026-11-20T05:39:07.234+00:00] user: Yes. That's correct.
r d nine six five zero.
Is there anything else I can help with?
[2026-11-20T05:39:13.638+00:00] assistant: No, thank you. Maria is booked for next Thursday at nine, with confirmation code R D nine six five zero. She’ll bring a photo ID and insurance card, and the late-cancellation fee is twenty-five dollars. Goodbye.
[2026-11-20T05:39:29.394+00:00] user: I have Maria booked for next Thursday at nine. She'll bring a photo ID and her insurance card, and the fee for canceling with less than twenty four hours notice is twenty five dollars. Goodbye.
[2026-11-20T05:39:41.878+00:00] assistant: Thank you for your help; goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Asked Riverside Dental to book a new-patient cleaning for Maria Lopez, preferably Wednesday morning; the front desk said Wednesday mornings were unavailable. Maria was booked for next Thursday at 9 a.m., confirmation code RD9650. She should bring a photo ID and insurance card; cancellations with less than 24 hours\u2019 notice cost $25.",
  "follow_up_needed": "Maria should bring a photo ID and her insurance card to the appointment."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 62: completed, 144 s, +12085050523 to +12088864742

```
[2026-11-20T05:37:22.252+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T05:37:30.093+00:00] user: Hi. I'm calling from Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T05:37:38.749+00:00] assistant: Hi! We’re closed Wednesday mornings. Next week, we have a cleaning appointment Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T05:37:49.933+00:00] user: Thursday at nine works for Maria.
Could you book that appointment?
[2026-11-20T05:37:54.233+00:00] assistant: Thursday at nine works. I can book it once I have Maria’s full name and date of birth. What’s her full name?
[2026-11-20T05:38:02.253+00:00] user: Maria Lopez.
[2026-11-20T05:38:04.635+00:00] assistant: Thank you. What’s Maria’s date of birth?
[2026-11-20T05:38:08.976+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T05:38:12.315+00:00] assistant: March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-20T05:38:17.373+00:00] user: Yes. That's correct.
[2026-11-20T05:38:19.636+00:00] assistant: I have Maria Lopez’s details. Shall I book her cleaning for next Thursday at nine?
[2026-11-20T05:38:26.653+00:00] user: Yes. Please book Maria for next Thursday at nine in the morning.
[2026-11-20T05:38:30.958+00:00] assistant: Maria is booked for next Thursday at nine in the morning. Her confirmation code is R, D, nine, six, five, zero. As a new patient, she should bring a photo ID and her insurance card. Cancellations with less than twenty-four hours’ notice cost twenty-five dollars. Do you need anything else?
[2026-11-20T05:38:51.294+00:00] user: Thank you. I have Thursday at nine in the morning, a photo ID, an insurance card, and a late cancellation fee of twenty five dollars. I heard the confirmation code as r d nine six five zero. Is that correct?
[2026-11-20T05:39:06.758+00:00] assistant: Yes, that’s correct: R, D, nine, six, five, zero. Is there anything else I can help with?
[2026-11-20T05:39:14.093+00:00] user: No. Thank you.
Maria is booked for next Thursday at nine, with confirmation code r d nine six five zero. She'll bring a photo ID in insurance card, and the late cancellation fee is twenty five dollars. Goodbye.
[2026-11-20T05:39:28.601+00:00] assistant: I have Maria booked for next Thursday at nine. She’ll bring a photo ID and her insurance card, and the fee for cancelling with less than twenty-four hours’ notice is twenty-five dollars. Goodbye!
[2026-11-20T05:39:40.641+00:00] assistant: Thank you for calling Riverside Dental; goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller rang to book a new-patient teeth cleaning for Maria Lopez, preferably Wednesday morning. The assistant said Wednesday mornings were unavailable and booked Maria for next Thursday at 9 a.m., confirming code RD9650 and advising her to bring a photo ID and insurance card; cancellations with less than 24 hours\u2019 notice incur a $25 fee. No callback number or message was left."
}
```

## Call answered by a voicemail box

Call 63: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T05:39:59.254+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T05:40:05.967+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 8 4 8. Goodbye.
```

## Call answered by a call screener, then a person

Call 64: completed, 69 s, +12088864742 to +12085050523

```
[2026-11-20T05:40:29.247+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T05:40:34.130+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T05:40:42.767+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking.
Go ahead.
[2026-11-20T05:40:54.199+00:00] assistant: Hi Sam, I’m an AI assistant calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T05:41:07.086+00:00] user: Yes. The bike is still for sale.
The price is one hundred sixty dollars. That is all I can tell you. Goodbye.
[2026-11-20T05:41:15.401+00:00] assistant: Thank you, Sam. I’ll let Dana know the bike is still for sale for one hundred sixty dollars. Goodbye.
[2026-11-20T05:41:32.041+00:00] assistant: Sam, are you still there?
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes asked whether Sam Carter\u2019s advertised bike was still for sale. Sam confirmed it is available for $160, then ended the call.",
  "follow_up_needed": ""
}
```
