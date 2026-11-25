# Calling platform verification

- Result: **PASS** (52 of 52 checks)
- Service: http://localhost:8000
- Run: 1120181455 (2026-11-20T18:14:55.702211+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A person without the operator secret cannot make an email account | PASS | HTTP 403 |
| A sign-in request sends one text with a code; a second request in the same minute, a number abroad, and a stranger while signup is closed get no text | PASS | first 200, second 429, abroad 403, closed n/a, texts 1 |
| Only the right code for the right number signs in, and a code works one time | PASS | wrong 401, other number 401, right 200, replay 401 |
| After five wrong guesses the code is dead, and the same phone signs in to the same account, not a new one | PASS | guesses [401, 401, 401, 401, 401], right code after them 401, same account True |
| The sign-in answer gives the real end of the token; sign-out stops that token at once and leaves the user's other session | PASS | token lifetime 30.0 days, same as in the token: True; before 200, sign-out 204, after 401, other session 200, no token 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500019 and 500020; subaccounts ...b81591 and ...925252; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| A phone number that belongs to one account cannot be the caller ID of a different account | PASS | refusal: 'This phone number belongs to another account. One phone number can be used on one account only.' |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | PASS | abroad: 'Calls to this country are not available. Allowed prefixes: +1.'; premium: 'This service calls numbers in the United States and Canada only. This number is not a valid number there, or it is in a different country or a premium-rate range.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 107, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "minutes_remaining": 10.0, "max_minutes_this_call": 10.0, "minutes_note": null, "next_step": "The call is in progres |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 215 s, 24 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-7789; digits heard: 29989977894577899778977897789977899 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 23 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 108 not found' / 'Call 107 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/108": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /a |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 3 8 4. Goodb' |
| With no voicemail message from the client, the service leaves a message written from the task: it names the caller and the person, asks for a reply, and keeps the private details out | PASS | answered_by voicemail, 21 s; agent said: 'hello. this is an ai assistant calling for riverside dental. this message is for sam carter. i’m calling about a private matter. please contact riverside dental. thank you. goodbye.' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 68 s, price 160; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m calling for dana reyes to ask about the bike in your ad. is it still for sale? sam, are you still there? the bike is still for sa' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by end_call; summary: 'Dana Reyes asked whether the bike in Sam Carter’s ad was still for sale. Sam confirmed it was available for $160 and ended the call.' |
| The agent gets through a two-step phone menu that takes keys only: the menu lets the call through only on the right option and the full member number | PASS | menu wanted ['2', '17799']; reached the desk: True; key entries Twilio heard: 2; service reports ['2', '17799'] |
| Behind the menu the agent brings back the answer of the desk, and the call record lists the keys it pressed | PASS | answered_by phone_menu, keys ['2', '17799'], 60 s; summary: 'I called Lakeside Medical Group for Sam Carter to ask about the next check-up opening. Robin at the appointments desk said the next opening was Wednesday at 11:00 and put Sam down for that time.' |
| The agent presses no keys on calls that a person, a voicemail box, or a call screener answers | PASS | keys: [None, None, None] |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 3.6 min of 1; refusal: 'The 1 free call minutes are used. The user must start the monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can get more minutes at https://danadial.com/dashboard/billing. Until then this account cannot make or answer calls.'; after renewal used 0.0 |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must start the monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| The assistant is warned when less than 20% of the minutes remain, and not when many remain | PASS | note: 'Less than 20% of the call minutes of this period remain: 0.5 of 6. Tell the user. A call ends when the minutes are used. The minutes renew on December 20, 2026; the user can get more minutes at https://danadial.com/dashboard/billing.'; place_call said minutes_remaining 0.5, max_minutes_this_c |
| A call that starts with about half a minute left ends when the minutes are used, and the next call is refused | PASS | 35 s were left (to the nearest 3 s); the call ran 34 s; the hold script is 100 s long; after it minutes_remaining 0.0; refusal: 'The call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can get more minutes at https://d |
| With more than 5 minutes left no minute pack is requested; a call that takes the minutes below 5 requests one pack while the call is in progress, and later status requests do not request it again | PASS | request before the call: None; request seen while the call was in_progress; call ran 0 s; billing system received 1 request(s), all signed: True, remaining seconds in them: [299] |
| A paid pack adds its minutes one time, a user cannot add a pack, and the next low state requests the next pack | PASS | user 404; remaining 320 s -> 380 s after the same payment two times; billing system received 2 request(s), all signed: True, remaining seconds in them: [299, 250] |
| A call is not cut at the remaining minutes while a pack can still come; with no payment the next call is refused; at the limit of packs no more are requested and the refusal names the limit | PASS | 40 s were left and the hold line call ran 155 s (hold_line); refusal with no payment: 'The call minutes of this account are used. A paid pack of more minutes is added automatically, and that payment is not complete. Try again in one minute. If the call is refused again, the user must check the payme |
| At the renewal the unused pack minutes stay and the used pack minutes do not come back | PASS | pack seconds after the renewal: 70 (expected 70), after a second renewal: 70; minutes_total 11.2 |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 116, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 107: completed, 215 s, +12085050523 to +12088864742

```
[2026-11-20T18:17:57.989+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T18:18:04.243+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening?
[2026-11-20T18:18:13.827+00:00] user: Hi. I'm here. We're closed Wednesday morning, but I have a cleaning opening next Tuesday at two thirty or Thursday at nine. Which works better for Maria?
[2026-11-20T18:18:24.125+00:00] assistant: Thursday at nine works for Maria. Is that next Thursday morning?
[2026-11-20T18:18:30.227+00:00] user: Yes. Next Thursday morning at nine. What's Maria's date of birth?
[2026-11-20T18:18:35.926+00:00] assistant: Next Thursday at nine. Maria’s date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-20T18:18:43.827+00:00] user: Thank you. I have Maria Lopez, born March fourteenth nineteen eighty eight for a new patient cleaning next Thursday at nine. Is that correct?
[2026-11-20T18:18:54.007+00:00] assistant: Yes, that’s correct.
[2026-11-20T18:18:57.347+00:00] user: Maria is booked for next Thursday at nine. Your confirmation code is r d seven seven eight nine. Please bring a photo ID and insurance card. Cancellations with less than twenty four hours notice cost forty five dollars. Have I got everything right?
And is there anything else you need?
[2026-11-20T18:19:15.805+00:00] assistant: I have next Thursday, November twenty-sixth, at nine, with a photo ID and insurance card, and a forty-five-dollar fee for cancellations with less than twenty-four hours’ notice. I heard the confirmation code as R, D, seven, seven, eight, nine. Is that correct?
[2026-11-20T18:19:34.387+00:00] user: Yes. That's correct. a d seven seven eight nine.
I've noted Maria's cleaning for next Thursday at nine. Is there anything else you need?
[2026-11-20T18:19:44.046+00:00] assistant: Sorry, I heard you say A, D, seven, seven, eight, nine, which differs from the code I read back. Could you please confirm the first letter?
[2026-11-20T18:19:53.907+00:00] user: Sorry for the confusion. The first letter is r as in Riverside. The full code is r d seven seven eight nine. Is that what you have?
[2026-11-20T18:20:05.286+00:00] assistant: Yes, I have R, D, seven, seven, eight, nine. Is that correct?
[2026-11-20T18:20:12.548+00:00] user: Not quite. The first letter is r, not a. The code is r d seven seven eight nine. Could you repeat it back?
[2026-11-20T18:20:22.607+00:00] assistant: R as in Riverside, D, seven, seven, eight, nine. Is that correct?
[2026-11-20T18:20:29.507+00:00] user: Yes. That's correct.
a d seven seven eight nine. I have Maria Lopez booked for next Thursday at nine. Do you need anything else?
[2026-11-20T18:20:38.849+00:00] assistant: I’m sorry, you said A again. I have R as in Riverside, D, seven, seven, eight, nine. Is R the correct first letter?
[2026-11-20T18:20:49.908+00:00] user: No. The first letter is r as in Riverside, not a. The code is r d seven seven eight nine. Could you say the first letter back to me?
[2026-11-20T18:21:01.010+00:00] assistant: R as in Riverside.
[2026-11-20T18:21:04.549+00:00] user: Yes. R is correct. I have Maria booked for next Thursday at nine. Do you need anything else?
[2026-11-20T18:21:11.134+00:00] assistant: No, thank you. Maria is booked for Thursday, November twenty-sixth, at nine. I have the confirmation code, what she needs to bring, and the late-cancellation fee. Goodbye.
[2026-11-20T18:21:24.947+00:00] user: Thank you for calling. Goodbye.
[2026-11-20T18:21:28.695+00:00] assistant: Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental booked Maria Lopez for a new-patient cleaning next Thursday at 9 a.m.; Wednesday morning was unavailable. The confirmation code is RD7789. Maria should bring a photo ID and insurance card, and cancellations with less than 24 hours\u2019 notice incur a $45 fee.",
  "follow_up_needed": "Maria should bring a photo ID and insurance card to the appointment."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 108: completed, 212 s, +12085050523 to +12088864742

```
[2026-11-20T18:17:57.254+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T18:18:05.066+00:00] user: Hi. I'm calling for Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening?
[2026-11-20T18:18:13.364+00:00] assistant: Hi, I’m here. We’re closed Wednesday morning, but I have a cleaning opening next Tuesday at two thirty or Thursday at nine. Which works better for Maria?
[2026-11-20T18:18:24.667+00:00] user: Thursday at nine works for Maria. Is that next Thursday morning?
[2026-11-20T18:18:29.605+00:00] assistant: Yes, next Thursday morning at nine. What’s Maria’s date of birth?
[2026-11-20T18:18:36.347+00:00] user: Next Thursday at nine. Maria's date of birth is March fourteenth nineteen eighty eight.
[2026-11-20T18:18:43.286+00:00] assistant: Thank you. I have Maria Lopez, born March fourteenth, nineteen eighty-eight, for a new-patient cleaning next Thursday at nine. Is that correct?
[2026-11-20T18:18:54.746+00:00] user: Yes. That's correct.
[2026-11-20T18:18:56.809+00:00] assistant: Maria is booked for next Thursday at nine. Your confirmation code is R, D, seven, seven, eight, nine. Please bring a photo ID and insurance card. Cancellations with less than twenty-four hours’ notice cost forty-five dollars. Have I got everything right, and is there anything else you need?
[2026-11-20T18:19:16.665+00:00] user: I have next Thursday, November twenty sixth at nine, with a photo ID and insurance card and a forty five dollar fee for cancellations with less than twenty four hours notice. I heard the confirmation code as r d seven seven eight nine. Is that correct?
[2026-11-20T18:19:34.003+00:00] assistant: Yes, that’s correct: R, D, seven, seven, eight, nine. I’ve noted Maria’s cleaning for next Thursday at nine. Is there anything else you need?
[2026-11-20T18:19:44.667+00:00] user: Sorry. I heard you say a d seven seven eight nine, which differs from the code I read back. Could you please confirm the first letter?
[2026-11-20T18:19:53.324+00:00] assistant: Sorry for the confusion. The first letter is R, as in Riverside. The full code is R, D, seven, seven, eight, nine. Is that what you have?
[2026-11-20T18:20:05.788+00:00] user: Yes. I have a d seven seven eight nine. Is that correct?
[2026-11-20T18:20:12.045+00:00] assistant: Not quite. The first letter is R, not A. The code is R, D, seven, seven, eight, nine. Could you repeat it back?
[2026-11-20T18:20:23.147+00:00] user: R as in Riverside, d seven seven eight nine.
Is that correct?
[2026-11-20T18:20:28.728+00:00] assistant: Yes, that’s correct: R, D, seven, seven, eight, nine. I have Maria Lopez booked for next Thursday at nine. Do you need anything else?
[2026-11-20T18:20:39.546+00:00] user: I'm sorry. You said a again. I have a as in Riverside, d seven seven eight nine. Is a the correct first letter?
[2026-11-20T18:20:49.250+00:00] assistant: No, the first letter is R, as in Riverside—not A. The code is R, D, seven, seven, eight, nine. Could you say the first letter back to me?
[2026-11-20T18:21:01.947+00:00] user: r as in Riverside.
[2026-11-20T18:21:04.010+00:00] assistant: Yes, R is correct. I have Maria booked for next Thursday at nine. Do you need anything else?
[2026-11-20T18:21:11.627+00:00] user: No. Thank you.
Maria is booked for Thursday, November twenty sixth at nine. I have the confirmation code, what she needs to bring, and the late cancellation fee.
Goodbye.
[2026-11-20T18:21:24.533+00:00] assistant: Thank you for calling; goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller booked a new-patient teeth cleaning for Maria Lopez for Thursday, November 26 at 9 a.m. The assistant confirmed the booking and code RD7789, advised bringing a photo ID and insurance card, and explained the $45 fee for cancellations with less than 24 hours\u2019 notice. No callback number or message was left."
}
```

## Call answered by a voicemail box

Call 109: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T18:21:52.176+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T18:21:58.566+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 3 8 4. Goodbye.
```

## Call answered by a call screener, then a person

Call 111: completed, 68 s, +12088864742 to +12085050523

```
[2026-11-20T18:22:57.992+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T18:23:02.796+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T18:23:11.433+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T18:23:24.465+00:00] assistant: Hi Sam, I’m calling for Dana Reyes to ask about the bike in your ad. Is it still for sale?
[2026-11-20T18:23:34.545+00:00] assistant: Sam, are you still there?
[2026-11-20T18:23:36.072+00:00] user: Yes. The bike is still for sale.
The price is one hundred sixty dollars. That is all I can tell you. Goodbye.
[2026-11-20T18:23:45.427+00:00] assistant: The bike is still for sale for one hundred sixty dollars. Thank you, Sam. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes asked whether the bike in Sam Carter\u2019s ad was still for sale. Sam confirmed it was available for $160 and ended the call.",
  "follow_up_needed": ""
}
```

## Call answered by a phone menu that takes keys only

Call 112: completed, 60 s, +12088864742 to +12085050523

```
[2026-11-20T18:24:19.455+00:00] user: Thank you for calling Lakeside Medical Group. Please listen to all options. For billing, press one. For appointments, press two. For medical records, press three. For the pharmacy, press four.
Please enter the patient's five digit member number.
Thank you.
One moment, please.
Appointments desk. This is Robin. How can I help you?
[2026-11-20T18:24:52.327+00:00] assistant: Hi, I’m an AI assistant calling for Sam Carter to ask about the next opening for a check-up. What day and time is available?
[2026-11-20T18:25:03.374+00:00] user: Okay.
The next opening for a checkup is Wednesday at eleven o'clock. I have put the patient down for that time. Goodbye.
[2026-11-20T18:25:13.250+00:00] assistant: Wednesday at eleven o’clock. Thank you.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "I called Lakeside Medical Group for Sam Carter to ask about the next check-up opening. Robin at the appointments desk said the next opening was Wednesday at 11:00 and put Sam down for that time.",
  "follow_up_needed": ""
}
```
