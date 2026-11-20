# Calling platform verification

- Result: **PASS** (10 of 10 checks)
- Service: https://app.danadial.com
- Run: 1120221942 (2026-11-20T22:19:42.713461+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| Maria has a verified phone, and place_call lets her assistant turn the join feature off | PASS | caller ID +12085050523 |
| The agent phones the user's verified number from the service line, and the user joins with key 1 | PASS | calls to the user's phone: [{'from': '+12088972452', 'status': 'completed', 'seconds': 64}] |
| The user and the other party talk directly: each side's words are in the audio of the correct channel | PASS | 13 lines in 62 s: other_party: Hello, Maria. / other_party: This is Dana at card services. / other_party: Please tell me the last four digits of the damaged card. / user: Hello, Dana. / user: This is Maria Lopez. / user: The last four digits are 6827. / other_party: Thank you. / other_party: That is |
| The agent heard the direct talk: its result has the reference and the day, which were said only there | PASS | summary: 'Maria Lopez requested a replacement for her damaged Riverside Bank card. Dana verified Maria’s identity, ordered the replacement, and confirmed it ships Thursday under reference number 5670.' |
| The agent took no part in the direct talk: the words were not spoken to it, and it did not answer them | PASS | agent heard: 'am sorry. I cannot order a card with an assistant. I must speak with Maria Lopez herself. to check her identity. Can you get her on the line? I will hold. Yes. That is all correct. Thank you. Goodbye.' |
| When the user hangs up, the agent continues with the other party and closes the call | PASS | 138 s; agent after the talk: ' i have the reference as five, six, seven, zero. is that correct? dana, are you still there? thank you, dana. maria’s replacement card ships thursday, and the confirmed order reference is five, six, seven, zero. goodbye.' |
| A voicemail box on the user's phone does not join the call; the other party waits less than a minute and the agent returns | PASS | user_not_reached; calls to the user's phone: [{'from': '+12088972452', 'status': 'completed', 'seconds': 45}] |
| After the user did not join, the agent takes the message and the result tells the user what to do | PASS | result: 'False I called Riverside Bank card services to request a replacement for Maria Lopez’s damaged card. Dana said she must speak with Maria to verify her identity; Maria did not answer when I tried to bring her on the line, so no replacement was ordered. Dana ask' |
| After "assistant, leave the call" the agent stops listening: the words that follow are not in the call record | PASS | lines: 'Hello, Dana. / This is Maria Lopez. / Assistant, / leave the call.' |
| The talk continues without the agent, and the call ends when the user hangs up; the agent does not speak again | PASS | direct talk 39 s, call 80 s |

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
