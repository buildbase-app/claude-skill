# Diagnostics - What the Docs Let You Conclude

**Honest scope:** the self-hosted docs (overview, quick-start, configuration, production) have no troubleshooting page. They do now document the licensing states, the health-check answers, the update procedure and many variables' failure modes, and the compose files carry comments that explain each guard. This file holds only diagnostics that follow **directly** from those. Everything else is marked as a gap - don't fabricate symptom -> cause -> fix entries that aren't grounded.

> **Source:** the four `docs/content/self-hosted/*.mdx` files and the compose comments in them; one entry quotes the platform's server source and says so.

---

## Contents

- [Start-up](#start-up)
- [Readiness and health](#readiness-and-health)
- [Console and licensing](#console-and-licensing)
- [Frontends and CORS](#frontends-and-cors)
- [Production behind Nginx](#production-behind-nginx)
- [Features that need a variable](#features-that-need-a-variable)
- [Not documented - do NOT invent answers for these](#not-documented---do-not-invent-answers-for-these)

---

## Start-up

### `docker compose up` aborts before any container starts

- **Symptom:** lines such as `required variable REDIS_PASSWORD is missing a value: REDIS_PASSWORD is required`, followed by a pointer to the generate-secrets command, and nothing runs.
- **Cause:** both compose files interpolate five secrets as `${VAR:?message}`, which Compose treats as fatal when the variable is unset or empty: `JWT_PASS`, `DB_ENCRYPTION_KEY`, `SECRET_KEY`, `OAUTH2_SECRET` and `REDIS_PASSWORD`.
- **Fix:** generate them and put them in `.env.selfhost`. The docs' command also prints `BULLMQ_DASHBOARD_PASSWORD`, which is optional but worth setting:

  ```bash
  for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD BULLMQ_DASHBOARD_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
  ```

  Also pass `--env-file .env.selfhost`; without it Compose sees none of them. If only `REDIS_PASSWORD` is named, you are probably working from an older copy of the published quick start, which printed only four secrets and had no line for the fifth.

### `tenant-server` exits at start and names an installation variable

- **Documented:** with no `INSTALLATION_ID` or `INSTALLATION_API_KEY`, the tenant server does not start, and says which variable is missing. The composes pass both as `${VAR:-}`, so Compose does not catch it.
- **Fix:** copy both values from Account, then Installations in the console (regenerate the key there if it was lost; it is shown once).
- **From the server source, not the docs** (`server/src/self-hosted-edition.ts` in the platform repo): the self-hosted image also refuses to start with `INTERNAL_API_KEY` set (the cloud tenant's credential) or `ORG_IDS` set. Remove them.

### `tenant-server` restarts repeatedly, exit code 137

- **Symptom:** the container is OOM-killed under load.
- **Cause:** the image's default Node heap is sized for larger hosts and exceeds the 1024M container limit.
- **Fix:** keep `NODE_OPTIONS=--max-old-space-size=768` on `tenant-server`. Both composes set it; do not strip it when adapting the file.

### Redis is killed instead of refusing writes

- **Cause, per the compose comment:** Redis needs memory beyond its data (allocator overhead, fragmentation, the AOF rewrite's fork), and a Redis that reaches its container limit is killed.
- **Fix:** the composes run `--maxmemory 150mb` under a 256M limit. To give Redis more, raise both numbers together.

### Bundled MongoDB crash-loops on restart, or the first `up` says "container mongodb is unhealthy"

- **Cause:** an install made before release 23 has a compose whose `mongodb` service lacks `CHOWN`: the healthcheck runs `mongosh` as root, leaving root-owned files the entrypoint cannot hand back, so every restart after the first crash-loops. Older composes also had a 5 s probe timeout that `mongosh`'s cold start could exceed on a first boot while mongod was fine.
- **Fix (documented):** save the current quick-start compose over yours and run `up -d`; it recovers with the data intact. See [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

### Port already in use on launch

- **Documented knobs:** host ports come from `CLIENT_PORT` (4100), `TENANT_SERVER_PORT` (4101), `AUTH_PORT` (4103); the containers listen on 3000 internally (Nginx on 8080 in production). Change the `*_PORT` value in `.env.selfhost` if a host port is taken.

---

## Readiness and health

### `/api/ready` does not return `{"ready":true,...}`

- **Documented meaning:** `200` with `{"ready": true, "mongo": "ok", "redis": "ready"}` when MongoDB and Redis are connected; `503` with `"ready": false` and the state of each connection when one is down. The body says which one.
- **Check:** `docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost ps` (are `mongodb` and `redis` healthy?), then `GET /api/health` with `x-internal-api-key: <INSTALLATION_API_KEY>` for the full report (database and Redis state, Redis latency, tenant connections and pool sizes, memory, uptime). Without the header it answers only `{"status", "timestamp"}`.
- **Config to verify:** `MONGO_CONNECTION_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` ([../config/env-reference.md](../config/env-reference.md)). In the quick-start compose these point at the bundled `mongodb` and `redis` services; in production Mongo is external via `env_file`.

### Production `/api/ready` never becomes true

- **Cause:** the production compose bundles no MongoDB, and `MONGO_CONNECTION_URL` is missing from `.env.selfhost`, so the server falls back to `localhost` inside its own container.
- **Fix:** set `MONGO_CONNECTION_URL` to your external Mongo. The template ships an Atlas-style SRV example.

### Every replica goes unready at once

- **Documented cause:** every replica shares one Redis, so a Redis outage fails every replica's probe at the same moment.
- **Option:** `READINESS_REDIS_FAIL_OPEN=true` keeps the probe answering ready (`"redis": "degraded"`), and the routes that need Redis answer `503` on their own. Off by default.

### Running jobs are cut off on every restart or update

- **Cause:** the workers run in the tenant-server process, and Compose's default stop is 10 s.
- **Fix:** keep `stop_grace_period: 180s` on `tenant-server`, and in production the `autoheal.stop.timeout=180` label, which stops autoheal restarting a shutting-down container with Docker's 10 s stop. Both are in the current composes.

---

## Console and licensing

### The installation shows as disconnected

- **Documented:** a wrong or regenerated key leaves end users unaffected, but the server cannot check in or read its organizations from BuildBase. It logs `[CentralAPI] central refused ...` once, and once more when accepted again.
- **Fix:** put the current key in `.env.selfhost` and restart. After **Regenerate**, the old key keeps working for up to 60 minutes.
- A newly started server shows **Connected** within a few minutes; it checks in every five.

### The console will not open an organization

Three documented causes, none of which affects your end users:

- **Minimum version:** the installation reports an older image, or none. Pull the newer image (after taking its compose file) and restart; the console names the version.
- **Self-hosting plan lapsed:** the refusal says to renew.
- **Detached organization:** a self-hosted organization on no installation runs nowhere. **Reattach** it from Account, then Installations (Detached organizations).

### Console sign-in waits while BuildBase is unreachable

- **Documented:** existing sessions keep working; signing in again waits for BuildBase. End users' sign-in, sessions and the app keep working throughout.

### "Test connection" in the setup wizard

- **Documented step:** create the organization on the installation, enter your **server URL**, click **Test connection**, then **Complete setup**. Locally `http://localhost:4101`; in production your public `TENANT_SERVER_URL`.
- **"Not checked from this browser"** on a local or private address means the dashboard page may not be allowed to reach it. Complete setup anyway if the server is running.
- BuildBase never connects to a private address itself, so the features where its servers call yours need a public HTTPS URL.

### The hosted sign-in page refuses password sign-up, or invitations fail with 503

- **Documented cause:** the organization has no email sender. Sign-up codes, password resets and invitations go through it (Messaging, then Sender accounts). Invitations refuse with 503 `NO_SENDER_CONFIGURED` before anything is written (workspaces invitations page). Also check that a sign-in method exists and is enabled on your app ([../deploy/quick-start.md](../deploy/quick-start.md) Step 7).

---

## Frontends and CORS

### The dashboard calls a literal `__NEXT_PUBLIC_SERVER_URL__`

- **Symptom:** the client or auth portal loads but its requests go to the string `__NEXT_PUBLIC_SERVER_URL__` instead of your server, and nothing authenticates.
- **Cause:** `read_only: true` was set on the `client` or `auth` service. Their entrypoints rewrite the `__NEXT_PUBLIC_*__` placeholders inside the built JS at container start, and on a read-only filesystem that rewrite fails silently.
- **Fix:** remove `read_only` from `client` and `auth`. Keep it on `tenant-server`, `redis` and `nginx`, where the docs set it.

### CORS errors from the client or auth portal in production only

- **Symptom:** the quick start worked; production blocks the frontends.
- **Cause:** the server reads `SERVER_URL`, `APPLICATION_URL` and `AUTH_SERVER_URL`, while `.env.selfhost` provides `TENANT_SERVER_URL`, `CLIENT_URL` and `AUTH_URL`. The production compose maps between them explicitly with no fallback; drop the mapping and the server uses localhost URLs.
- **Fix:** keep the mapping block on `tenant-server`, and keep `CORS_WHITELISTED_DOMAINS=${CLIENT_URL},${AUTH_URL}`.

### A browser app gets CORS errors calling the tenant server

- **Documented rule:** `/api/v1/*`, `/.well-known/*` and `/org/*` answer any origin, so an app's SDK calls never need its origin in `CORS_WHITELISTED_DOMAINS`. The list governs the rest of `/api` (the organization API), which a browser should not call at all: an API key belongs on a server.
- **Action:** if the failing path is under `/api/v1`, the cause is elsewhere (the wrong `serverUrl`, a proxy stripping headers, or an error answer read as CORS). If it is an organization-API path, move the call to the app's server rather than widening the list.

---

## Production behind Nginx

### Rate-limited (HTTP 429)

- **Documented behaviour:** `nginx-lb.conf` answers `429` past its zones: `api_general` 30 r/s on `/`; `api_auth` 5 r/s on `^/api/(auth|oauth|login|register|password)` and on `/api/v1/auth`; `api_sdk_session` 20 r/s per address and session plus `api_sdk_ip` 200 r/s per address on `/api/v1/`. `/ready` and `/health` are never limited. Adjust `nginx-lb.conf` deliberately if needed.

### Everyone is rate-limited together, or one ban takes the whole install offline

- **Cause, per the production compose comment:** without `TRUST_PROXY=1` behind the bundled Nginx, every caller is Nginx's address: one shared bucket for every per-IP rate limit, and a probe-shield ban takes the whole install offline.
- **Fix:** keep `TRUST_PROXY=${TRUST_PROXY:-1}` in production, and raise it by one for each further appending proxy (a load balancer, Cloudflare). Never set it higher than the real count: callers could then pick their own address.

### WebSocket connections drop with two replicas

- **Cause, per the Nginx comment:** socket.io opens with polling and upgrades to a WebSocket, and the upgrade has to reach the replica that holds the session.
- **Fix:** keep `hash $remote_addr consistent;` in the `upstream` block. Older copies of `nginx-lb.conf` lacked it; take the current one.

### Nginx exits at once

- **Cause, per the compose comment:** with every capability dropped, a root Nginx master can neither write its tmpfs nor switch its workers to the nginx user.
- **Fix:** keep `user: '101:101'`, `listen 8080` and `pid /tmp/nginx.pid` together; older copies listened on 80 with `NET_BIND_SERVICE`. Take the current compose and `nginx-lb.conf` as a pair.

### HTTP 413 / large request rejected

- **Documented limit:** `client_max_body_size 500M` and `large_client_header_buffers 4 8k` in `nginx-lb.conf`.

---

## Features that need a variable

| Symptom | Documented cause |
|---|---|
| Every password takes about 2 seconds to be accepted | `BREACHED_PASSWORD_CHECK` is on and the server cannot reach `api.pwnedpasswords.com`. Set it `off` |
| Uploads stop at 5 MB; form file fields and SDK uploads answer 501 | `GOOGLE_STORAGE_STAGING_BUCKET_NAME` is unset |
| The staging bucket's finalize webhook answers 404 | `GOOGLE_STORAGE_FINALIZE_TOKEN` is unset (uploads still complete) |
| Owner data exports answer 503 | `EXPORTS_BUCKET` is unset |
| File items answer `FILES_NOT_SET_UP` | `GOOGLE_STORAGE_DELIVERABLES_BUCKET_NAME` is unset |
| The server warns about the job dashboard at every boot | `BULLMQ_DASHBOARD_PASSWORD` is unset and falls back to `INSTALLATION_API_KEY` |
| Saving an email sender is refused | Its mail server rejected the login (`SENDER_VERIFY_ON_SAVE`). Only when the server cannot reach the mail host at all, set it `false` |
| Bandwidth is never measured | `GOOGLE_STORAGE_USAGE_LOG_BUCKET` unset, or `GOOGLE_STORAGE_USAGE_LOG_PREFIX` does not match the bucket's log prefix |

Each variable is in [../config/env-reference.md](../config/env-reference.md).

---

## Not documented - do NOT invent answers for these

The self-hosted docs do not cover:
- What happens if **`DB_ENCRYPTION_KEY`** (or `JWT_PASS`, `OAUTH2_SECRET`, `SECRET_KEY`) is rotated or lost.
- **Restore** procedures and their failure modes (the docs document only `mongodump` before an update - see [../operations/upgrades-backups.md](../operations/upgrades-backups.md)).
- Going back to an older image after its successor ran migrations.
- The exact outbound host and port the check-in uses (only a diagram label names `central.console.buildbase.app`).
- Log formats beyond the lines quoted above, replica-flapping causes, MongoDB and Redis sizing for load, scaling past two replicas.
- How the host-level `certbot --nginx` and the compose's own Nginx are meant to fit together.

If asked about any of these, say it isn't in the current self-hosted docs and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview) or suggest raising it with Buildbase.

---

## Read next

- Config reference -> [../config/env-reference.md](../config/env-reference.md)
- Updating, migrations and backups -> [../operations/upgrades-backups.md](../operations/upgrades-backups.md)
- Architecture and connections -> [../architecture/four-components.md](../architecture/four-components.md)
