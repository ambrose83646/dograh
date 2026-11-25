# Design: sign-up through the assistant, with OAuth

Status: proposal, November 21, 2026. Nothing in this document is built.

## 1. Goal

A person installs the DanaDial plugin in GrokBot. The assistant does all of
the onboarding. The person does one thing: answers the phone and enters a
code on the keypad.

## 2. What GrokBot needs

Sources: the xAI submission form, the xAI documentation for Grok Bot, and a
guide that follows the Grok Bot changelog and the staff answers on the
forum. I did not test a connector in GrokBot for this document.

| Fact | Effect on the design |
| --- | --- |
| A plugin signs in with OAuth only. Staff say that there is no safe way to enter a secret header. | The API key method cannot be the plugin method. |
| The user selects "Authorize". GrokBot opens a page of the service, then keeps the tokens on its own servers. | Our server must be an OAuth authorization server. The assistant never sees a token. |
| GrokBot registers itself as a client, and its callback is `cursor://anysphere.cursor-mcp/oauth/callback`. Services that accept only `https` callbacks fail. | Our server must accept client registration and this callback. |
| The OAuth discovery comes from GrokBot's servers, not from the user's computer. | Limits for each network address do not work for plugin users. |
| The review takes 3 to 5 weeks or more. Each update is reviewed again. | The tools must be correct before the submission. |
| The reviewer needs a way to sign in that works for months. | The design needs a reviewer path (section 8). |

## 3. Two options for the Authorize page

OAuth always opens one page of ours. The question is what the person does on
that page.

### Option A: consent only (recommended)

The page has the terms and one button: "Allow". There is no form. The
service creates an account that has no phone number yet. The assistant then
asks for the phone number in the chat and starts the phone check. That one
check proves the phone, makes it the caller ID, and binds the account to the
phone.

### Option B: phone number and text code on the page

The page asks for the phone number and a text code, as the sign-in page does
today. The assistant then does the caller ID check as today.

### Comparison

| | Option A | Option B |
| --- | --- | --- |
| Steps for the person | Select "Allow". Answer the phone and enter the code. | Type the phone number. Read a text. Type the code. Answer the phone and enter a second code. |
| Proofs of the phone | 1 | 2 |
| Who asks for the phone number | The assistant, in the chat | A web form |
| Text message cost for each sign-up | None | One text |
| New code | More: an account without a phone, and the bind step | Less: the sign-in code is used again |
| Risk of abuse | Higher: an account exists before a phone is proved. Section 7 gives the controls. | Lower |

The phone call with a code cannot be removed in either option. Twilio
requires its own call before a number can be shown as the caller ID. For
that reason the text code in option B adds a step and removes none.

## 4. Onboarding with option A

| # | Who | Step |
| --- | --- | --- |
| 1 | Person | Installs the plugin and selects "Authorize" |
| 2 | Person | Reads the terms on the DanaDial page and selects "Allow" |
| 3 | Assistant | Calls `get_account_status`. The result says: no phone, ask the user for the number. |
| 4 | Assistant | Asks for the phone number in the chat and calls `start_caller_id_verification` |
| 5 | Assistant | Tells the person the code |
| 6 | Person | Answers the phone and enters the code on the keypad |
| 7 | Assistant | Calls `get_account_status`. The phone is verified. The 10 free minutes start. |
| 8 | Assistant | Makes the first call |

Step 2 stays with the person on purpose. The person must accept the terms:
the service makes calls in the person's name and writes down what is said.
An assistant cannot give that consent.

## 5. What step 6 does on the server

When Twilio confirms the code:

1. If no account has this phone: the phone becomes the sign-in phone and
   the caller ID of the new account. The free minutes start.
2. If an account has this phone already: the new authorization is moved to
   that account, and the empty account is deleted. This is the path for a
   person who installs the plugin a second time, or who signed up on the web
   before.

The second case is as safe as the text code today. In both, the person
proves that they hold the phone.

Before step 6, an account can do one thing: start the phone check. It has no
minutes, no Twilio subaccount, and cannot call.

## 6. Changes to the server

### 6.1 OAuth

- Authorization server on `app.danadial.com`: discovery documents, client
  registration, authorization code with PKCE, access tokens of one hour, and
  refresh tokens that change with each use.
- Accept the GrokBot callback (`cursor://...`), `https` callbacks, and
  loopback callbacks. The last two are for Grok, Cursor, Claude, and ChatGPT.
- A request with no token gets HTTP 401 with the address of the discovery
  document.
- The MCP library in use (FastMCP 4) has the base parts for this. Its default
  rules reject app callbacks such as `cursor://`, so that rule needs our own
  setting.
- API keys continue to work for the accounts that have them.

### 6.2 Tools and text

| Change | Reason |
| --- | --- |
| `get_account_status` gets a `setup` part: the state and the next step | The assistant follows it and does not guess |
| `start_caller_id_verification` also binds the account to the phone | One proof |
| Server instructions: new first-run steps. Remove "do not send the user to a web page" for billing. | The text is wrong today |
| `end_call` (new) | The assistant can read a live call but cannot stop it |
| `get_billing_link` (new): a link that signs the person in to the billing page | Payment needs the person. The link removes the second sign-in. |
| `request_inbound_number` (new) | Today only the operator can add a number. This needs a decision: section 9. |

### 6.3 Web

- A new Authorize page: terms, "Allow", and a link for a review code.
- The sign-in page with a text code stays for the billing dashboard on
  `danadial.com`. The accounts are the same, because the phone is the
  account.

## 7. Abuse controls for option A

The risk: a script authorizes many times and makes the service call phones
that did not ask for it. Each call costs money.

| Control | Value (proposal) |
| --- | --- |
| Human check on the "Allow" button (Cloudflare Turnstile) | Always |
| Phone checks for one account | 3 in 24 hours (as today) |
| Phone checks to one phone number, from all accounts | 3 in 24 hours |
| Phone checks for the full service | A limit for each hour, with an alert to the operator |
| Twilio subaccount | Made only when the phone check passes |
| Account with no phone | Deleted after 7 days |
| Free minutes | Start only when the phone is verified. One phone, one account, as today. |

## 8. Reviewer path

A reviewer can use the same path as a person, with their own United States
or Canada phone. Two additions make the review possible without that:

- **Review code:** a link on the Authorize page takes a code and signs the
  reviewer in to a prepared account with a caller ID and minutes.
- **Demo line:** a DanaDial number that an agent answers as a small
  business. The reviewer can ask the assistant to call it. No real business
  gets a test call.

## 9. Decisions that I need from you

1. Option A or option B.
2. Inbound numbers: each number costs money each month. Who gets one: each
   account, accounts on the paid plan only, or on request as today?
3. The terms and privacy pages for the Authorize page. Do they exist on
   `danadial.com`?

## 10. Order of work

| # | Work | Why in this order |
| --- | --- | --- |
| 1 | OAuth server in the sandbox, then connect a real GrokBot to it as a custom connector | The callback is the largest technical risk. Test it first. |
| 2 | Account without a phone, the bind step, and the abuse controls | The core of option A |
| 3 | `setup` in `get_account_status`, new instructions | The assistant can then lead the onboarding |
| 4 | `end_call`, `get_billing_link`, and the inbound decision | Before the submission, because each update is reviewed again |
| 5 | Review code and demo line | For the reviewer |
| 6 | Full check with real calls in the sandbox, then production | As for each release |
| 7 | New submission text, then the submission after your approval | |

## 11. What I did not confirm

- That GrokBot accepts our OAuth server. Step 1 of the work tests this.
- If a plugin in the catalog uses the same callback as a custom connector.
- The review rules of xAI for a service that makes phone calls.
