# Calling platform verification

- Result: **FAIL** (46 of 47 checks)
- Service: http://localhost:8000
- Run: 1120071957 (2026-11-20T07:19:57.288462+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A person without the operator secret cannot make an email account | PASS | HTTP 403 |
| A sign-in request sends one text with a code; a second request in the same minute, a number abroad, and a stranger while signup is closed get no text | PASS | first 200, second 429, abroad 403, closed n/a, texts 1 |
| Only the right code for the right number signs in, and a code works one time | PASS | wrong 401, other number 401, right 200, replay 401 |
| After five wrong guesses the code is dead, and the same phone signs in to the same account, not a new one | PASS | guesses [401, 401, 401, 401, 401], right code after them 401, same account True |
| The sign-in answer gives the real end of the token; sign-out stops that token at once and leaves the user's other session | PASS | token lifetime 30.0 days, same as in the token: True; before 200, sign-out 204, after 401, other session 200, no token 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500015 and 500016; subaccounts ...55407f and ...f75d82; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| A phone number that belongs to one account cannot be the caller ID of a different account | PASS | refusal: 'This phone number belongs to another account. One phone number can be used on one account only.' |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | FAIL | abroad: 'This service is in a test period and can call approved test numbers only.'; premium: 'This service calls numbers in the United States and Canada only. This number is not a valid number there, or it is in a different country or a premium-rate range.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 89, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "minutes_remaining": 10.0, "max_minutes_this_call": 10.0, "minutes_note": null, "next_step": "The call is in progress |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 132 s, 18 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-4595; digits heard: 29989945954545959 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 17 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 90 not found' / 'Call 89 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/90": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 1 7 0. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 66 s, price 160; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling for dana reyes about the bike in your ad. is it still for sale? sam, are you still there? the bike is still for sale for ' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by end_call; summary: 'I called Sam Carter for Dana Reyes to ask whether the bike in his ad was still for sale. Sam confirmed it was available for $160, then ended the call.' |
| The agent gets through a two-step phone menu that takes keys only: the menu lets the call through only on the right option and the full member number | PASS | menu wanted ['4', '86654']; reached the desk: True; key entries Twilio heard: 2; service reports ['4', '86654'] |
| Behind the menu the agent brings back the answer of the desk, and the call record lists the keys it pressed | PASS | answered_by phone_menu, keys ['4', '86654'], 61 s; summary: 'The caller asked Robin at Lakeside Medical Group for the next check-up opening for Sam Carter. Robin said the next opening was Wednesday at 11:00 and that she had put the patient down for that time; n' |
| The agent presses no keys on calls that a person, a voicemail box, or a call screener answers | PASS | keys: [None, None, None] |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.2 min of 1; refusal: 'The 1 free call minutes are used. The user must choose a monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The 1 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can change to a larger plan at https://danadial.com/dashboard/billing; the larger plan gives its minutes immediately. Until then this account cannot m |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must choose a monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| The assistant is warned when less than 20% of the minutes remain, and not when many remain | PASS | note: 'Less than 20% of the call minutes of this period remain: 0.6 of 5. Tell the user. A call ends when the minutes are used. The minutes renew on December 20, 2026; a larger plan at https://danadial.com/dashboard/billing gives its minutes immediately.'; place_call said minutes_remaining 0.6, max_ |
| A call that starts with about half a minute left ends when the minutes are used, and the next call is refused | PASS | 35 s were left (to the nearest 3 s); the call ran 37 s; the hold script is 100 s long; after it minutes_remaining 0.0; refusal: 'The 5 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can change to a larger plan at  |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 95, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 89: completed, 132 s, +12085050523 to +12088864742

```
[2026-11-20T07:23:01.956+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T07:23:06.324+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T07:23:15.756+00:00] user: Sorry. I didn't catch your name clearly. Could you repeat your full name?
[2026-11-20T07:23:20.725+00:00] assistant: I’m an AI assistant calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T07:23:30.077+00:00] user: We're closed Wednesday mornings for staff training. Next week, we have Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T07:23:39.285+00:00] assistant: Thursday at nine works for Maria. Could you book that appointment?
[2026-11-20T07:23:44.877+00:00] user: Thursday at nine. Before I book it, could you give me Maria's full name?
[2026-11-20T07:23:49.726+00:00] assistant: Maria Lopez.
[2026-11-20T07:23:53.117+00:00] user: Thank you. What's Maria's date of birth?
[2026-11-20T07:23:56.367+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T07:24:00.717+00:00] user: March fourteenth nineteen eighty eight. I have Maria Lopez for a new patient cleaning next Thursday at nine. Shall I book it?
[2026-11-20T07:24:09.687+00:00] assistant: Yes, please book next Thursday at nine.
[2026-11-20T07:24:14.078+00:00] user: You'll booked for next Thursday at nine. Your confirmation code is r d four five nine five. Please bring a photo ID and your insurance card. Cancellations with less than twenty four hours notice cost forty five dollars. Is there anything else I can help with?
[2026-11-20T07:24:30.688+00:00] assistant: Thank you. Next Thursday at nine, with a photo ID and insurance card, and a forty-five-dollar fee for cancellations within twenty-four hours. Is the confirmation code R, D, four, five, nine, five?
[2026-11-20T07:24:45.197+00:00] user: Yes. That's correct. r d four five nine five. I have Maria Lopez booked for next Thursday at nine. Is there anything else you need?
[2026-11-20T07:24:54.689+00:00] assistant: That’s everything, thank you. Maria is booked for next Thursday at nine. Goodbye.
[2026-11-20T07:25:01.838+00:00] user: Goodbye.
and thank you for calling Riverside Dental.
[2026-11-20T07:25:06.971+00:00] assistant: Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental booked Maria Lopez for a new-patient teeth cleaning next Thursday at 9:00 a.m.; Wednesday morning was unavailable. The confirmation code is RD4595, and cancellations with less than 24 hours\u2019 notice cost $45.",
  "follow_up_needed": "Maria should bring a photo ID and insurance card."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 90: completed, 129 s, +12085050523 to +12088864742

```
[2026-11-20T07:22:58.981+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T07:23:03.336+00:00] user: Hi. I'm --
Hi. I'm calling from Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T07:23:15.245+00:00] assistant: Sorry, I didn’t catch your name clearly. Could you repeat your full name?
[2026-11-20T07:23:21.620+00:00] user: I'm an AI assistant calling from Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T07:23:29.687+00:00] assistant: We’re closed Wednesday mornings for staff training. Next week, we have Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T07:23:39.937+00:00] user: Thursday at nine works for Maria.
Could you book that appointment?
[2026-11-20T07:23:44.209+00:00] assistant: Thursday at nine. Before I book it, could you give me Maria’s full name?
[2026-11-20T07:23:50.337+00:00] user: Maria Lopez.
[2026-11-20T07:23:52.651+00:00] assistant: Thank you. What’s Maria’s date of birth?
[2026-11-20T07:23:56.898+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T07:24:00.169+00:00] assistant: March fourteenth, nineteen eighty-eight. I have Maria Lopez for a new-patient cleaning next Thursday at nine. Shall I book it?
[2026-11-20T07:24:10.501+00:00] user: Yes. Please book next Thursday at nine.
[2026-11-20T07:24:13.570+00:00] assistant: You’re booked for next Thursday at nine. Your confirmation code is R, D, four, five, nine, five. Please bring a photo ID and your insurance card. Cancellations with less than twenty-four hours’ notice cost forty-five dollars. Is there anything else I can help with?
[2026-11-20T07:24:31.297+00:00] user: Thank you. Next Thursday at nine with a photo ID and insurance card and a forty five dollar fee for cancellations within twenty four hours. Is the confirmation code r d four five nine five?
[2026-11-20T07:24:44.410+00:00] assistant: Yes, that’s correct: R, D, four, five, nine, five. I have Maria Lopez booked for next Thursday at nine. Is there anything else you need?
[2026-11-20T07:24:55.138+00:00] user: That's everything. Thank you.
Maria is booked for next Thursday at nine. Goodbye.
[2026-11-20T07:25:01.052+00:00] assistant: Goodbye, and thank you for calling Riverside Dental.
```

## Call answered by a voicemail box

Call 91: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T07:25:18.031+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T07:25:24.860+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 1 7 0. Goodbye.
```

## Call answered by a call screener, then a person

Call 92: completed, 66 s, +12088864742 to +12085050523

```
[2026-11-20T07:25:48.316+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T07:25:53.320+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T07:26:01.957+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T07:26:14.148+00:00] assistant: Hi Sam, I’m calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T07:26:23.029+00:00] assistant: Sam, are you still there?
[2026-11-20T07:26:26.356+00:00] user: Yes. The bike is still for sale.
The price is one hundred sixty dollars. That is all I can tell you. Goodbye.
[2026-11-20T07:26:34.591+00:00] assistant: The bike is still for sale for one hundred sixty dollars. Thank you, Sam. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "I called Sam Carter for Dana Reyes to ask whether the bike in his ad was still for sale. Sam confirmed it was available for $160, then ended the call.",
  "follow_up_needed": ""
}
```

## Call answered by a phone menu that takes keys only

Call 93: completed, 61 s, +12088864742 to +12085050523

```
[2026-11-20T07:27:05.053+00:00] user: Thank you for calling Lakeside Medical Group. Please listen to all options. For the pharmacy, press one. For medical records, press two. For billing, press three. For appointments, press four.
Please enter the patient's five digit member number.
Thank you. One moment, please.
Appointments desk. This is Robin.
can I help you?
[2026-11-20T07:27:37.491+00:00] assistant: Hi, I’m an AI assistant calling for Sam Carter to ask about the next opening for a check-up. What day and time is available?
[2026-11-20T07:27:48.652+00:00] user: Okay.
The next opening for a checkup is Wednesday at eleven o'clock. I have put the patient down for that time. Goodbye.
[2026-11-20T07:27:58.654+00:00] assistant: Wednesday at eleven o’clock. Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "The caller asked Robin at Lakeside Medical Group for the next check-up opening for Sam Carter. Robin said the next opening was Wednesday at 11:00 and that she had put the patient down for that time; no confirmation number was given.",
  "follow_up_needed": ""
}
```
