# Calling platform verification

- Result: **PASS** (15 of 15 checks)
- Service: http://localhost:8000
- Run: 1121024250 (2026-11-21T02:42:50.088933+00:00)

| Check | Result | Detail |
| --- | --- | --- |
| Maria has a verified phone, and place_call lets her assistant turn the join feature off | PASS | caller ID +12085050523 |
| The agent phones the user's verified number from the service line, and the user joins with key 1 | PASS | calls to the user's phone: [{'from': '+12088864742', 'status': 'completed', 'seconds': 64}] |
| The user and the other party talk directly: each side's words are in the audio of the correct channel | PASS | 13 lines in 62 s: other_party: Hello, Maria. / other_party: This is Dana at card services. / other_party: Please tell me the last four digits of the damaged card. / user: Hello, Dana. / user: This is Maria Lopez. / user: The last four digits are 9537. / other_party: Thank you. / other_party: That is |
| The agent heard the direct talk: its result has the reference and the day, which were said only there | PASS | summary: 'Maria Lopez requested a replacement for her damaged Riverside Bank card. Dana verified Maria’s identity and confirmed that the new card ships Tuesday; the order reference is 5119.' |
| The agent took no part in the direct talk: the words were not spoken to it, and it did not answer them | PASS | agent heard: 'am sorry. I cannot order a card with an assistant. I must speak with Maria Lopez herself. To check her identity, can you get her on the line? I will hold. Yes. That is all correct. Thank you. Goodbye.' |
| The transcript is one record: the words of the direct talk are in it at the correct place, each with the correct speaker | PASS | speakers in order: ['user', 'assistant', 'user', 'assistant', 'talk:other person', 'talk:other person', 'talk:other person', 'talk:your user', 'talk:your user', 'talk:your user', 'talk:other person', 'talk:other person', 'talk:other person', 'talk:other person', 'talk:your user', 'talk:your user', ' |
| When the user hangs up, the agent continues with the other party and closes the call | PASS | 137 s; agent after the talk: 'nd i heard the order reference as five, one, one, nine. is that correct? dana, are you still there? thank you, dana. the replacement card ships tuesday, and the confirmed order reference is five, one, one, nine. goodbye.' |
| A voicemail box on the user's phone does not join the call; the other party waits less than a minute and the agent returns | PASS | user_not_reached; calls to the user's phone: [{'from': '+12088864742', 'status': 'completed', 'seconds': 44}] |
| After the user did not join, the agent takes the message and the result tells the user what to do | PASS | result: 'False I called Riverside Bank card services to request a replacement for Maria Lopez’s damaged card. Dana said she must speak directly with Maria to verify her identity; Maria did not answer, so no replacement was ordered. Dana asked Maria to call card service' |
| After "assistant, leave the call" the agent stops listening: the words that follow are not in the call record | PASS | lines: 'Hello, Dana. / This is Maria Lopez. / Assistant, / leave the call.' |
| The talk continues without the agent, and the call ends when the user hangs up; the agent does not speak again | PASS | direct talk 39 s, call 79 s |
| During the call, the call result shows the running time and the words so far | PASS | 25 reports; seconds [13, 28, 44] ... [362, 377] |
| During the direct talk, the call result shows that the user is on the line, and the words of the talk so far | PASS | 23 reports with the user on the line; last at 340 s |
| A direct talk of more than five minutes is not cut: the words that the other party says after minute five are in the record | PASS | direct talk 342 s; last words: 'ile. This is step eight. To check is done, The password of the day is strawberry. Goodbye.' |
| When the other party hangs up, the user's phone is released at once, and the result says that the call ended | PASS | result call_ended; user's phone call [345] s, direct talk 342 s |

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
