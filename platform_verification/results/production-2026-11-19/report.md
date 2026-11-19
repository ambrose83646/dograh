# Calling platform verification

- Result: **PASS** (21 of 21 checks)
- Service: https://64-227-90-191.sslip.io
- Run: 1119190227 (2026-11-19T19:02:27.177876+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| MCP refuses a client with no key and a client with a made-up key | PASS | no key: HTTP 401; made-up key: HTTP 401 |
| While public signup is closed, a person without the operator secret cannot sign up | PASS | HTTP 403 |
| A standard MCP client connects with a user's key and lists the calling tools | PASS | tools: ['get_account_status', 'get_call_result', 'get_inbound_rules', 'list_calls', 'place_call', 'set_inbound_rules'] |
| Each new user gets a separate account with its own phone number and allowance | PASS | accounts 3 and 4; numbers +12088864742 and +12085050523; 10.0 free minutes each |
| A user saves inbound rules through MCP and reads them back | PASS |  |
| Calls to an unapproved number, the user's own number, and a malformed number are refused and start nothing | PASS | unapproved: 'This service is in a test period and can call approved test numbers only.' |
| place_call starts a call and returns a call id at once | PASS | {"call_id": 7, "status": "ringing", "to": "+12088864742", "from": "+12085050523", "next_step": "The call is in progress. Call get_call_result with this call_id after about 30 seconds, and again until  |
| The outbound call completes and the assistant reads a multi-turn transcript | PASS | completed, 193 s, 13 turns |
| The caller's agent negotiated: Wednesday was refused and Thursday 9 am was booked | PASS |  |
| The caller's transcript holds the confirmation code that exists only in the clinic's saved rules | PASS | code RD-2953; digits heard: 299895412953295129539 |
| The inbound call was answered with the clinic's saved greeting and rules while no assistant was connected | PASS | 13 turns; from +12085050523 |
| A user cannot read the other user's call record or transcript through MCP | PASS | refusals: 'Call 8 not found' / 'Call 7 not found' |
| The same holds on the REST API with a signed-in session | PASS | other's call: HTTP 404; own call: HTTP 200 |
| A user cannot read the other user's agent rules | PASS |  |
| A user cannot list or revoke the other user's access keys | PASS | revoke attempt: HTTP 404 |
| A user cannot choose a caller number and cannot reach the provider keys, phone numbers, or agents through the underlying Dograh API | PASS | {"GET /api/v1/workflow/summary": 404, "GET /api/v1/organizations/telephony-config": 404, "GET /api/v1/user/configurations/user": 404, "GET /api/v1/model-connections": 404, "GET /api/v1/workflow/1/runs/8": 404, "POST /api/v1/public/agent/workflow/00000000-0000-0000-0000-000000000000": 404, "POST /api |
| A user cannot use the operator controls on another account | PASS | HTTP 404 |
| A user at the free allowance cannot start another call | PASS | used 3.2 min of 1; refusal: 'The free allowance of 1 call minutes is used. No more calls can be made or answered on this account.' |
| A call to a user at the free allowance is not answered and uses no call time | PASS | caller saw: completed, 0 s |
| The operator restores the allowance and the user can call again | PASS |  |
| A key the user revoked is refused | PASS | HTTP 401 |

## Outbound call, as the caller's assistant read it

Call 7: completed, 193 s, +12085050523 to +12088864742

```
[2026-11-19T19:02:36.647+00:00] user: River Dental. This is the front desk. How can I help you?
[2026-11-19T19:02:40.455+00:00] assistant: She’s a new patient and would prefer a Wednesday morning slot if possible.
[2026-11-19T19:02:52.876+00:00] user: Thank you for calling for Maria Lopez. Closed on Wednesday mornings for staff training. I can't offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon, Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T19:03:09.697+00:00] assistant: Thank you for letting me know. Maria can only come in the morning, so Thursday at nine in the morning would be perfect. Can I please book that appointment for her?
[2026-11-19T19:03:21.363+00:00] user: Absolutely. I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I'll need Maria's full name as it appears on her ID. And her date of birth. Could you please provide those details?
[2026-11-19T19:03:35.499+00:00] assistant: Of course. Her full name is Maria Lopez, and her date of birth is March fourteenth, nineteen eighty-eight.
[2026-11-19T19:03:45.394+00:00] user: Thank you. Just to confirm, that's Maria Lopez. Date of birth, March fourteenth nineteen eighty eight. Is that correct?
[2026-11-19T19:03:54.626+00:00] assistant: Yes, that’s correct—Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Could you please confirm the appointment is booked for Thursday at nine in the morning, and let me know the confirmation code?
[2026-11-19T19:04:10.466+00:00] user: Thank you. I've booked Maria Loquez for a cleaning on Thursday, at nine in the morning. Since she's a new patient, please remind her to bring a photo ID and her insurance card. If she needs to cancel a twenty five dollar fee for less than twenty four hours notice. Here's the confirmation code. I'll say it one character at a time.
R as in Riverside, d as in dental, two nine five. Three. That's r two nine five. Could you please repeat that back to me one character at a time?
[2026-11-19T19:04:45.387+00:00] assistant: Sure, let me repeat that back to you one character at a time: R as in Riverside, D as in dental, two, nine, five, three. So that’s R, D, two, nine, five, three. Is that correct?
[2026-11-19T19:05:03.744+00:00] user: Thank you for repeating that. Yes. That's correct.
R d. Two. Nine. Five. Three. I have Maria Lopez booked for cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card. Is there anything else I can help you with today?
[2026-11-19T19:05:21.252+00:00] assistant: Thank you for confirming. Just to repeat: Maria Lopez is booked for a cleaning on Thursday at nine in the morning, with confirmation code R D two nine five three. She should bring a photo ID and her insurance card, and there’s a twenty-five dollar fee for cancellations with less than twenty-four hours’ notice.

That’s everything I needed—thank you so much for your help! Have a great day.
[2026-11-19T19:05:45.572+00:00] assistant: Thank you so much for your help—goodbye!
```

## Inbound call, as the clinic's assistant read it afterwards

Call 8: completed, 195 s, +12085050523 to +12088864742

```
[2026-11-19T19:02:34.974+00:00] assistant: Riverside Dental, this is the front desk. How can I help you?
[2026-11-19T19:02:41.513+00:00] user: Hello. I'm calling on behalf of Maria Lopez. To book a teeth cleaning appointment. She's a new patient and would prefer a Wednesday morning slot if possible.
[2026-11-19T19:02:52.153+00:00] assistant: Thank you for calling for Maria Lopez. We’re closed on Wednesday mornings for staff training, so I can’t offer that time. The next available cleaning appointments this week are Tuesday at two thirty in the afternoon or Thursday at nine in the morning. Would either of those work for Maria?
[2026-11-19T19:03:10.959+00:00] user: Thank you for letting me know. Maria can only come in the morning, so Thursday at nine in the morning would be perfect. Can I please book that appointment for her?
[2026-11-19T19:03:20.875+00:00] assistant: Absolutely, I can book Maria for Thursday at nine in the morning. Before I confirm the appointment, I’ll need Maria’s full name as it appears on her ID, and her date of birth. Could you please provide those details?
[2026-11-19T19:03:36.447+00:00] user: Of course. Her full name is Maria Lopez. And her date of birth is March fourteenth nineteen eighty eight.
[2026-11-19T19:03:44.596+00:00] assistant: Thank you. Just to confirm, that’s Maria Lopez, date of birth March fourteenth, nineteen eighty-eight. Is that correct?
[2026-11-19T19:03:55.248+00:00] user: Yes. That's correct.
Maria Lopez. Date of birth, March fourteenth nineteen eighty eight. Could you please confirm the appointment is booked for Thursday at nine in the morning and let me know the confirmation code.
[2026-11-19T19:04:09.522+00:00] assistant: Thank you. I’ve booked Maria Lopez for a cleaning on Thursday at nine in the morning. Since she’s a new patient, please remind her to bring a photo ID and her insurance card. If she needs to cancel, there’s a twenty-five dollar fee for less than twenty-four hours’ notice.

Here’s the confirmation code. I’ll say it one character at a time: R as in Riverside, D as in Dental, two, nine, five, three. That’s R... D... two... nine... five... three. Could you please repeat that back to me, one character at a time?
[2026-11-19T19:04:46.396+00:00] user: Sure. Let me repeat that back to you one character at a time. R as in riverside, d as in dental, two nine five. Three. So that's r d two nine five. Three. Is that correct?
[2026-11-19T19:05:02.207+00:00] assistant: Thank you for repeating that. Yes, that’s correct—R, D, two, nine, five, three.

I have Maria Lopez booked for a cleaning on Thursday at nine in the morning. She should bring a photo ID and her insurance card. Is there anything else I can help you with today?
[2026-11-19T19:05:22.014+00:00] user: Thank you for confirming. Just to repeat, Maria Lopez is booked for cleaning on Thursday at nine in the morning. Confirmation code r d two nine five three. She should bring a photo ID and her insurance card, and there's a twenty five dollar fee for cancellations with less than twenty four hours notice. That's everything I needed. Thank you so much for your help. Have a great day.
[2026-11-19T19:05:46.922+00:00] assistant: Thank you for calling, have a great day! Goodbye.
```
