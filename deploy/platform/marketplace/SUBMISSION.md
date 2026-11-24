# Marketplace submission package

Answers for the form at <https://x.ai/bot/marketplace/submit-a-plugin>. The
owner sends the form.

| Form field | Value |
| --- | --- |
| First Name, Last Name | Adam, Stewart |
| Work Email | `info@danadial.com` |
| Organization Name | DanaDial |
| Organization Handle | `danadial` |
| Website URL | `https://danadial.com` |
| Logotype URL | `https://raw.githubusercontent.com/ambrose83646/dograh/c6ab645390d99c402751106c48e53516f88d7ab7/deploy/platform/marketplace/logo.svg` |
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

The form field takes fewer than 600 characters. This text has 552.

> No test account is necessary. You need a US or Canada phone that you can answer.
> 1. Add the plugin and select "Allow". There is no password.
> 2. Ask: "Set up DanaDial." Give your phone number. The Bot tells you a 6-digit code.
> 3. Your phone rings. Answer and enter the code on the keypad.
> 4. Ask: "Call <a US business number> and ask what time they close today." The Bot reports the answer with the transcript.
> 5. Ask: "Show my recent calls."
> Limits: 10 free minutes, 10 minutes for each call. The voice agent says that it is Dana Dial, an AI assistant.

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

## Authentication

OAuth 2.1 with dynamic client registration and PKCE. The server accepts the
three return addresses that Grok Bot registers. Consent is one "Allow"
button. The consent makes the account. The phone check in steps 2 and 3 joins
the person to an account that has that phone already.

## Logo

`logo.svg` in this directory: the DanaDial dial on a square dark plate, 1:1.
The address in the table is the raw GitHub address of that file.

## Before the owner submits

- The form has a box: "I've tested this plugin locally and in-app". Add
  `https://app.danadial.com/mcp` in Grok Bot as a custom connector (apps
  icon → custom connector → Remote HTTPS) and do steps 1 to 5.
- `https://danadial.com/terms` and `https://danadial.com/privacy` are
  published. Get a legal review of the two texts if you have not done so.
- Version 1 is for outbound calls only. The server shows no inbound tools
  (`PLATFORM_INBOUND_TOOLS` is off).
- After the listing, put the plugin link `https://x.ai/bot/plugin/<plugin-id>`
  on the "Add to Grok Bot" button of the site.
