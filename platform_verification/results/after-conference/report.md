# Calling platform verification

- Result: **PASS** (52 of 52 checks)
- Service: http://localhost:8000
- Run: 1120201135 (2026-11-20T20:11:35.289608+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A person without the operator secret cannot make an email account | PASS | HTTP 403 |
| A sign-in request sends one text with a code; a second request in the same minute, a number abroad, and a stranger while signup is closed get no text | PASS | first 200, second 429, abroad 403, closed n/a, texts 1 |
| Only the right code for the right number signs in, and a code works one time | PASS | wrong 401, other number 401, right 200, replay 401 |
| After five wrong guesses the code is dead, and the same phone signs in to the same account, not a new one | PASS | guesses [401, 401, 401, 401, 401], right code after them 401, same account True |
| The sign-in answer gives the real end of the token; sign-out stops that token at once and leaves the user's other session | PASS | token lifetime 30.0 days, same as in the token: True; before 200, sign-out 204, after 401, other session 200, no token 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500029 and 500030; subaccounts ...b2064c and ...4634e1; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| A phone number that belongs to one account cannot be the caller ID of a different account | PASS | refusal: 'This phone number belongs to another account. One phone number can be used on one account only.' |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| Calls to a number outside the United States and Canada, and to a premium-rate number, are refused and start nothing | PASS | abroad: 'Calls to this country are not available. Allowed prefixes: +1.'; premium: 'This service calls numbers in the United States and Canada only. This number is not a valid number there, or it is in a different country or a premium-rate range.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 144, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "minutes_remaining": 10.0, "max_minutes_this_call": 10.0, "minutes_note": null, "next_step": "The call is in progres |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 138 s, 18 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-2983; digits heard: 2998992983452992983 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 18 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 145 not found' / 'Call 144 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/145": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /a |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 4 5 1. Goodb' |
| With no voicemail message from the client, the service leaves a message written from the task: it names the caller and the person, asks for a reply, and keeps the private details out | PASS | answered_by voicemail, 22 s; agent said: 'hello. this is an ai assistant calling for riverside dental. this message is for sam carter. i’m calling about a matter that needs his attention. please contact riverside dental. thank you. goodbye.' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 69 s, price 160; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m an ai assistant calling for dana reyes about the bike in your ad. is it still for sale? sam, are you still there? the bike is sti' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by user_hangup; summary: "Dana Reyes asked whether Sam Carter's advertised bike was still for sale. Sam confirmed it was and said the price was $160 before ending the call." |
| The agent gets through a two-step phone menu that takes keys only: the menu lets the call through only on the right option and the full member number | PASS | menu wanted ['2', '23329']; reached the desk: True; key entries Twilio heard: 2; service reports ['2', '23329'] |
| Behind the menu the agent brings back the answer of the desk, and the call record lists the keys it pressed | PASS | answered_by phone_menu, keys ['2', '23329'], 71 s; summary: 'Called Lakeside Medical Group to ask about the next available check-up for Sam Carter. Robin said the next opening was Tuesday at 10:00 and put Sam down for that time.' |
| The agent presses no keys on calls that a person, a voicemail box, or a call screener answers | PASS | keys: [None, None, None] |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.3 min of 1; refusal: 'The 1 free call minutes are used. The user must start the monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| A user cannot give a plan to their own account, and a period that ends before it starts is refused | PASS | tenant 404, backwards 422 |
| A monthly plan unblocks a user whose free minutes are used, and earlier calls do not count against the plan | PASS | status {'plan': 'Starter', 'minutes_total': 100.0, 'minutes_used': 0.0, 'can_call': True} |
| A plan with its minutes used blocks calls until the renewal starts the count again | PASS | refusal: 'The call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can get more minutes at https://danadial.com/dashboard/billing. Until then this account cannot make or answer calls.'; after renewal used 0.0 |
| When a plan period is over without a renewal the user cannot call and does not get the free minutes again | PASS | refusal: 'The 1 free call minutes are used. The user must start the monthly plan at https://danadial.com/dashboard/billing before this account can make or answer more calls.' |
| The assistant is warned when less than 20% of the minutes remain, and not when many remain | PASS | note: 'Less than 20% of the call minutes of this period remain: 0.6 of 5. Tell the user. A call ends when the minutes are used. The minutes renew on December 20, 2026; the user can get more minutes at https://danadial.com/dashboard/billing.'; place_call said minutes_remaining 0.6, max_minutes_this_c |
| A call that starts with about half a minute left ends when the minutes are used, and the next call is refused | PASS | 35 s were left (to the nearest 3 s); the call ran 39 s; the hold script is 100 s long; after it minutes_remaining 0.0; refusal: 'The call minutes of the Starter plan are used for this period. The minutes renew on December 20, 2026. To call before that date, the user can get more minutes at https://d |
| With more than 5 minutes left no minute pack is requested; a call that takes the minutes below 5 requests one pack while the call is in progress, and later status requests do not request it again | PASS | request before the call: None; request seen while the call was in_progress; call ran 0 s; billing system received 1 request(s), all signed: True, remaining seconds in them: [299] |
| A paid pack adds its minutes one time, a user cannot add a pack, and the next low state requests the next pack | PASS | user 404; remaining 320 s -> 380 s after the same payment two times; billing system received 2 request(s), all signed: True, remaining seconds in them: [299, 250] |
| A call is not cut at the remaining minutes while a pack can still come; with no payment the next call is refused; at the limit of packs no more are requested and the refusal names the limit | PASS | 40 s were left and the hold line call ran 155 s (hold_line); refusal with no payment: 'The call minutes of this account are used. A paid pack of more minutes is added automatically, and that payment is not complete. Try again in one minute. If the call is refused again, the user must check the payme |
| At the renewal the unused pack minutes stay and the used pack minutes do not come back | PASS | pack seconds after the renewal: 70 (expected 70), after a second renewal: 70; minutes_total 11.2 |
| The operator restores the allowance and the user can call again | PASS |  |
| A user on a plan, with the free minutes used, places a real call; the operator can end the plan | PASS | call 153, end plan 200 |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 144: completed, 138 s, +12085050523 to +12088864742

```
[2026-11-20T20:14:31.518+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T20:14:36.690+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening?
[2026-11-20T20:14:45.559+00:00] user: Wednesday morning isn't available.
Next week, I can offer Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T20:14:53.773+00:00] assistant: Thursday at nine works for Maria. Can you book that for her?
[2026-11-20T20:14:58.998+00:00] user: Thursday at nine for Maria's cleaning.
What's Maria's date of birth?
[2026-11-20T20:15:04.493+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T20:15:08.599+00:00] user: March fourteenth nineteen eighty eight. I have Maria Lopez's name and date of birth. Do you agree to book her cleaning for next Thursday at nine in the morning?
[2026-11-20T20:15:18.814+00:00] assistant: Yes, please book Maria for next Thursday, November twenty-sixth, at nine in the morning.
[2026-11-20T20:15:25.638+00:00] user: Maria Lopez is booked for Thursday, November twenty sixth at nine in the morning. Her confirmation code is r d two nine eight three. Please have her bring a photo ID and insurance card. Cancellations with less than twenty four hours notice cost twenty five dollars. Is there anything else I can help with?
[2026-11-20T20:15:45.015+00:00] assistant: I have the confirmation code as R, D, two, nine, eight, three. Is that correct?
[2026-11-20T20:15:53.398+00:00] user: Yes. That's correct.
[2026-11-20T20:15:54.976+00:00] assistant: Thank
[2026-11-20T20:15:55.638+00:00] user: r d two nine. I've noted Maria's cleaning for Thursday, November twenty sixth at nine in the morning. Do you need anything else?
[2026-11-20T20:16:05.339+00:00] assistant: The full code is R, D, two, nine, eight, three—not R, D, two, nine. Could you confirm the full code?
[2026-11-20T20:16:15.638+00:00] user: Yes. The full code is r d two nine eight three. Is there anything else you need?
[2026-11-20T20:16:21.780+00:00] assistant: Thank you. Maria is booked for Thursday, November twenty-sixth, at nine in the morning. Her code is R, D, two, nine, eight, three. She’ll bring a photo ID and insurance card, and the late-cancellation fee is twenty-five dollars. Goodbye.
[2026-11-20T20:16:40.278+00:00] user: Thank you for calling. Goodbye.
[2026-11-20T20:16:44.422+00:00] assistant: Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Called Riverside Dental to book Maria Lopez for a new-patient teeth cleaning, preferably Wednesday morning. Wednesday was unavailable, so she was booked for Thursday, November 26, at 9:00 a.m.; the confirmed code is RD2983. The office said to bring a photo ID and insurance card and noted a $25 fee for cancellations with less than 24 hours\u2019 notice.",
  "follow_up_needed": "Maria should bring a photo ID and insurance card to the appointment."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 145: completed, 134 s, +12085050523 to +12088864742

```
[2026-11-20T20:14:31.635+00:00] user: Hi.
[2026-11-20T20:14:30.169+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T20:14:37.173+00:00] user: Hi. I'm calling for Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening?
[2026-11-20T20:14:44.973+00:00] assistant: Wednesday morning isn’t available. Next week, I can offer Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T20:14:54.293+00:00] user: Thursday at nine works for Maria. Can you book that for her?
[2026-11-20T20:14:58.373+00:00] assistant: Thursday at nine for Maria’s cleaning. What’s Maria’s date of birth?
[2026-11-20T20:15:05.093+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T20:15:08.214+00:00] assistant: March fourteenth, nineteen eighty-eight. I have Maria Lopez’s name and date of birth. Do you agree to book her cleaning for next Thursday at nine in the morning?
[2026-11-20T20:15:19.254+00:00] user: Yes. Please book Maria for next Thursday, November twenty sixth at nine in the morning.
[2026-11-20T20:15:25.260+00:00] assistant: Maria Lopez is booked for Thursday, November twenty-sixth, at nine in the morning. Her confirmation code is R, D, two, nine, eight, three. Please have her bring a photo ID and insurance card. Cancellations with less than twenty-four hours’ notice cost twenty-five dollars. Is there anything else I can help with?
[2026-11-20T20:15:45.732+00:00] user: I have the confirmation code as r d two nine eight three. Is that correct?
[2026-11-20T20:15:52.615+00:00] assistant: Yes, that’s correct: R, D, two, nine, eight, three.
[2026-11-20T20:15:55.653+00:00] user: Thank you.
[2026-11-20T20:15:57.737+00:00] assistant: I’ve noted Maria’s cleaning for Thursday, November twenty-sixth, at nine in the morning. Do you need anything else?
[2026-11-20T20:16:06.212+00:00] user: The full code is r d two nine eight three, not r d two nine. Could you confirm the full code?
[2026-11-20T20:16:14.860+00:00] assistant: Yes, the full code is R, D, two, nine, eight, three. Is there anything else you need?
[2026-11-20T20:16:22.213+00:00] user: Thank you. Maria is booked for Thursday, November twenty sixth at nine in the morning. Her code is r d two nine eight three. She'll bring a photo ID and insurance card, and the late cancellation fee is twenty five dollars. Goodbye.
[2026-11-20T20:16:39.661+00:00] assistant: Thank you for calling—goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller booked a new-patient teeth cleaning for Maria Lopez on Thursday, November 26, at 9 a.m. The assistant confirmed booking code RD2983, asked her to bring a photo ID and insurance card, and explained the $25 fee for cancellations with less than 24 hours\u2019 notice. No callback number was left."
}
```

## Call answered by a voicemail box

Call 146: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T20:17:21.494+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T20:17:28.205+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 4 5 1. Goodbye.
```

## Call answered by a call screener, then a person

Call 148: completed, 69 s, +12088864742 to +12085050523

```
[2026-11-20T20:18:27.413+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T20:18:32.496+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T20:18:41.134+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T20:18:54.084+00:00] assistant: Hi Sam, I’m an AI assistant calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T20:19:05.045+00:00] assistant: Sam, are you still there?
[2026-11-20T20:19:05.853+00:00] user: Yes. The bike is still for sale.
The price is one hundred sixty dollars. That is all I can tell you. Goodbye.
[2026-11-20T20:19:13.885+00:00] assistant: The bike is still for sale at one hundred sixty dollars. Thank you, goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes asked whether Sam Carter's advertised bike was still for sale. Sam confirmed it was and said the price was $160 before ending the call.",
  "follow_up_needed": ""
}
```

## Call answered by a phone menu that takes keys only

Call 149: completed, 71 s, +12088864742 to +12085050523

```
[2026-11-20T20:19:47.863+00:00] user: Thank you for calling Lakeside Medical Group. Please listen to all options. For the pharmacy, press one. For appointments, press two. For medical records, press three. For billing, press four.
Please enter the patient's five digit member number.
Thank you. One moment, please.
Appointments desk. This is Robin. How can I help you?
[2026-11-20T20:20:21.574+00:00] assistant: I’m calling for Sam Carter to ask when the next check-up appointment is available.
[2026-11-20T20:20:32.225+00:00] user: Okay.
The next opening for a checkup is Tuesday at ten o'clock.
I have put the patient down for that time. Goodbye.
[2026-11-20T20:20:42.096+00:00] assistant: Thank you. I have Tuesday at ten o’clock for Sam Carter’s check-up. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Called Lakeside Medical Group to ask about the next available check-up for Sam Carter. Robin said the next opening was Tuesday at 10:00 and put Sam down for that time.",
  "follow_up_needed": ""
}
```
