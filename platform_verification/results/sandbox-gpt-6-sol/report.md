# Calling platform verification

- Result: **PASS** (30 of 30 checks)
- Service: http://localhost:8000
- Run: 1120033817 (2026-11-20T03:38:17.683024+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification', 'update_settings'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 500003 and 500004; subaccounts ...595668 and ...0a899a; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 49, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 171 s, 20 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-2831; digits heard: 299891452831954283192831 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 21 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 50 not found' / 'Call 49 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/50": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user changes the agent's voice through MCP, and the other user's voice does not change | PASS | clinic voice: ara; unknown voice: 'Unknown voice. The voices are: eve, ara, leo, rex, sal.' |
| When a voicemail box answers, the agent leaves the given message, ends the call, and reports voicemail | PASS | answered_by voicemail, 20 s; agent said: 'Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 9 3 5. Goodb' |
| When a call screener answers, the agent gives the name and reason, waits, and then does the task with the person | PASS | answered_by person, screener True, 68 s, price 160; agent said: 'this is an ai assistant calling for dana reyes, about the bike you advertised. hi sam, i’m an ai assistant calling for dana reyes about the bike in your ad. is it still for sale? sam, are you still there? the bike is sti' |
| When the other person ends the call first, the assistant still gets a result summary with the answer | PASS | ended by end_call; summary: 'Dana Reyes asked whether Sam Carter’s advertised bike was still for sale. Sam confirmed it was available for $160 and then ended the call.' |
| A call that a person answered reports that a person answered | PASS | answered_by person |
| A user at the free allowance cannot start another call | PASS | used 2.9 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 49: completed, 171 s, +12085050523 to +12088864742

```
[2026-11-20T03:38:45.333+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-20T03:38:50.660+00:00] assistant: Hi, I’m calling for Maria Lopez to book a new-patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T03:38:59.574+00:00] user: We're closed Wednesday mornings for staff training. Next week, I can offer Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T03:39:09.422+00:00] assistant: Thursday at nine works for Maria. May I book that appointment?
[2026-11-20T03:39:15.014+00:00] user: Thursday at nine. I can book it once I have Maria's details. What's her full name?
[2026-11-20T03:39:20.423+00:00] assistant: Maria Lopez.
[2026-11-20T03:39:23.894+00:00] user: Thank you. What's Maria's date of birth?
[2026-11-20T03:39:27.303+00:00] assistant: March fourteenth, nineteen eighty-eight.
[2026-11-20T03:39:31.733+00:00] user: March fourteenth nineteen eighty eight. Can you confirm that's correct?
[2026-11-20T03:39:36.345+00:00] assistant: Yes, that’s correct.
[2026-11-20T03:39:39.494+00:00] user: Thank you. To confirm, you'd like to book Maria Lopez for a new patient cleaning next Thursday at nine in the morning. Is that right?
[2026-11-20T03:39:48.106+00:00] assistant: Yes, next Thursday at nine in the morning is right.
[2026-11-20T03:39:52.773+00:00] user: Maria ist booked für nächste Thursday at neun in der morning. Ihr confirmation code ist r d zwei acht drei one. Please have Maria bring a Foto ID and her insurance card. Cancellations with less than twenty four hours notice cost thirty five dollars. Is there anything else I can help you with?
[2026-11-20T03:40:11.507+00:00] assistant: Thank you. I have Thursday at nine in the morning, a photo ID and insurance card, and a thirty-five-dollar fee for cancellations with less than twenty-four hours’ notice. I heard the confirmation code as R, D, two, eight, three, one. Is that correct?
[2026-11-20T03:40:29.893+00:00] user: Yes. That's correct. a d two eight three one. I've noted Maria Lopez for next Thursday at nine in the morning with a photo ID and insurance card to bring and a thirty five dollar fee for cancellations with less than twenty four hours notice. Is there anything else you need?
[2026-11-20T03:40:46.708+00:00] assistant: I heard you repeat A, D, two, eight, three, one, which differs from R, D, two, eight, three, one. Could you confirm the first letter of the code?
[2026-11-20T03:40:57.894+00:00] user: Sorry for the confusion. The first letter is r. The full code is r d two eight three one. Does that match what you have?
[2026-11-20T03:41:07.588+00:00] assistant: Yes, that matches: R, D, two, eight, three, one. Maria is booked for next Thursday at nine in the morning. Thank you for your help.
[2026-11-20T03:41:17.734+00:00] user: You're welcome. I have Maria Lopez booked for next Thursday at nine in the morning, and the confirmation code is r d two eight three one. Do you need anything else?
[2026-11-20T03:41:28.869+00:00] assistant: No, that’s everything. Thank you. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Riverside Dental booked Maria Lopez for a new-patient cleaning next Thursday at 9:00 a.m.; Wednesday morning was unavailable. The confirmed code is RD2831, and cancellations with less than 24 hours\u2019 notice cost $35.",
  "follow_up_needed": "Maria must bring a photo ID and insurance card."
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 50: completed, 174 s, +12085050523 to +12088864742

```
[2026-11-20T03:38:44.438+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-20T03:38:51.250+00:00] user: Hi. I'm calling from Maria Lopez to book a new patient teeth cleaning, preferably Wednesday morning. Do you have an opening then?
[2026-11-20T03:38:59.140+00:00] assistant: We’re closed Wednesday mornings for staff training. Next week, I can offer Tuesday at two thirty or Thursday at nine. Which works for Maria?
[2026-11-20T03:39:10.051+00:00] user: Thursday at nine works for Maria. May I book that appointment?
[2026-11-20T03:39:14.420+00:00] assistant: Thursday at nine. I can book it once I have Maria’s details. What’s her full name?
[2026-11-20T03:39:20.851+00:00] user: María López.
[2026-11-20T03:39:23.381+00:00] assistant: Thank you. What’s María’s date of birth?
[2026-11-20T03:39:27.891+00:00] user: March fourteenth nineteen eighty eight.
[2026-11-20T03:39:31.141+00:00] assistant: March fourteenth, nineteen eighty-eight. Can you confirm that’s correct?
[2026-11-20T03:39:36.691+00:00] user: Yes. That's correct.
[2026-11-20T03:39:38.945+00:00] assistant: Thank you. To confirm, you’d like to book María López for a new-patient cleaning next Thursday at nine in the morning. Is that right?
[2026-11-20T03:39:48.850+00:00] user: Yes. Next Thursday at nine in the morning is right.
[2026-11-20T03:39:52.383+00:00] assistant: María is booked for next Thursday at nine in the morning. Your confirmation code is R, D, two, eight, three, one. Please have María bring a photo ID and her insurance card. Cancellations with less than twenty-four hours’ notice cost thirty-five dollars. Is there anything else I can help you with?
[2026-11-20T03:40:12.131+00:00] user: Thank you. I have Thursday at nine in the morning, a photo ID and insurance card, and a thirty five dollar fee for cancellations with less than twenty four hours notice. I heard the confirmation code as r d two eight three one. Is that correct?
[2026-11-20T03:40:29.104+00:00] assistant: Yes, that’s correct: R, D, two, eight, three, one. I’ve noted María López for next Thursday at nine in the morning, with a photo ID and insurance card to bring and a thirty-five-dollar fee for cancellations with less than twenty-four hours’ notice. Is there anything else you need?
[2026-11-20T03:40:47.251+00:00] user: I heard you repeat a d two eight three one, which differs from r d two eight three one. Could you confirm the first letter of the code?
[2026-11-20T03:40:57.306+00:00] assistant: Sorry for the confusion. The first letter is R. The full code is R, D, two, eight, three, one. Does that match what you have?
[2026-11-20T03:41:07.971+00:00] user: Yes. That matches. r d two eight three one. Maria is booked for next Thursday at nine in the morning. Thank you for your help.
[2026-11-20T03:41:17.226+00:00] assistant: You’re welcome. I have María López booked for next Thursday at nine in the morning, and the confirmation code is R, D, two, eight, three, one. Do you need anything else?
[2026-11-20T03:41:29.251+00:00] user: No. That's everything.
Thank you. Goodbye.
[2026-11-20T03:41:33.828+00:00] assistant: Thank you for calling; goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller booked a new-patient teeth cleaning for Mar\u00eda L\u00f3pez, initially requesting Wednesday morning. The assistant said the office is closed Wednesday mornings and booked Mar\u00eda for next Thursday at 9 a.m., confirming code RD2831 and advising her to bring a photo ID and insurance card; cancellations with less than 24 hours\u2019 notice cost $35. No callback number was left."
}
```

## Call answered by a voicemail box

Call 51: completed, 20 s, +12088864742 to +12085050523

```
[2026-11-20T03:41:52.212+00:00] user: Hi. You have reached Sam Carter. I cannot take your call right now. Please leave a message after the tone.
[2026-11-20T03:41:59.121+00:00] assistant: Hello, this is the assistant of Riverside Dental with a reminder of your cleaning on Thursday at nine. To change it, call us and give the reference 9 3 5. Goodbye.
```

## Call answered by a call screener, then a person

Call 52: completed, 68 s, +12088864742 to +12085050523

```
[2026-11-20T03:42:22.516+00:00] user: Hi. Before I try to connect you, please say your name and the reason for your call.
[2026-11-20T03:42:27.401+00:00] assistant: This is an AI assistant calling for Dana Reyes, about the bike you advertised.
[2026-11-20T03:42:36.276+00:00] user: Thank you. Please stay on the line.
Hello. This is Sam Carter speaking. Go ahead.
[2026-11-20T03:42:48.469+00:00] assistant: Hi Sam, I’m an AI assistant calling for Dana Reyes about the bike in your ad. Is it still for sale?
[2026-11-20T03:42:58.790+00:00] assistant: Sam, are you still there?
[2026-11-20T03:43:00.756+00:00] user: Yes. The bike is still for sale.
The price is one hundred sixty dollars. That is all I can tell you. Goodbye.
[2026-11-20T03:43:08.832+00:00] assistant: The bike is still for sale at one hundred sixty dollars. Thank you, Sam. Goodbye.
[2026-11-20T03:43:25.512+00:00] assistant: Thank you, Sam. Goodbye.
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "Dana Reyes asked whether Sam Carter\u2019s advertised bike was still for sale. Sam confirmed it was available for $160 and then ended the call.",
  "follow_up_needed": ""
}
```
