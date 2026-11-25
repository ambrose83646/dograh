# Calling platform verification

- Result: **PASS** (26 of 26 checks)
- Service: https://app.danadial.com
- Run: 1119212154 (2026-11-19T21:21:54.936070+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| While public signup is closed, a person without the operator secret cannot sign up | PASS | HTTP 403 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules', 'start_caller_id_verification'] |
| Each new user gets a separate account with its own Twilio subaccount, its own allowance, and no bought number | PASS | accounts 8 and 9; subaccounts ...b7b02c and ...7b5330; 10.0 free minutes each |
| Only the operator can give an account a number for inbound calls | PASS | clinic number +12088864742; user attempt: HTTP 404 |
| A user with no caller ID cannot place a call, and cannot make the service phone an unapproved number for a check | PASS | no caller ID: 'This account has no caller ID yet. Use start_caller_id_verification with a phone number the user owns, then place the call.' |
| A user verifies a phone they own with a keypad code and then calls from that number, with no number bought | PASS | caller ID +12085050523 |
| The other user's account does not gain that caller ID | PASS |  |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 15, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 221 s, 15 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-5307; digits heard: 9903141988803141988845953075307153079854 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 13 turns; from +12085050523 |
| Twilio recorded the outbound leg in the caller's subaccount and the inbound leg in the clinic's subaccount | PASS | 2 call records in the caller's subaccount, 1 in the clinic's |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 16 not found' / 'Call 15 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/16": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user at the free allowance cannot start another call | PASS | used 3.7 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| The operator restores the allowance and the user can call again | PASS |  |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 15: completed, 221 s, +12085050523 to +12088864742

```
[2026-11-19T21:22:24.239+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-19T21:22:29.282+00:00] assistant: She’s a new patient and would prefer a Wednesday morning.
[2026-11-19T21:22:40.242+00:00] user: Thank you for calling. We're closed on Wednesday mornings for staff training, so I can't offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T21:22:56.843+00:00] assistant: Thank you for letting me know. Maria cannot come in the afternoon, so Thursday at nine in the morning would be perfect. Can we please book that appointment for her?
[2026-11-19T21:23:07.762+00:00] user: Absolutely. I can book Maria for Thursday at nine in the morning since she's a new patient. I'll need her full name and date of birth to complete the booking.
[2026-11-19T21:23:17.405+00:00] assistant: Thank you. Her full name is Maria Lopez, and her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-19T21:23:17.519+00:00] user: Could you please provide those details?
[2026-11-19T21:23:17.569+00:00] assistant: Of course. Her name is Maria Lopez. That’s M-A-R-I-A L-O-P-E-Z. Her date of birth is March fourteenth, nineteen eighty-eight. That’s zero three, one four, one nine eight eight. Is that clear?
[2026-11-19T21:23:37.600+00:00] user: Thank you for spelling that out. Let me confirm what I have.
Her name is Maria Lopez. You spelled it m a r i a l o p, but I think you may have left off the last letter. Is her last name spelled l o p e z with a z at the end?
for her date of birth, you said zero three one four one nine eight eight. That's March fourteenth nineteen eighty eight. Is that correct?
[2026-11-19T21:24:08.422+00:00] assistant: Yes, that’s correct—her last name is spelled L-O-P-E-Z, with a Z at the end. And her date of birth is March fourteenth, nineteen eighty-eight—zero three, one four, one nine eight eight.
[2026-11-19T21:24:24.482+00:00] user: Thank you for confirming. I have Mario Lopez, spelled m a r i a l o p e z, and her date of birth as zero three one four one nine eight eight, which is March fourteenth nineteen eighty eight. Since Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, cancellations with less than twenty four hours notice will have a forty five dollar fee. Her cleaning appointment is booked for Thursday at nine in the morning. <lang:en> The confirmation code is r d five three zero seven. That's r as in river, d as in dental, five three zero seven. Could you please repeat that code back to me?
one character at a time?
[2026-11-19T21:25:13.477+00:00] assistant: Yes, of course. The confirmation code is:  
R as in river,  
D as in dental,  
Five,  
Three,  
Zero,  
Seven.  

So that’s R, D, 5, 3, 0, 7. Is that correct?
[2026-11-19T21:25:28.082+00:00] user: Yes.
That's correct.
The confirmation code is r d five three zero seven. I have Maria Lopez booked for a cleaning on Thursday at nine in the morning with her date of birth as March fourteenth nineteen eighty eight. She should bring a photo ID and her insurance card, and there's a forty five dollar fee for cancellations with less than twenty four hours notice. Is there anything else I can help you with today?
[2026-11-19T21:25:53.565+00:00] assistant: No, that’s everything I needed. Thank you for your help and for confirming all the details. Have a great day!
[2026-11-19T21:26:00.883+00:00] assistant: Thank you so much for your help. Goodbye!
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "The assistant scheduled a new patient cleaning appointment for Maria Lopez, date of birth March 14, 1988, at Riverside Dental for Thursday at 9:00 AM. The front desk confirmed the spelling of her name, date of birth, and provided the confirmation code RD5307. The assistant repeated the code back, and all details were confirmed, including instructions to bring a photo ID and insurance card and information about the cancellation fee.",
  "follow_up_needed": ""
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 16: completed, 222 s, +12085050523 to +12088864742

```
[2026-11-19T21:22:23.187+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-19T21:22:29.848+00:00] user: Hello. I'm calling on behalf of Maria Lopez to book a teeth cleaning appointment. She's a new patient and would prefer a Wednesday morning.
[2026-11-19T21:22:39.724+00:00] assistant: Thank you for calling. We’re closed on Wednesday mornings for staff training, so I can’t offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T21:22:57.369+00:00] user: Thank you for letting me know. Maria cannot come in the afternoon, so Thursday at nine in the morning would be perfect. Can we please book that appointment for her?
[2026-11-19T21:23:07.167+00:00] assistant: Absolutely, I can book Maria for Thursday at nine in the morning. Since she’s a new patient, I’ll need her full name and date of birth to complete the booking. Could you please provide those details?
[2026-11-19T21:23:20.090+00:00] user: Of course. Her name is Maria Lopez. That's m a r i a l o p. Her date of birth is March fourteenth nineteen eighty eight.
That's zero three one four one nine eight eight.
Is that clear?
[2026-11-19T21:23:37.014+00:00] assistant: Thank you for spelling that out. Let me confirm what I have:

Her name is Maria Lopez. You spelled it m a r i a l o p, but I think you may have left off the last letter. Is her last name spelled l o p e z, with a z at the end?

For her date of birth, you said zero three one four one nine eight eight. That’s March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-19T21:24:09.368+00:00] user: Yes. That's correct. Her last name is spelled l o p e z with a z at the end.
And her date of birth is March fourteenth nineteen eighty eight.
zero three one four one nine eight eight.
[2026-11-19T21:24:23.824+00:00] assistant: Thank you for confirming. I have Maria Lopez, spelled m a r i a l o p e z, and her date of birth as zero three one four one nine eight eight, which is March fourteenth, nineteen eighty-eight.

Since Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, cancellations with less than twenty-four hours’ notice will have a forty-five dollar fee.

Her cleaning appointment is booked for Thursday at nine in the morning. The confirmation code is R D 5 3 0 7. That’s R as in river, D as in dental, five, three, zero, seven. Could you please repeat that code back to me, one character at a time?
[2026-11-19T21:25:14.011+00:00] user: Yes. Of course.
The confirmation code is r as in river, d as in dental, five three zero seven. So that's r d five three zero seven. Is that correct?
[2026-11-19T21:25:27.673+00:00] assistant: Yes, that’s correct. The confirmation code is r d five three zero seven.

I have Maria Lopez booked for a cleaning on Thursday at nine in the morning, with her date of birth as March fourteenth, nineteen eighty-eight. She should bring a photo ID and her insurance card, and there’s a forty-five dollar fee for cancellations with less than twenty-four hours’ notice.

Is there anything else I can help you with today?
[2026-11-19T21:25:54.090+00:00] user: No. That's everything I needed.
Thank you for your help and for confirming all the details. Have a great day.
[2026-11-19T21:26:02.036+00:00] assistant: Thank you for calling, and have a wonderful day. Goodbye!
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller phoned on behalf of Maria Lopez to book a new patient teeth cleaning appointment, requesting a Wednesday morning. The assistant explained that Wednesday mornings are unavailable and offered alternative times; the caller chose Thursday at 9 a.m. The assistant booked the appointment, confirmed Maria's details, provided a confirmation code, and reminded the caller about required documents and the cancellation policy. No callback number or additional message was left."
}
```
