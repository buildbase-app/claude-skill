# Diagnostics — What the Docs Let You Conclude

**Honest scope:** the self-hosted docs (overview, quick-start, configuration, production) do **not** include a troubleshooting / failure guide. This file contains only diagnostics that follow **directly** from documented behavior. Everything else is marked as a gap — don't fabricate symptom→cause→fix entries that aren't grounded.

> **Source:** the four `docs/content/self-hosted/*.mdx` files. Where a conclusion is a direct reading of a documented fact, it's used; where it isn't, it's listed under "Not documented."

---

## Grounded diagnostics

### `docker compose up` aborts before any container starts

- **Symptom:** a message naming a variable, for example `REDIS_PASSWORD is required - run the generate-secrets command from the quick start`, and nothing runs.
- **Cause:** both compose files interpolate their secrets as `${VAR:?message}`, which Compose treats as fatal when the variable is unset or empty. The five required values are `JWT_PASS`, `DB_ENCRYPTION_KEY`, `SECRET_KEY`, `OAUTH2_SECRET` and `REDIS_PASSWORD`.
- **Fix:** generate all five and put them in `.env.selfhost`:

  ```bash
  for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
  ```

  Also pass `--env-file .env.selfhost`; without it Compose sees none of them. If the message names `REDIS_PASSWORD` specifically, you are probably working from an older copy of the published quick start, which printed only four secrets and had no line for the fifth.

### The dashboard calls a literal `__NEXT_PUBLIC_SERVER_URL__`

- **Symptom:** the client or auth portal loads but its requests go to the string `__NEXT_PUBLIC_SERVER_URL__` instead of your server, and nothing authenticates.
- **Cause:** `read_only: true` was set on the `client` or `auth` service. Their entrypoints rewrite the `__NEXT_PUBLIC_*__` placeholders inside the built JS at container start, and on a read-only filesystem that rewrite fails silently.
- **Fix:** remove `read_only` from `client` and `auth`. Keep it on `tenant-server`, `redis` and `nginx`, where the docs set it.

### `tenant-server` restarts repeatedly, exit code 137

- **Symptom:** the container is OOM-killed under load.
- **Cause:** the image's default Node heap is sized for larger hosts and exceeds the 1024M container limit.
- **Fix:** keep `NODE_OPTIONS=--max-old-space-size=768` on `tenant-server`. The quick-start compose sets it; do not strip it when adapting the file.

### Production `/api/ready` never becomes true

- **Symptom:** the stack is up but readiness never passes.
- **Cause:** the production compose bundles no MongoDB, and `MONGO_CONNECTION_URL` is missing from `.env.selfhost`, so the server falls back to `localhost` inside its own container.
- **Fix:** set `MONGO_CONNECTION_URL` to your external Mongo. The template ships an Atlas-style SRV example.

### CORS errors from the app or auth portal in production only

- **Symptom:** the quick start worked; production blocks the frontends.
- **Cause:** the server reads `SERVER_URL`, `APPLICATION_URL` and `AUTH_SERVER_URL`, while `.env.selfhost` provides `TENANT_SERVER_URL`, `CLIENT_URL` and `AUTH_URL`. The production compose maps between them explicitly with no fallback; drop the mapping and the server uses localhost URLs.
- **Fix:** keep the mapping block on `tenant-server`, and keep `CORS_WHITELISTED_DOMAINS=${CLIENT_URL},${AUTH_URL}`.

### `/api/ready` does not return `{"ready": true}`
- **Documented meaning:** `/api/ready` returns `{"ready": true}` **"when DB and Redis are connected."** So a non-ready response means the tenant server is **not connected to MongoDB and/or Redis.**
- **Check:** `docker compose -f docker-compose.selfhost.yml ps` (are mongodb/redis healthy?), then `GET /api/health` for **DB status, Redis latency, worker status** (documented fields).
- **Observed, not documented:** a non-ready response is HTTP 503 and its JSON names which of `db` / `redis` is disconnected. Useful for diagnosis; label it as observed rather than quoting it as documented behaviour.
- **Config to verify:** `MONGO_CONNECTION_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` ([../config/env-reference.md](../config/env-reference.md)). In the quick-start compose these point at the bundled `mongodb`/`redis` services; in production Mongo is external via `env_file`.

### Browser CORS errors calling the tenant server
- **Documented control:** `CORS_WHITELISTED_DOMAINS` is a "comma-separated list of allowed origins," and "platform origins (`console.buildbase.app`) are always allowed by default." Both compose files set it to `${CLIENT_URL},${AUTH_URL}`.
- **Action:** ensure your app's origin is included in `CORS_WHITELISTED_DOMAINS`.

### "Test Connection" in the setup wizard
- **Documented step:** you enter your **server URL** and click **Test Connection** → **Complete Setup**. For local testing the docs use `http://localhost:4101`; in production you enter your public `TENANT_SERVER_URL` (e.g. `https://api.yourcompany.com`).
- **Implication:** the URL you enter must be the address that actually reaches your tenant server.

### Port already in use on launch
- **Documented knobs:** host ports come from `CLIENT_PORT` (4100), `TENANT_SERVER_PORT` (4101), `AUTH_PORT` (4103); containers always listen on 3000 internally. Change the `*_PORT` value in `.env.selfhost` if a host port is taken.

### Rate-limited (HTTP 429) in production
- **Documented behavior:** `nginx-lb.conf` sets `rate=30r/s` general and `rate=5r/s` on `^/api/(auth|oauth|login|register|password)`, returning `429`. This is expected protection; adjust `nginx-lb.conf` deliberately if needed.

### HTTP 413 / large request rejected
- **Documented limit:** `client_max_body_size 500M` and `large_client_header_buffers 4 8k` in `nginx-lb.conf`.

---

## Connectivity note (grounded in the architecture diagram)

The architecture diagram shows the tenant server makes **HMAC-signed API** calls to the central server and the client does **org auth (JWT)** against it. So the stack needs **outbound access to the central server**. If that connectivity is blocked, those documented interactions can't happen. *(The docs don't enumerate the resulting error states — see below.)*

---

## ⚠️ Not documented — do NOT invent answers for these

The self-hosted docs do not cover:
- Specific error messages or states for a **wrong/expired `INSTALLATION_API_KEY`** or failed licensing/activation.
- What happens if **`DB_ENCRYPTION_KEY`** (or other secrets) is rotated or lost.
- **Backup/restore** failure modes (no backup procedure exists in the docs — see [../operations/upgrades-backups.md](../operations/upgrades-backups.md)).
- Behavior when the **central server is unreachable** (timeouts, retries, offline grace).
- Log locations / formats, replica-flapping causes, MongoDB sizing.

If asked about any of these, say it isn't in the current self-hosted docs and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview) or suggest raising it with Buildbase. **These are exactly the gaps to fill in the docs.**

---

## Read next

- Config reference → [../config/env-reference.md](../config/env-reference.md)
- Updating + backup gap → [../operations/upgrades-backups.md](../operations/upgrades-backups.md)
- Architecture/connections → [../architecture/four-components.md](../architecture/four-components.md)
