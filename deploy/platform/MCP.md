# DanaDial MCP server

This document describes the MCP server as it is built on November 21, 2026.
It is written from the code and from the live configuration of
`app.danadial.com`. The last section lists what an assistant cannot do today.

## 1. Connection

| Item | Value |
| --- | --- |
| URL | `https://app.danadial.com/mcp` |
| Transport | Streamable HTTP, stateless |
| Authentication | API key: `Authorization: Bearer <key>` or `X-API-Key: <key>` |
| Without a valid key | HTTP 401 before the tool list. There is no OAuth flow. |
| Server name | `phone-calls` |
| Tools | 8 |

One API key belongs to one account. One account belongs to one phone number.

## 2. Onboarding as it works today

Steps 1 to 3 are done by the user on a web page. Steps 4 to 7 are done by the
assistant.

| # | Who | Step | Where |
| --- | --- | --- | --- |
| 1 | User | Gives a phone number and gets a 6-digit code by text message | Sign-in page |
| 2 | User | Enters the code. The first sign-in creates the account. | Sign-in page |
| 3 | User | Creates an API key and copies the key and the MCP URL into the assistant | Account page |
| 4 | Assistant | Calls `get_account_status`. `caller_id` is empty. | MCP |
| 5 | Assistant | Asks for a phone number that the user owns, calls `start_caller_id_verification`, and tells the user the code | MCP |
| 6 | User | Answers the phone and enters the code on the keypad | Phone |
| 7 | Assistant | Calls `get_account_status` to confirm, then `place_call` | MCP |

What the service creates at step 2, with no action from the user:

- A separate Twilio subaccount for the account.
- An outbound agent and an inbound agent.
- 10 free call minutes. They do not renew.

Rules of the sign-in:

- United States and Canada numbers only.
- One phone number is one account. Only the operator can release a number.
- The code is valid for 10 minutes and permits 5 guesses.
- One code each minute, 6 codes each day for a number, 20 codes each hour for
  a network address.

Rules of the caller ID check (steps 5 and 6):

- A new account cannot call before this check. `place_call` is refused with
  the instruction to use `start_caller_id_verification`.
- 3 checks in 24 hours for each account.
- The check stays open for 3 minutes.
- A number that is the sign-in phone or the caller ID of a different account
  is refused.

## 3. Instructions that the server gives to the assistant

The server sends this text when the assistant connects:

- The server is a phone. The assistant can call a number, read what was said,
  and set how calls to the user's number are answered.
- The user manages everything through the assistant. The assistant must not
  send the user to a web page for a setting.
- Before the first call, do the caller ID check.
- To call: `place_call`, then `get_call_result` after about 30 seconds, and
  again until the status is `completed` or `failed`.
- Write the task as a brief for a human assistant. The voice agent knows only
  the `task` and the `background`.
- Call only numbers that the user asked for. No sales, survey, or bulk calls.
- How minutes, the monthly plan, and automatic minute packs work.
- The voice agent gives its name, "Dana Dial", at the start of each call, and
  says that it is an AI assistant. If your `voicemail_message` does not have
  the name, the service says "This is Dana Dial, an AI assistant." before it.

## 4. Tools

### 4.1 `get_account_status`

Reads the account. It also completes a caller ID check that is open.

No parameters. Fields of the result:

| Field | Meaning |
| --- | --- |
| `caller_id` | The verified number of the user, or empty |
| `caller_id_status` | `verified`, or text that says what to do |
| `outbound_calls_from` | The number that outbound calls show |
| `phone_number` | The number for inbound calls, or empty |
| `phone_number_status` | `ready`, or text that says that the operator adds a number on request |
| `plan`, `plan_period_end` | The monthly plan. Empty during the free minutes. |
| `minutes_total`, `minutes_used`, `minutes_remaining` | Call minutes |
| `minutes_note` | Text for the user when less than 20% of the minutes remain |
| `automatic_packs` | `limit` and `added_this_period` |
| `calls_in_last_24_hours`, `daily_call_limit` | The limit is 20 |
| `max_call_minutes` | 10 |
| `can_call` | True when a call is possible now |
| `blocked_reason` | Text for the user when a call is not possible |
| `voice`, `voice_options` | `eve`, `ara`, `leo`, `rex`, `sal` |

### 4.2 `start_caller_id_verification`

Starts a call to the user's phone with a code.

| Parameter | Required | Meaning |
| --- | --- | --- |
| `phone_number` | Yes | A phone that the user owns and can answer now, as `+14155550123` |

Result: `status` (`calling`), `phone_number`, `validation_code`, `next_step`.

### 4.3 `place_call`

Starts an outbound call. It returns at once with a `call_id`.

| Parameter | Required | Limit | Meaning |
| --- | --- | --- | --- |
| `phone_number` | Yes | | The number to call, as `+14155550123` |
| `task` | Yes | 4000 characters | The full brief for the voice agent |
| `background` | No | 6000 characters | Facts that the agent can give if a person asks |
| `on_behalf_of` | No | 120 characters | The name of the person that the agent calls for |
| `call_reason` | No | 200 characters | Spoken to a call screener and at the start of a voicemail message |
| `voicemail_message` | No | 600 characters | The exact words for a voicemail box. If it is empty, the service writes a message. |
| `allow_user_to_join` | No | Default: true | The agent can phone the user and connect the user to the call |

Result: `call_id`, `status` (`ringing`), `to`, `from`, `minutes_remaining`,
`max_minutes_this_call`, `minutes_note`, `next_step`.

What the service does when the call is answered:

| What answers | What the agent does |
| --- | --- |
| A person | Does the task |
| A voicemail box | Leaves the message and ends the call |
| A call screener | Gives the name and the reason, then waits for the person |
| A phone menu | Presses the keys to get to the correct department |
| A hold recording | Waits |

Direct talk between the user and the other party:

- The agent phones the user's verified number from the service line. The user
  presses 1 to join.
- The agent does not speak during the talk. It listens and writes down the
  words.
- "Assistant, leave the call" makes the agent stop listening.
- When the user hangs up, the agent continues the call with the other party.
- When the other party hangs up, the user's phone is released at once.
- The time counts as call minutes.
- For "get Steve on the line for me", the tool description tells the
  assistant to write a task with one question only.

Reasons for a refusal:

- The number is not a valid United States or Canada number, or it is a
  premium-rate number.
- The account has no caller ID.
- The number is the account's own number.
- The minutes are used, or the limit of 20 calls in 24 hours is reached. The
  message says what the user must do, with the address of the billing page.

### 4.4 `get_call_result`

Reads one call, during the call or after it.

| Parameter | Required | Meaning |
| --- | --- | --- |
| `call_id` | Yes | From `place_call` or `list_calls` |

| Field | Meaning |
| --- | --- |
| `status` | `ringing`, `in_progress`, `completed`, `failed` |
| `direction` | `outbound` or `inbound` |
| `started_at`, `duration_seconds` | During a call, the duration is the time so far |
| `to`, `from`, `task` | |
| `disposition`, `error` | How the call ended |
| `answered_by` | `person`, `voicemail`, `call_screener`, `phone_menu`, `hold_line`, `unknown` |
| `voicemail_message_left` | Only with `voicemail` |
| `keys_pressed` | Keys that the agent pressed in a menu |
| `result` | The agent's summary |
| `transcript` | The record of the words. During a call, the words so far. |
| `direct_talk` | For each talk: `result`, `user_joined`, `seconds`, `lines` |
| `direct_talk_now` | Present while the user is on the line |
| `transcript_deleted` | `true` when the words were deleted (30 days after the call). `transcript` is then empty and `direct_talk` has no `lines`. |
| `next_step` | What the assistant must do next |

In `transcript`, `assistant:` is the voice agent and `user:` is the person on
the phone. Lines that start with `direct talk,` are from the user (`your
user`) or the other party (`other person`).

### 4.5 `list_calls`

Lists recent calls, outbound and inbound, newest first.

| Parameter | Required | Meaning |
| --- | --- | --- |
| `limit` | No | Default 10, maximum 50 |

Each item has the summary fields of `get_call_result`, without the
transcript.

### 4.6 `set_inbound_rules`

Saves how calls to the user's number are answered. It replaces the earlier
rules. The rules apply when no assistant is connected.

| Parameter | Required | Limit | Meaning |
| --- | --- | --- | --- |
| `rules` | Yes | 6000 characters | Instructions in plain language |
| `answer_as` | No | 120 characters | Whose phone this is |
| `greeting` | No | 300 characters | The exact first sentence |

### 4.7 `get_inbound_rules`

Reads the saved rules: `phone_number`, `rules`, `answer_as`, `greeting`,
`is_default`.

The default rules: answer politely, say that the owner is not available, and
take a message with the name, the reason, and a number to call back.

### 4.8 `update_settings`

Changes the voice. With no parameters, it reads the settings.

| Parameter | Required | Meaning |
| --- | --- | --- |
| `voice` | No | `eve`, `ara`, `leo`, `rex`, or `sal` |

The voice applies to the next call, outbound and inbound.

## 5. Limits on the live service

| Limit | Value |
| --- | --- |
| Free minutes for a new account | 10, one time |
| Longest call | 10 minutes |
| Calls in 24 hours | 20 |
| Countries | United States and Canada |
| Caller ID checks in 24 hours | 3 |
| Sign-in codes each day for a number | 6 |
| Sign-up | Open |

## 6. Minutes and billing

- An account starts with free minutes. After them, the user needs the monthly
  plan.
- When fewer than 5 minutes remain on a plan, the service asks the billing
  system for a paid pack of minutes, up to the limit that the user set.
- When the minutes are used, the account cannot make calls and does not
  answer calls.
- The billing page is `https://danadial.com/dashboard/billing`. The MCP
  server has no billing tool. It gives the assistant the text and the page
  address to give to the user.

## 7. What the assistant cannot do today

These are the steps that need a web page or the operator.

| Step | Today | Effect |
| --- | --- | --- |
| Sign up | Web page: phone number and text code | The assistant cannot create the account |
| Get access | Web page: create a key, copy the key and the URL | Manual copy and paste. No OAuth, so "add connector, approve" is not possible. |
| Prove the phone | Two times: text code at sign-in, then a call with a code for the caller ID | The user proves the same phone two times |
| Start the monthly plan | Billing page | The assistant can give only the address |
| Set the limit of minute packs | Billing page | Same |
| Get a number for inbound calls | The operator adds it on request | No tool. A new account has no inbound number. |
| Stop a call in progress | Not built | The assistant can read a live call but cannot end it |
| Learn that a call ended or came in | The assistant must ask again (poll) | No notification |
| Change or remove the caller ID | A new check with a different number. Removal is not built. | Not tested as a user flow |
| Manage API keys | Web page | The assistant cannot revoke a key |
| Close the account | Operator only | No tool |

One conflict in the text: the server instructions say that the assistant must
not send the user to a web page for a setting. The billing steps and the key
need a web page.

## Changes on branch `platform-calling` that are not on the live server

These need the owner's approval before a deploy.

| Change | Meaning |
| --- | --- |
| OAuth sign-in | A plugin host signs in with OAuth. The API key continues to work. |
| `get_account_status` → `setup` | `state` (`verify_phone`, `waiting_for_code`, `ready`, `blocked`), `done`, and `next_step`. The assistant follows `next_step` while `done` is false. |
| `end_call` (new) | Parameter `call_id`. Hangs up a call that rings or is in progress. The record keeps the words said before the end and shows `ended_by: "assistant"`. |
| `get_billing_link` (new) | No parameters. Gives `url` (the billing page), `sign_in` (how the user signs in), `plan`, and `minutes_remaining`. |
| Instructions | The first step is `get_account_status`. The only web page for the user is the billing page. |
| Outbound only | Version 1 has no inbound calls. The server does not show `set_inbound_rules`, `get_inbound_rules`, `phone_number`, or `phone_number_status`, and no text speaks of inbound calls. `PLATFORM_INBOUND_TOOLS=true` shows them again; `platform_verification/verify.py` needs that value. |

Check: `platform_verification/assistant_setup.py` (results in
`platform_verification/results/assistant_setup/`).
