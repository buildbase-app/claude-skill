# Diagnostics — What the Docs Let You Conclude

**Honest scope:** the self-hosted docs (overview, quick-start, configuration, production) do **not** include a troubleshooting / failure guide. This file contains only diagnostics that follow **directly** from documented behavior. Everything else is marked as a gap — don't fabricate symptom→cause→fix entries that aren't grounded.

> **Source:** the four `docs/content/self-hosted/*.mdx` files. Where a conclusion is a direct reading of a documented fact, it's used; where it isn't, it's listed under "Not documented."

---

## Grounded diagnostics

### `/api/ready` does not return `{"ready": true}`
- **Documented meaning:** `/api/ready` returns `{"ready": true}` **"when DB and Redis are connected."** So a non-ready response means the tenant server is **not connected to MongoDB and/or Redis.**
- **Check:** `docker compose -f docker-compose.selfhost.yml ps` (are mongodb/redis healthy?), then `GET /api/health` for **DB status, Redis latency, worker status** (documented fields).
- **Config to verify:** `MONGO_CONNECTION_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` ([../config/env-reference.md](../config/env-reference.md)). In the quick-start compose these point at the bundled `mongodb`/`redis` services; in production Mongo is external via `env_file`.

### Browser CORS errors calling the tenant server
- **Documented control:** `CORS_WHITELISTED_DOMAINS` is a "comma-separated list of allowed origins," and "platform origins (`console.buildbase.app`) are always allowed by default." The quick-start compose sets it to `${CLIENT_URL},${AUTH_URL}`.
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
