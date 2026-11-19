# Marketplace submission package

Answers for the form at <https://x.ai/bot/marketplace/submit-a-plugin>. The
form lists MCP servers for Grok Bot, Grok, and Cursor. The fields marked
**operator** need the operator's own details.

| Form field | Value |
| --- | --- |
| First Name, Last Name | **operator** |
| Work Email | **operator** |
| Organization Name | **operator** |
| Organization Handle | **operator** (lower case, no spaces) |
| Website URL | `https://PUBLIC_HOST/` |
| Logotype URL | `https://raw.githubusercontent.com/ambrose83646/dograh/main/deploy/platform/marketplace/logo.svg` |
| Where do you want to be listed? | Grok Bot |
| MCP Server URL | `https://PUBLIC_HOST/mcp` |

## Brief Description

> Gives your assistant a phone. It makes calls for you: it books an
> appointment, asks a business a question, or confirms an order, and then
> reports what was said. It also answers calls to your own number with rules
> that you save. Each account gets a phone number and free call minutes.

## Testing Instructions

> 1. Go to https://PUBLIC_HOST/ and sign in with the reviewer account:
>    REVIEWER_EMAIL / REVIEWER_PASSWORD.
> 2. Select "Create an access key" and copy the key.
> 3. Add the MCP server https://PUBLIC_HOST/mcp (Streamable HTTP) with the
>    header `Authorization: Bearer <key>`.
> 4. Ask: "What is my phone number and how many call minutes do I have?"
>    The assistant calls `get_account_status`.
> 5. Ask: "When someone calls my number, answer as the front desk of Riverside
>    Dental. We are open Monday to Friday, 8 to 5." The assistant calls
>    `set_inbound_rules`. Call the account's number from a phone to hear it.
> 6. Ask: "Call REVIEWER_TEST_NUMBER and ask what time they close today."
>    The assistant calls `place_call`, then `get_call_result` until the call
>    ends, and reports the answer with the transcript.
> 7. Ask: "Show my recent calls." The assistant calls `list_calls`.

## Tools

| Tool | Purpose |
| --- | --- |
| `place_call` | Start a call with a task for the voice agent. Returns a call id at once. |
| `get_call_result` | Status, result, and transcript of one call. |
| `list_calls` | Recent inbound and outbound calls. |
| `set_inbound_rules` | Save the greeting and rules for calls to the user's number. |
| `get_inbound_rules` | Read the saved rules. |
| `get_account_status` | Phone number, free minutes left, and limits. |

## Authentication

The server uses a Bearer access key that the user creates on the account
page. It answers HTTP 401 without a valid key. It does not use OAuth.

## Before you submit

- Replace `PUBLIC_HOST` with the production address.
- Create the reviewer account and give it a number from the pool.
- Decide which number reviewers can call. While
  `PLATFORM_DESTINATION_ALLOWLIST` is set, calls go only to the numbers in it.
- Run `platform_verification/verify.py` against production.
- The form asks you to confirm that you tested the plugin in the app. Connect
  the server in Grok Bot and run the steps above first.
