# Calling platform verification

- Result: **PASS** (6 of 6 checks)
- Service: http://localhost:8000
- Run: None (2026-11-20T23:22:21.466585+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| An exempt number keeps the one-minute wait between codes | PASS | first 200; at once: (429, 'A code was sent a moment ago. Wait one minute.') |
| A number that is not exempt gets two codes, then the day limit stops it | PASS | codes: 200, 200; third: (429, 'Too many codes were requested. Try again later.') |
| The exempt number gets a third code on the same day | PASS | second 200, third (200, '') |
| The reset does nothing without the operator token | PASS | no token 404, wrong token 404, next request (429, 'A code was sent a moment ago. Wait one minute.') |
| After the operator reset, the number gets a code at once: the day count and the wait are both clear | PASS | reset 200 {"phone_number":"+12085050523","reset":true}; next request (200, '') |
| The reset keeps the code that the phone has, and the phone stays connected to its account and its access key | PASS | sign-in 200; account before 500031, after 500031; key 200 |

## Outbound call, as the caller's assistant read it

Call None: None, None s, None to None

```
(no transcript)
```

## Inbound call, as the clinic's assistant read it afterwards

Call None: None, None s, None to None

```
(no transcript)
```

## Call answered by a voicemail box

Call None: None, None s, None to None

```
(no transcript)
```

## Call answered by a call screener, then a person

Call None: None, None s, None to None

```
(no transcript)
```

## Call answered by a phone menu that takes keys only

Call None: None, None s, None to None

```
(no transcript)
```
