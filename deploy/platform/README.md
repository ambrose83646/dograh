# Deploy the calling service (platform mode)

This stack runs the shared calling service on one server: Postgres, Redis,
MinIO, the API, and Caddy for HTTPS. Users sign up on the account page at `/`
and connect an AI assistant to the MCP server at `/mcp`.

## What you need

- A server with Ubuntu 24.04, 2 vCPU, 4 GB memory, and ports 80 and 443 open.
- Docker with the Compose plugin (`curl -fsSL https://get.docker.com | sh`).
- A Twilio account, an OpenAI key, and a Deepgram key. The operator pays for
  these. An xAI key is optional: with it, the agent speaks with a Grok voice.
- No phone number for each user. Each new account gets its own Twilio
  subaccount, which is free, and the user verifies a phone they own as their
  caller ID. A user needs a Twilio number only to receive calls. The operator
  assigns that number from a pool (see "Numbers for inbound calls").

## Steps

```bash
git clone --recurse-submodules https://github.com/ambrose83646/dograh.git
cd dograh/deploy/platform
./setup.sh                 # or: ./setup.sh calls.example.com
```

`setup.sh` writes `.env` with random secrets. With no argument it uses
`<server-ip>.sslip.io`, a free name that points at the server, so HTTPS works
before you have a domain. Add the provider values to `.env`:

```
PLATFORM_TWILIO_ACCOUNT_SID=
PLATFORM_TWILIO_AUTH_TOKEN=
PLATFORM_OPENAI_API_KEY=
PLATFORM_DEEPGRAM_API_KEY=
PLATFORM_XAI_API_KEY=                       # optional, for Grok voices
PLATFORM_TWILIO_NUMBER_POOL=+15550100       # optional, numbers for inbound calls
```

The Twilio values must be those of the main account. Subaccounts are made from
it and their usage is billed to it.

Then start the stack and check it:

```bash
./setup.sh && docker compose up -d --build
curl -s https://$(grep ^PUBLIC_HOST= .env | cut -d= -f2)/api/v1/health
```

The first build takes about 10 minutes.

## Settings

| Variable | Default | Effect |
| --- | --- | --- |
| `ENABLE_SIGNUP` | `false` | `true` opens registration to the public. |
| `ENABLE_CALL_RECORDING_UPLOAD` | `false` | `true` stores the audio of each call. The agent gives no recording notice, so check the consent law first. |
| `PLATFORM_FREE_SECONDS` | `600` | Free call time for each new account. It does not renew. After it, the account needs a monthly plan. |
| `PLATFORM_SMS_FROM` | empty | Sender of the sign-in codes: a phone number of the main Twilio account, or a Messaging Service SID (`MG…`). It must be registered for text messages (A2P 10DLC). Do not use a number from the pool. Empty: phone sign-in is off. |
| `PLATFORM_OTP_DAILY_PER_NUMBER` | `6` | Sign-in codes that one phone number can get in 24 hours. |
| `PLATFORM_OTP_HOURLY_PER_ADDRESS` | `20` | Sign-in codes that one client address can request in one hour. |
| `PLATFORM_BILLING_URL` | empty | Page where a user chooses a monthly plan. The agent gets this address when the minutes are used. |
| `PLATFORM_MAX_CALL_SECONDS` | `600` | Longest single call. |
| `PLATFORM_DAILY_CALL_LIMIT` | `20` | Calls for each account in 24 hours. |
| `PLATFORM_ALLOWED_PREFIXES` | `+1` | Number prefixes that users can call. |
| `PLATFORM_LLM_MODEL` | `gpt-4.1` | OpenAI model that holds the conversation. Tested: `gpt-4.1` and `gpt-6-sol`. `gpt-6-luna` ends calls too early. An account gets a new value on its next use. |
| `PLATFORM_STT_MODEL` | `flux-general-multi` | Deepgram speech recognition model. |
| `PLATFORM_TTS_VOICE` | `eve` | Grok voice: `eve`, `ara`, `leo`, `rex`, or `sal`. Used when `PLATFORM_XAI_API_KEY` is set. |
| `PLATFORM_CALLER_ID_DAILY_ATTEMPTS` | `3` | Caller ID checks for each account in 24 hours. Each check is a phone call. |
| `PLATFORM_DESTINATION_ALLOWLIST` | empty | When set, users can call only these numbers and the pool. A caller ID check is a call, so the same list applies. Use it for a test period. |

After a change to `.env`, run `docker compose up -d`.

## While signup is closed

The operator can create an account with the operator secret:

```bash
curl -X POST https://HOST/api/v1/auth/signup \
  -H "X-Operator-Token: $PLATFORM_OPERATOR_TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"a-long-password","name":"User"}'
```

## Numbers for inbound calls

A user receives calls only after the operator assigns a number. The number
moves from the main Twilio account into the user's subaccount:

```bash
H="X-Operator-Token: $PLATFORM_OPERATOR_TOKEN"
curl -X POST -H "$H" https://HOST/api/v1/platform/operator/accounts/ORG_ID/assign-number
curl -X POST -H "$H" https://HOST/api/v1/platform/operator/accounts/ORG_ID/release-number
```

`release-number` moves the number back to the pool. To stop an account, use
`.../suspended` with `{"suspended": true}`. To end it for good, use
`.../close`: Twilio cannot reopen a closed subaccount.

## Change the domain

Point the new name at the server, then:

```bash
./setup.sh calls.example.com && docker compose up -d
```

New accounts use the new address at once. For each account that already has a
number, the Twilio webhook keeps the old address until the number is released
and assigned again, so change the domain before you open signup.

## Verify

`platform_verification/README.md` describes the end-to-end run. It makes real
calls between two new accounts and closes both accounts at the end.

## Backups

All state is in the `postgres_data` and `minio_data` volumes:

```bash
docker compose exec -T postgres pg_dump -U postgres postgres | gzip > backup.sql.gz
```
