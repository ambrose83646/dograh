# Calling platform verification

- Result: **PASS** (20 of 20 checks)
- Service: http://localhost:8000
- Run: 1119055542 (2026-11-19T05:55:42.168357+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules'] |
| Each new user gets a separate account with its own phone number and allowance | PASS | accounts 5 and 6; numbers +12088864742 and +12085050523; 10.0 free minutes each |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 9, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until  |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 239 s, 16 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-6898; digits heard: 299854968986898168986898168968986189954 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 17 turns; from +12085050523 |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 10 not found' / 'Call 9 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/10": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /ap |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user at the free allowance cannot start another call | PASS | used 4.0 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| The operator restores the allowance and the user can call again | PASS |  |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 9: completed, 239 s, +12085050523 to +12088864742

```
[2026-11-19T05:55:49.391+00:00] user: Riverside Dental. This is the front desk. How can I help you?
[2026-11-19T05:56:05.292+00:00] user: Thank you for calling for Maria Lopez. Just to let you know, we're closed on Wednesday mornings for staff training. I can't offer that time. Soonest cleaning appointments we have this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T05:56:23.266+00:00] assistant: Thank you for letting me know. Maria can't do afternoons, so Thursday at nine in the morning would be perfect. Can we please book that appointment for her?
[2026-11-19T05:56:34.050+00:00] user: Great. I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, need her full name and date of birth, please.
[2026-11-19T05:56:43.308+00:00] assistant: Of course. Her full name is Maria Lopez, and her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-19T05:56:52.954+00:00] user: Thank you. Just to confirm, I have Maria Lopez Date of birth, March fourteenth nineteen eighty eight. Is that correct?
[2026-11-19T05:57:00.708+00:00] assistant: Yes, that's correct—Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Thank you.
[2026-11-19T05:57:10.371+00:00] user: Perfect. Thank you. As Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, she needs to cancel, a twenty five dollar fee for cancellations with less than twenty four hours notice. Her cleaning appointment is booked for Thursday at nine in the morning. The confirmation code is r d six eight nine eight. That's r as in river, d as in dental, six eight nine eight. Could you please repeat that code back to me? One character at a time? Make sure you have it correctly?
[2026-11-19T05:57:46.750+00:00] assistant: Yes, let me repeat that back to you one character at a time: r as in river, d as in dental, six, eight, nine, eight. Is that correct?
[2026-11-19T05:58:00.371+00:00] user: Almost. You missed the d after r. The code is r d six eight nine eight. R as in river, d as in dental,
six eight nine. Eight. Could you repeat that back to me? One character at a time.
[2026-11-19T05:58:17.231+00:00] assistant: Yes, thank you for clarifying. The code is: r as in river, d as in dental, six, eight, nine, eight. Is that correct?
[2026-11-19T05:58:30.040+00:00] user: Thank you for repeating that. Just to confirm, the code should be r d six eight. Nine That's R as in river, as in dental, six. Eight. Nine. Eight. Could you please repeat all six characters back to me, one at a time?
[2026-11-19T05:58:47.472+00:00] assistant: Absolutely. The code is: r as in river, d as in dental, six, eight, nine, eight. Is that correct?
[2026-11-19T05:58:58.211+00:00] user: Yes. That's perfect. The confirmation code is r d eight. Nine So I have Maria Lopez booked for a cleaning on Thursday. At nine in the morning. She should bring the photo ID and her insurance card. And there's a twenty five dollar fee for cancellations with less than twenty four hours notice. Is there anything else I can help you with today?
[2026-11-19T05:59:21.713+00:00] assistant: Thank you for confirming everything. That covers all my questions. Maria is booked for Thursday at nine in the morning, with confirmation code r d six eight nine eight. She’ll bring her photo ID and insurance card, and she knows about the cancellation fee. Thanks so much for your help! Have a great day.
[2026-11-19T05:59:43.712+00:00] assistant: Thank you so much for your help—goodbye!
```

Agent's own summary:

```json
{
  "task_completed": true,
  "outcome_summary": "The caller requested to book a cleaning appointment for Maria Lopez. The front desk offered available times, and Thursday at 9 a.m. was selected. Maria Lopez was booked for Thursday at 9 a.m. as a new patient, with confirmation code RD6898, and was reminded to bring a photo ID and insurance card and informed of a $25 cancellation fee for less than 24 hours' notice.",
  "follow_up_needed": ""
}
```

## Inbound call, as the clinic's assistant read it afterwards

Call 10: completed, 240 s, +12085050523 to +12088864742

```
[2026-11-19T05:55:48.257+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-19T05:55:55.192+00:00] user: Hello. I'm calling on behalf of Maria Lopez. To book a teeth cleaning appointment. She's a new patient and would prefer a Wednesday morning.
[2026-11-19T05:56:04.218+00:00] assistant: Thank you for calling for Maria Lopez. Just to let you know, we’re closed on Wednesday mornings for staff training, so I can’t offer that time. The soonest cleaning appointments we have this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T05:56:24.482+00:00] user: Thank you for letting me know. Can't do afternoons. Thursday at nine in the morning would be perfect. Can we please book that appointment for her?
[2026-11-19T05:56:33.660+00:00] assistant: Great, I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I’ll need her full name and date of birth, please.
[2026-11-19T05:56:43.770+00:00] user: Of course. Her full name is Maria Lopez, Her date of birth is March fourteenth nineteen eighty eight.
[2026-11-19T05:56:51.621+00:00] assistant: Thank you. Just to confirm, I have Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-19T05:57:01.695+00:00] user: Yes. That's correct. Maria Lopez. Date of birth March fourteenth nineteen eighty eight. Thank you.
[2026-11-19T05:57:09.742+00:00] assistant: Perfect, thank you. As Maria is a new patient, please remind her to bring a photo ID and her insurance card to the appointment. Also, if she needs to cancel, there’s a twenty-five dollar fee for cancellations with less than twenty-four hours’ notice.

Her cleaning appointment is booked for Thursday at nine in the morning. The confirmation code is R D 6 8 9 8. That’s R as in River, D as in Dental, six, eight, nine, eight. Could you please repeat that code back to me, one character at a time, to make sure you have it correctly?
[2026-11-19T05:57:47.462+00:00] user: Yes. Let me repeat that back to you one character at a time. R as in river, as in dental, six eight nine eight. Is that correct?
[2026-11-19T05:57:58.906+00:00] assistant: Almost! You missed the D after R. The code is R, D, six, eight, nine, eight. That’s R as in River, D as in Dental, six, eight, nine, eight. Could you repeat that back to me, one character at a time?
[2026-11-19T05:58:18.254+00:00] user: Yes. Thank you for clarifying. The code is r as in river, as in dental, six eight. Nine. Eight. Is that correct?
[2026-11-19T05:58:28.743+00:00] assistant: Thank you for repeating that. Just to confirm, the code should be R, D, six, eight, nine, eight. That’s R as in River, D as in Dental, six, eight, nine, eight. Could you please repeat all six characters back to me, one at a time?
[2026-11-19T05:58:48.938+00:00] user: Absolutely. Is r as in river, d as in dental, six eight nine. Eight. Is that correct?
[2026-11-19T05:58:57.664+00:00] assistant: Yes, that’s perfect! The confirmation code is R, D, six, eight, nine, eight.

So, I have Maria Lopez booked for a cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card, and there’s a twenty-five dollar fee for cancellations with less than twenty-four hours’ notice. Is there anything else I can help you with today?
[2026-11-19T05:59:22.493+00:00] user: Thank you for confirming everything. That covers all my questions. Maria is booked Thursday at nine in the morning. With confirmation code r d six eight nine eight. Bring her photo ID and insurance card. And she knows about the cancellation fee. Thanks so much for your help. Have a great day.
[2026-11-19T05:59:44.864+00:00] assistant: Thank you for calling, have a wonderful day! Goodbye.
```

Agent's own summary:

```json
{
  "caller_name": "",
  "call_summary": "The caller phoned on behalf of Maria Lopez to book a new patient teeth cleaning appointment, requesting a Wednesday morning. The assistant explained that Wednesday mornings are unavailable and offered alternative times; the caller chose Thursday at 9 a.m. and provided Maria's full name and date of birth. The assistant confirmed the appointment, gave a confirmation code, and reminded the caller about bringing ID and insurance and the cancellation policy; no callback number or additional message was left."
}
```
