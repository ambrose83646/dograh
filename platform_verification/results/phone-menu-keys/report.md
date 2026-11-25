# Calling platform verification

- Result: **FAIL** (42 of 44 checks)
- Service: http://localhost:8000
- Run: 1120065146 (2026-11-20T06:51:46.255249+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A person without the operator secret cannot make an email account | PASS | HTTP 403 |
| A sign-in request sends one text with a code; a second request in the same minute, a number abroad, and a stranger while signup is closed get no text | PASS | first 200, second 429, abroad 403, closed n/a, texts 1 |
| Only the right code for the right number signs in, and a code works one time | PASS | wrong 401, other number 401, right 200, replay 401 |
| After five wrong guesses the code is dead, and the same phone signs in to the same account, not a new one | PASS | guesses [401, 401, 401, 401, 401], right code after them 401, same account True |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500011 and 500012; subaccounts ...474c0b and ...a88b00; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| A phone number that belongs to one account cannot be the caller ID of a different account | PASS | refusal: 'This phone number belongs to another account. One phone number can be used on one account only.' |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | FAIL | abroad: 'This service is in a test period and can call approved test numbers only.'; premium: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 74, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 185 s, 24 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-7612; digits heard: 299889976124576129761276129459 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 25 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 75 not found' / 'Call 74 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/75": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 9 7 8. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 66 s, price 180; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling for dana reyes about the bike in your ad. is it still for sale? sam, are you still there? thanks, sam. the bike is still ' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by end_call; summary: 'I called Sam Carter for Dana Reyes to ask whether the bike in his ad was still for sale. Sam confirmed it was available for $180 and then ended the call.' |
| The agent gets through a two-step phone menu that takes keys only: the menu lets the call through only on the right option and the full member number | PASS | menu wanted ['4', '74442']; reached the desk: True; key entries Twilio heard: 2; service reports ['4', '74442', '4'] |
| Behind the menu the agent brings back the answer of the desk, and the call record lists the keys it pressed | FAIL | answered_by phone_menu, keys ['4', '74442', '4'], 62 s; summary: 'Called Lakeside Medical Group to ask about the next check-up appointment for Sam Carter. Robin said the next opening was Wednesday at 11:00 and put Sam down for that time; no confirmation number was g' |
| The agent presses no keys on calls that a person, a voicemail box, or a call screener answers | PASS | keys: [None, None, None] |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 3.1 min of 1; refusal: 'The 1 free call minutes are used. The user must choose a monthly plan before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The 1 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. Until then this account cannot make or answer calls.'; after renewal used 0.0 |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must choose a monthly plan before this account can make or answer more calls.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 79, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 74: completed, 185 s, +12085050523 to +12088864742

```
[2026-11-20T06:54:39.699+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T06:54:45.560+00:00] assistant: I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T06:54:54.540+00:00] user: Sorry. We closed Wednesday mornings. Next week, we have Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T06:55:02.601+00:00] assistant: Thursday at nine works for Maria. Can you book that for her?
[2026-11-20T06:55:07.659+00:00] user: Thursday at nine. I'll need Maria's full name before I can book it. Is it Maria Lopez?
[2026-11-20T06:55:13.882+00:00] assistant: Yes, Maria Lopez.
[2026-11-20T06:55:17.138+00:00] user: Thank you. What's Maria's date of birth?
[2026-11-20T06:55:20.524+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T06:55:24.899+00:00] user: March fourteenth nineteen eighty eight. Is that right?
[2026-11-20T06:55:28.484+00:00] assistant: Yes, that’s right.
[2026-11-20T06:55:31.901+00:00] user: I have Maria Lopez's date of birth as March fourteen nineteen eighty eight. Do you agree to book her cleaning for Thursday at nine?
[2026-11-20T06:55:40.126+00:00] assistant: Yes, please book her for Thursday at nine in the morning.
[2026-11-20T06:55:45.201+00:00] user: Maria's cleaning is booked for Thursday at nine in the morning. Her confirmation code is r d seven six one two. As a new patient, she should bring a photo ID and her insurance card. Cancellations with less than twenty four hours notice cost thirty five dollars. Is there anything else you need?
[2026-11-20T06:56:04.326+00:00] assistant: Thank you. I have Thursday at nine in the morning, a photo ID and insurance card, and a late-cancellation fee of thirty-five dollars. Is the confirmation code R, D, seven, six, one, two?
[2026-11-20T06:56:20.865+00:00] user: Yes. That's correct. a d seven six one two. I've noted Maria's cleaning for Thursday at nine, and that shall bring a photo ID and insurance card. Is there anything else you need?
[2026-11-20T06:56:32.368+00:00] assistant: Sorry, I heard “A, D, seven, six, one, two” that time. Is the first letter R or A?
[2026-11-20T06:56:40.459+00:00] user: The first letter is r. The full code is r d seven six one two. Did you get that?
[2026-11-20T06:56:48.168+00:00] assistant: Yes, R, D, seven, six, one, two. Is that correct?
[2026-11-20T06:56:54.459+00:00] user: Yes. That's correct. a d seven six one two. Maria is booked for Thursday at nine in the morning. She should bring a photo ID and insurance card, and a cancellation with less than twenty four hours notice costs thirty five dollars. Do you need anything else?
[2026-11-20T06:57:10.769+00:00] assistant: The first letter sounded like “A” again. Could you confirm just the first letter of the code?
[2026-11-20T06:57:17.659+00:00] user: The first letter is r as in Riverside. Did you hear r?
[2026-11-20T06:57:23.009+00:00] assistant: Yes, R as in Riverside. Thank you. Maria is booked for Thursday at nine in the morning, and I have everything I need.
[2026-11-20T06:57:32.539+00:00] user: You're welcome. Maria Lopez is booked for Thursday at nine in the morning. Have a good day.
[2026-11-20T06:57:38.810+00:00] assistant: Thank you. Have a good day.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental booked Maria Lopez for a new-patient teeth cleaning next Thursday at 9:00 a.m.; Wednesday morning was unavailable. The confirmation code is RD7612. Maria should bring a photo ID and insurance card; cancellations with less than 24 hours\u2019 notice cost $35.",
  "follow_up_needed": "Maria should bring a photo ID and insurance card to the appointment."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 75: completed, 188 s, +12085050523 to +12088864742

```
[2026-11-20T06:54:38.947+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T06:54:46.284+00:00] user: I'm calling from Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T06:54:53.882+00:00] assistant: Sorry, we’re closed Wednesday mornings. Next week, we have Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T06:55:03.164+00:00] user: Thursday at nine works for Maria. Can you book that for her?
[2026-11-20T06:55:07.164+00:00] assistant: Thursday at nine. I’ll need Maria’s full name before I can book it. Is it Maria Lopez?
[2026-11-20T06:55:14.284+00:00] user: Yes, Maria Lopez.
[2026-11-20T06:55:16.685+00:00] assistant: Thank you. What’s Maria’s date of birth?
[2026-11-20T06:55:21.085+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T06:55:24.366+00:00] assistant: March fourteenth, nineteen eighty-eight. Is that right?
[2026-11-20T06:55:29.165+00:00] user: Yes. That's right.
[2026-11-20T06:55:31.166+00:00] assistant: I have Maria Lopez’s date of birth as March fourteenth, nineteen eighty-eight. Do you agree to book her cleaning for Thursday at nine?
[2026-11-20T06:55:40.845+00:00] user: Yes. Please book her for Thursday at nine in the morning.
[2026-11-20T06:55:44.607+00:00] assistant: Maria’s cleaning is booked for Thursday at nine in the morning. Her confirmation code is R, D, seven, six, one, two. As a new patient, she should bring a photo ID and her insurance card. Cancellations with less than twenty-four hours’ notice cost thirty-five dollars. Is there anything else you need?
[2026-11-20T06:56:04.925+00:00] user: Thank you. I have Thursday at nine in the morning, a photo ID, an insurance card, and a late cancellation fee of thirty five dollars. Is the confirmation code r d seven six one two?
[2026-11-20T06:56:20.047+00:00] assistant: Yes, that’s correct: R, D, seven, six, one, two. I’ve noted Maria’s cleaning for Thursday at nine, and that she’ll bring a photo ID and insurance card. Is there anything else you need?
[2026-11-20T06:56:32.845+00:00] user: Sorry. I heard a d seven six one two that time. Is the first letter r or a?
[2026-11-20T06:56:40.048+00:00] assistant: The first letter is R. The full code is R, D, seven, six, one, two. Did you get that?
[2026-11-20T06:56:48.845+00:00] user: Yes. r d seven six one two. Is that correct?
[2026-11-20T06:56:53.649+00:00] assistant: Yes, that’s correct: R, D, seven, six, one, two. Maria is booked for Thursday at nine in the morning. She should bring a photo ID and insurance card, and a cancellation with less than twenty-four hours’ notice costs thirty-five dollars. Do you need anything else?
[2026-11-20T06:57:11.324+00:00] user: The first letter sounded like a again. Could you confirm just the first letter of the code?
[2026-11-20T06:57:17.290+00:00] assistant: The first letter is R, as in Riverside. Did you hear R?
[2026-11-20T06:57:23.804+00:00] user: Yes. R as in Riverside. Thank you. Maria is booked for Thursday at nine in the morning, and I have everything I need.
[2026-11-20T06:57:31.971+00:00] assistant: You’re welcome. Maria Lopez is booked for Thursday at nine in the morning. Have a good day!
[2026-11-20T06:57:39.245+00:00] user: Thank you. Have a good day.
[2026-11-20T06:57:42.732+00:00] assistant: Thank you for calling, and goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller rang to book a new-patient teeth cleaning for Maria Lopez, preferably Wednesday morning. The front desk said Wednesday mornings were unavailable and booked her for Thursday at 9 a.m., with confirmation code RD7612; it also advised her to bring a photo ID and insurance card and explained the $35 fee for cancellations with less than 24 hours\u2019 notice. No callback number was left."
}
```

## Call answered by a voicemail box

Call 76: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T06:58:01.833+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T06:58:08.426+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 9 7 8. Goodbye.
```

## Call answered by a call screener, then a person

Call 77: completed, 66 s, +12088864742 to +12085050523

```
[2026-11-20T06:58:31.919+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T06:58:36.848+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T06:58:45.720+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T06:58:57.948+00:00] assistant: Hi Sam, I’m calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T06:59:07.430+00:00] assistant: Sam, are you still there?
[2026-11-20T06:59:09.879+00:00] user: Yes. The bike is still for sale.
The price is one hundred eighty dollars. That is all I can tell you. Goodbye.
[2026-11-20T06:59:17.790+00:00] assistant: Thanks, Sam. The bike is still for sale for one hundred eighty dollars. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "I called Sam Carter for Dana Reyes to ask whether the bike in his ad was still for sale. Sam confirmed it was available for $180 and then ended the call.",
  "follow_up_needed": ""
}
```

## Call answered by a phone menu that takes keys only

Call 78: completed, 62 s, +12088864742 to +12085050523

```
[2026-11-20T06:59:48.658+00:00] user: Thank you for calling Lakeside Medical Group. Please listen to all options. For billing, press one. For medical records, press two. For the pharmacy, press three. For appointments, press four.
Please enter the patient's five digit member number.
Thank you. One moment, please.
Appointments desk. This is Robin. How can I help you?
[2026-11-20T07:00:21.128+00:00] assistant: Hi Robin, I’m an AI assistant calling for Sam Carter to ask when the next check-up appointment is available.
[2026-11-20T07:00:31.935+00:00] user: Okay.
The next opening for a checkup is Wednesday at eleven o'clock. I have put the patient down for that time. Goodbye.
[2026-11-20T07:00:42.170+00:00] assistant: Thank you. I have Wednesday at eleven o’clock for Sam Carter’s check-up. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Called Lakeside Medical Group to ask about the next check-up appointment for Sam Carter. Robin said the next opening was Wednesday at 11:00 and put Sam down for that time; no confirmation number was given.",
  "follow_up_needed": ""
}
```
