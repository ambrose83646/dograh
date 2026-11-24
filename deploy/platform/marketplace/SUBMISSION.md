# Marketplace submission package

Answers for the form at <https://x.ai/bot/marketplace/submit-a-plugin>. The
owner sends the form. The fields marked **owner** need the owner's details.

| Form field | Value |
| --- | --- |
| First Name, Last Name | **owner** |
| Work Email | **owner** |
| Organization Name | DanaDial |
| Organization Handle | `danadial` |
| Website URL | `https://danadial.com` |
| Logotype URL | See "Logo" below |
| Where do you want to be listed? | Grok Bot |
| MCP Server URL | `https://app.danadial.com/mcp` |

## Brief Description

> DanaDial gives your Bot a phone. Ask it to book an appointment, ask a
> business a question, or confirm an order. It makes the call, speaks for
> you, and reports what was said with the transcript. Calls show your own
> phone number, which you confirm with one short call. It can also bring you
> into a call when a person asks for you. No account form and no key: select
> Add, and your Bot does the setup. 10 free call minutes. US and Canada
> numbers.

## Testing Instructions

> No test account is necessary. The plugin makes the account at sign-in.
> You need a US or Canada phone that you can answer.
>
> 1. Add the plugin. A DanaDial page opens. Select "Allow". There is no
>    password and no form.
> 2. Ask: "Set up DanaDial." The Bot calls `get_account_status` and asks for
>    your phone number. Give it. The Bot calls
>    `start_caller_id_verification` and tells you a 6-digit code.
> 3. Your phone rings. Answer and enter the code on the keypad. Tell the Bot
>    that you did. It confirms that calls now show your number, and that you
>    have 10 free call minutes.
> 4. Ask: "Call <a US business number> and ask what time they close today."
>    The Bot calls `place_call`, then `get_call_result` until the call ends,
>    and reports the answer with the transcript.
> 5. During a longer call, ask: "End that call." The Bot calls `end_call`.
>    The phone call stops in a few seconds.
> 6. Ask: "Show my recent calls." The Bot calls `list_calls`.
> 7. Ask: "How do I get more minutes?" The Bot calls `get_billing_link` and
>    gives the billing page. The plan is optional and is sold on
>    danadial.com.
>
> Limits: 10 minutes for each call, 20 calls each day. The service refuses
> emergency and premium-rate numbers. The voice agent says that it is an AI
> assistant if a person asks.

## Tools

| Tool | Purpose |
| --- | --- |
| `get_account_status` | Setup state with the next step, caller ID, minutes, limits. |
| `start_caller_id_verification` | Call the user's own phone with a code, so that calls show that number. |
| `place_call` | Start a call with a task for the voice agent. Returns a call id at once. |
| `get_call_result` | Status, result, and transcript of one call. |
| `end_call` | Hang up a call that rings or is in progress. |
| `list_calls` | Recent calls. |
| `update_settings` | Change the voice of the agent. |
| `get_billing_link` | The page where the user starts or changes the monthly plan. |
| `set_inbound_rules`, `get_inbound_rules` | Rules for calls to the user's inbound number, when the account has one. |

## Authentication

OAuth 2.1 with dynamic client registration and PKCE. The server accepts the
three return addresses that Grok Bot registers. Consent is one "Allow"
button. The consent makes the account. The phone check in step 2 and 3 joins
the person to an account that has that phone already.

## Logo

`logo.svg` in this directory: the DanaDial dial on a square dark plate, 1:1.
Use the raw GitHub address of the file at the commit that contains it.

## Before the owner submits

- The form has a box: "I've tested this plugin locally and in-app". Add
  `https://app.danadial.com/mcp` in Grok Bot as a custom connector (apps
  icon → custom connector → Remote HTTPS) and do steps 1 to 7.
- `https://danadial.com/terms` and `/privacy` show "not in service". Publish
  the two pages before the submission. The Publisher Terms and the reviewers
  expect them.
- An inbound number is added by the operator on request. Decide if the
  listing mentions inbound calls. The text above does not.
- After the listing, put the plugin link `https://x.ai/bot/plugin/<plugin-id>`
  on the "Add to Grok Bot" button of the site.
