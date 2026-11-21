# Calling platform verification

- Result: **PASS** (47 of 47 checks)
- Service: https://app.danadial.com
- Run: 1120170050 (2026-11-20T17:00:50.289257+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A person without the operator secret cannot make an email account | PASS | HTTP 403 |
| A sign-in request sends one text with a code; a second request in the same minute, a number abroad, and a stranger while signup is closed get no text | PASS | first 200, second 429, abroad 403, closed 403, texts 1 |
| Only the right code for the right number signs in, and a code works one time | PASS | wrong 401, other number 401, right 200, replay 401 |
| After five wrong guesses the code is dead, and the same phone signs in to the same account, not a new one | PASS | guesses [401, 401, 401, 401, 401], right code after them 401, same account True |
| The sign-in answer gives the real end of the token; sign-out stops that token at once and leaves the user's other session | PASS | token lifetime 30.0 days, same as in the token: True; before 200, sign-out 204, after 401, other session 200, no token 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 30 and 31; subaccounts ...20c130 and ...208e75; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| A phone number that belongs to one account cannot be the caller ID of a different account | PASS | refusal: 'This phone number belongs to another account. One phone number can be used on one account only.' |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'skipped: the service is past its test period' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | PASS | abroad: 'Calls to this country are not available. Allowed prefixes: +1.'; premium: 'This service calls numbers in the United States and Canada only. This number is not a valid number there, or it is in a different country or a premium-rate range.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 64, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "minutes_remaining": 10.0, "max_minutes_this_call": 10.0, "minutes_note": null, "next_step": "The call is in progress |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 194 s, 26 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-1262; digits heard: 29988991262451262954126212629 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 24 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 65 not found' / 'Call 64 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/65": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 21 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 6 4 6. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 67 s, price 180; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling for dana reyes about the bike in your ad. is it still for sale? sam, are you still there? thank you, sam. i’ll let dana k' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by end_call; summary: 'Dana Reyes asked whether the bike in Sam Carter’s ad was still for sale. Sam confirmed that it is available for $180, then ended the call.' |
| The agent gets through a two-step phone menu that takes keys only: the menu lets the call through only on the right option and the full member number | PASS | menu wanted ['2', '38833']; reached the desk: True; key entries Twilio heard: 2; service reports ['2', '38833'] |
| Behind the menu the agent brings back the answer of the desk, and the call record lists the keys it pressed | PASS | answered_by phone_menu, keys ['2', '38833'], 62 s; summary: 'Called Lakeside Medical Group to ask about the next check-up opening for Sam Carter. Robin at the appointments desk said the next opening was Friday at 2:00 and put Sam down for that time.' |
| The agent presses no keys on calls that a person, a voicemail box, or a call screener answers | PASS | keys: [None, None, None] |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 3.2 min of 1; refusal: 'The 1 free call minutes are used. The user must choose a monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The 1 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can change to a larger plan at https://danadial.com/dashboard/billing; the larger plan gives its minutes immediately. Until then this account cannot m |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must choose a monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| The assistant is warned when less than 20% of the minutes remain, and not when many remain | PASS | note: 'Less than 20% of the call minutes of this period remain: 0.6 of 6. Tell the user. A call ends when the minutes are used. The minutes renew on December 20, 2026; a larger plan at https://danadial.com/dashboard/billing gives its minutes immediately.'; place_call said minutes_remaining 0.6, max_ |
| A call that starts with about half a minute left ends when the minutes are used, and the next call is refused | PASS | 35 s were left (to the nearest 3 s); the call ran 38 s; the hold script is 100 s long; after it minutes_remaining 0.0; refusal: 'The 6 call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can change to a larger plan at  |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 71, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 64: completed, 194 s, +12085050523 to +12088864742

```
[2026-11-20T17:03:48.600+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T17:03:55.372+00:00] assistant: Hi, I’m
[2026-11-20T17:03:56.758+00:00] user: Hello. Are you --
I
[2026-11-20T17:04:02.180+00:00] assistant: Hi, I’m calling for
[2026-11-20T17:04:03.239+00:00] user: Hi. I'm here.
[2026-11-20T17:04:06.463+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning. Do you have a Wednesday morning appointment next week?
[2026-11-20T17:04:15.722+00:00] user: We're closed Wednesday mornings. Next week, I can offer Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T17:04:23.346+00:00] assistant: Thursday at nine works for Maria. Can you book that for her?
[2026-11-20T17:04:28.759+00:00] user: Thursday at nine. I can help with that. What's Maria's full name?
[2026-11-20T17:04:33.827+00:00] assistant: Maria Lopez.
[2026-11-20T17:04:37.400+00:00] user: Thank you. What's Maria's date of birth?
[2026-11-20T17:04:40.868+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T17:04:45.239+00:00] user: March fourteenth nineteen eighty eight. Is that correct?
[2026-11-20T17:04:48.993+00:00] assistant: Yes, that’s correct.
[2026-11-20T17:04:52.359+00:00] user: I have Maria Lopez's date of birth as March fourteen nineteen eighty eight. Do you agree to book her cleaning for Thursday at nine?
[2026-11-20T17:05:01.195+00:00] assistant: Yes, please book her for Thursday, November twenty-sixth, at nine in the morning.
[2026-11-20T17:05:07.960+00:00] user: Maria is booked for Thursday, November twenty sixth at nine in the morning. Her confirmation code is r d one two six two. Since she's a new patient, she should bring a photo ID and her insurance card. Cancellations with less than twenty four hours notice cost thirty five dollars. Does she need anything else?
[2026-11-20T17:05:28.357+00:00] assistant: Thank you. I have Thursday, November twenty-sixth at nine in the morning, with a thirty-five-dollar late-cancellation fee. The code is R, D, one, two, six, two. Is that correct?
[2026-11-20T17:05:42.518+00:00] user: Yes. That's correct. a d one two six two. The appointment is Thursday, November twenty sixth at nine in the morning, and the thirty five dollar fee applies to cancellations with less than twenty four hours notice. Is there anything else I can help with?
[2026-11-20T17:05:59.038+00:00] assistant: I heard you say A, D, one, two, six, two just now, which differs from R, D, one, two, six, two. Which is the correct code?
[2026-11-20T17:06:09.560+00:00] user: Sorry for the confusion. The correct code is r d one two six two. Did you get that?
[2026-11-20T17:06:17.238+00:00] assistant: R, D, one, two, six, two. Is that correct?
[2026-11-20T17:06:22.998+00:00] user: Yes. That's correct. RD one two six two. I have Maria Lopez booked for Thursday, November twenty sixth at nine in the morning. Does she need anything else?
[2026-11-20T17:06:33.881+00:00] assistant: No, thank you. Maria is booked for Thursday, November twenty-sixth at nine in the morning, confirmation code R D one two six two. She’ll bring a photo ID and insurance card, and she knows the thirty-five-dollar fee applies to cancellations with less than twenty-four hours’ notice. Goodbye.
[2026-11-20T17:06:54.280+00:00] user: Thank you for calling, and goodbye.
[2026-11-20T17:06:58.443+00:00] assistant: Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental was asked to book a new-patient teeth cleaning for Maria Lopez on Wednesday morning, but the office was closed then. Maria was booked for Thursday, November 26, at 9:00 a.m., with confirmation code RD1262; cancellations with less than 24 hours\u2019 notice incur a $35 fee.",
  "follow_up_needed": "Maria should bring a photo ID and insurance card."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 65: completed, 192 s, +12085050523 to +12088864742

```
[2026-11-20T17:03:47.522+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T17:03:55.455+00:00] assistant: Hello, are you still there?
[2026-11-20T17:03:56.463+00:00] user: Hi. I'm calling from --
[2026-11-20T17:04:02.298+00:00] assistant: Hi, I’m here. Could you
[2026-11-20T17:04:03.418+00:00] user: Hi. I'm -- Hi. I'm calling for Maria Lopez to book a new patient teeth cleaning. Do you have a Wednesday morning appointment next week?
[2026-11-20T17:04:14.860+00:00] assistant: We’re closed Wednesday mornings. Next week, I can offer Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T17:04:23.896+00:00] user: Thursday at nine works for Maria. Can you book that for her?
[2026-11-20T17:04:28.180+00:00] assistant: Thursday at nine. I can help with that. What’s Maria’s full name?
[2026-11-20T17:04:34.539+00:00] user: Maria Lopez.
[2026-11-20T17:04:36.862+00:00] assistant: Thank you. What’s Maria’s date of birth?
[2026-11-20T17:04:41.418+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T17:04:44.584+00:00] assistant: March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-20T17:04:49.816+00:00] user: Yes. That's correct.
[2026-11-20T17:04:51.667+00:00] assistant: I have Maria Lopez’s date of birth as March fourteenth, nineteen eighty-eight. Do you agree to book her cleaning for Thursday at nine?
[2026-11-20T17:05:02.054+00:00] user: Yes. Please book her for Thursday, November twenty sixth at nine in the morning.
[2026-11-20T17:05:07.309+00:00] assistant: Maria is booked for Thursday, November twenty-sixth, at nine in the morning. Her confirmation code is R, D, one, two, six, two. Since she’s a new patient, she should bring a photo ID and her insurance card. Cancellations with less than twenty-four hours’ notice cost thirty-five dollars. Does she need anything else?
[2026-11-20T17:05:28.937+00:00] user: Thank you. I have Thursday, November twenty sixth at nine in the morning with a thirty five dollar late cancellation fee. The code is r d one two six two. Is that correct?
[2026-11-20T17:05:41.669+00:00] assistant: Yes, that’s correct: R, D, one, two, six, two. The appointment is Thursday, November twenty-sixth, at nine in the morning, and the thirty-five-dollar fee applies to cancellations with less than twenty-four hours’ notice. Is there anything else I can help with?
[2026-11-20T17:05:59.655+00:00] user: I heard you say a d one two six two just now, which differs from r d one two six two.
which is the correct code?
[2026-11-20T17:06:09.036+00:00] assistant: Sorry for the confusion. The correct code is R, D, one, two, six, two. Did you get that?
[2026-11-20T17:06:18.056+00:00] user: RD one two six two.
Is that correct?
[2026-11-20T17:06:22.200+00:00] assistant: Yes, that’s correct: R, D, one, two, six, two. I have Maria Lopez booked for Thursday, November twenty-sixth, at nine in the morning. Does she need anything else?
[2026-11-20T17:06:34.694+00:00] user: No. Thank you. Maria is booked for Thursday, November twenty sixth at nine in the morning. Confirmation code r d one two six two. She'll bring a photo ID and insurance card, and she knows the thirty five dollar fee applies to cancellations with less than twenty four hours notice. Goodbye.
[2026-11-20T17:06:53.763+00:00] assistant: Thank you for calling, and goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller booked a new-patient teeth cleaning for Maria Lopez on Thursday, November 26, at 9 a.m. The assistant confirmed the booking and code RD1262, advised Maria to bring a photo ID and insurance card, and explained the $35 fee for cancellations with less than 24 hours\u2019 notice. No callback number was left."
}
```

## Call answered by a voicemail box

Call 66: completed, 21 s, +12088864742 to +12085050523

```
[2026-11-20T17:07:12.167+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T17:07:18.762+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 6 4 6. Goodbye.
```

## Call answered by a call screener, then a person

Call 67: completed, 67 s, +12088864742 to +12085050523

```
[2026-11-20T17:07:42.617+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T17:07:47.308+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T17:07:56.178+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T17:08:08.026+00:00] assistant: Hi Sam, I’m calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T17:08:17.267+00:00] assistant: Sam, are you still there?
[2026-11-20T17:08:19.935+00:00] user: Yes. The bike is still for sale. The price is one hundred eighty dollars. That is all I can tell you. Goodbye.
[2026-11-20T17:08:28.629+00:00] assistant: Thank you, Sam. I’ll let Dana know the bike is still for sale for one hundred eighty dollars. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes asked whether the bike in Sam Carter\u2019s ad was still for sale. Sam confirmed that it is available for $180, then ended the call.",
  "follow_up_needed": ""
}
```

## Call answered by a phone menu that takes keys only

Call 69: completed, 62 s, +12088864742 to +12085050523

```
[2026-11-20T17:08:59.818+00:00] user: Thank you for calling Lakeside Medical Group. Please listen to all options. For the pharmacy, press one. For appointments, press two. For billing, press three. For medical records, press four.
Please enter the patient's five digit member number.
Thank you. One moment, please.
Appointments desk. This is Robin. How can I help you?
[2026-11-20T17:09:31.144+00:00] assistant: Hi Robin, I’m calling on behalf of Sam Carter to ask when the next opening is for a check-up.
[2026-11-20T17:09:42.897+00:00] user: Okay.
the next opening for a checkup is Friday at two o'clock. I have put the patient down for that time. Goodbye.
[2026-11-20T17:09:51.948+00:00] assistant: Thank you. I have Friday at two o’clock for Sam Carter’s check-up. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Called Lakeside Medical Group to ask about the next check-up opening for Sam Carter. Robin at the appointments desk said the next opening was Friday at 2:00 and put Sam down for that time.",
  "follow_up_needed": ""
}
```
