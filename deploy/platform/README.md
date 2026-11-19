# Deploy the calling service (platform mode)

This stack runs the shared calling service on one server: Postgres, Redis,
MinIO, the API, and Caddy for HTTPS. Users sign up on the account page at `/`
and connect an AI assistant to the MCP server at `/mcp`.

## What you need

- A server with Ubuntu 24.04, 2 vCPU, 4 GB memory, and ports 80 and 443 open.
- Docker with the Compose plugin (`curl -fsSL https://get.docker.com | sh`).
- A Twilio account, an OpenAI key, and a Deepgram key. The operator pays for
  these.
- One Twilio phone number for each user that you expect. Each account keeps
  one number. When the pool is empty, a new account gets no number.

## Steps

```bash
git clone https://github.com/ambrose83646/dograh.git && cd dograh/deploy/platform
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
PLATFORM_TWILIO_NUMBER_POOL=+15550100,+15550101
```

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
| `PLATFORM_FREE_SECONDS` | `600` | Free call time for each account. |
| `PLATFORM_MAX_CALL_SECONDS` | `600` | Longest single call. |
| `PLATFORM_DAILY_CALL_LIMIT` | `20` | Calls for each account in 24 hours. |
| `PLATFORM_ALLOWED_PREFIXES` | `+1` | Number prefixes that users can call. |
| `PLATFORM_DESTINATION_ALLOWLIST` | empty | When set, users can call only these numbers and the pool. Use it for a test period. |

After a change to `.env`, run `docker compose up -d`.

## While signup is closed

The operator can create an account with the operator secret:

```bash
curl -X POST https://HOST/api/v1/auth/signup \
  -H "X-Operator-Token: $PLATFORM_OPERATOR_TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"a-long-password","name":"User"}'
```

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
calls between two new accounts and releases their numbers at the end.

## Backups

All state is in the `postgres_data` and `minio_data` volumes:

```bash
docker compose exec -T postgres pg_dump -U postgres postgres | gzip > backup.sql.gz
```
