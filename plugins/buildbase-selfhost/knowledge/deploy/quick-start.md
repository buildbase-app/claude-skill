# Quick Start - From Zero to a Running Stack

The documented path to a running self-hosted stack. Everything is bundled - **MongoDB, Redis, tenant server, client app and auth portal** in one Docker Compose file. The checks map to the docs' own verify step.

> **Source:** `docs/content/self-hosted/quick-start.mdx` -> [docs.buildbase.app/self-hosted/quick-start](https://docs.buildbase.app/self-hosted/quick-start). The `.env.selfhost`, the generate-secrets command and `docker-compose.selfhost.yml` below are the generated output of `packages/shared/src/constants/self-hosted.ts` and are reproduced byte-for-byte, em dashes in the compose error messages included. Re-sync them whenever the docs change; see MAINTENANCE.md.
>
> Rather clone than copy? The docs point at the [self-hosted starter](https://github.com/buildbase-app/self-hosted-starter), which is this same stack as a repo.

---

## Contents

- [Prerequisites](#prerequisites)
- [Step 1 - Create an Installation](#step-1---create-an-installation)
- [Step 2 - Create the environment file](#step-2---create-the-environment-file)
- [Step 3 - Save the Docker Compose file](#step-3---save-the-docker-compose-file)
- [Step 4 - Start the stack](#step-4---start-the-stack)
- [Step 5 - Verify](#step-5---verify)
- [Step 6 - Connect](#step-6---connect)
- [Step 7 - Let people sign in](#step-7---let-people-sign-in)
- [What's next](#whats-next)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-started/get-docker/) and Docker Compose v2.
- A BuildBase account at **[console.buildbase.app](https://console.buildbase.app)**, with self-hosting enabled. A new account offers **Shared cloud** only; if **Self-hosted** is not among the hosting options when you create an organization, contact support to have self-hosting enabled for the account.
- An `amd64` or `arm64` host. The images are multi-arch and run natively on both, Apple Silicon included.

Self-hosting is licensed per installation, and how many installations you can run (and how many organizations each holds) depends on the self-hosting plan on your own account: [../mental-models/installations.md](../mental-models/installations.md). Full requirements table (Ubuntu 20.04+, 2 GB RAM, 2 vCPU, MongoDB 7+, Redis 7+) is in [../architecture/four-components.md](../architecture/four-components.md).

---

## Step 1 - Create an Installation

1. Log in to **[console.buildbase.app](https://console.buildbase.app)**.
2. Open **Account**, then **Installations**, and click **Create installation**. (Choosing **Self-hosted** while creating an organization takes you to the same page.)
3. Copy the **Installation API Key** and **Installation ID**. The key is shown once; if you lose it, regenerate it on the same page.

The organization itself comes later, in Step 6, once the server is running: it is created on an installation that has checked in.

Check: you have both values. Concept: [../mental-models/installations.md](../mental-models/installations.md).

---

## Step 2 - Create the environment file

Save as `.env.selfhost`:

```bash
# ═══════════════════════════════════════════════════════════════════
# Self-Hosted — Production Environment
# ═══════════════════════════════════════════════════════════════════

# ── Installation (from BuildBase dashboard) ──────────────────────
INSTALLATION_API_KEY=<INSTALLATION_API_KEY>
INSTALLATION_ID=<INSTALLATION_ID>

# ── Database (REQUIRED for production) ───────────────────────────
# The production compose uses an external MongoDB (Atlas or
# self-managed). Without this, the server falls back to localhost
# inside the container and never becomes ready.
# The quick-start compose bundles MongoDB and ignores this value.
MONGO_CONNECTION_URL=mongodb+srv://user:password@your-cluster.mongodb.net/

# ── Public URLs ──────────────────────────────────────────────────
# For local testing use http://localhost:4100, :4101, :4103
CLIENT_URL=https://app.yourcompany.com
TENANT_SERVER_URL=https://api.yourcompany.com
AUTH_URL=https://auth.yourcompany.com

# ── Ports ────────────────────────────────────────────────────────
CLIENT_PORT=4100
TENANT_SERVER_PORT=4101
AUTH_PORT=4103

# ── Security (REQUIRED — run: openssl rand -hex 32) ──────────────
JWT_PASS=
DB_ENCRYPTION_KEY=
SECRET_KEY=
OAUTH2_SECRET=
# Redis auth. Both compose files require this and both start Redis with
# --requirepass, so it must match on the server and the container.
REDIS_PASSWORD=

# ── Optional services ────────────────────────────────────────────
# GOOGLE_AUTH_CLIENT_ID=
# GOOGLE_AUTH_CLIENT_SECRET=
# GOOGLE_STORAGE_ASSETS_BUCKET_NAME=
# Direct uploads: up to 100 MB, form file fields and SDK uploads. Unset keeps
# every upload on the 5 MB server route, and those two answer 501.
# GOOGLE_STORAGE_STAGING_BUCKET_NAME=
# GOOGLE_STORAGE_FINALIZE_TOKEN=     # optional: finalize notifications
# GOOGLE_STORAGE_USAGE_LOG_BUCKET=   # optional: measures bandwidth
# GOOGLE_STORAGE_USAGE_LOG_PREFIX=assets
# EXPORTS_BUCKET=                    # owner data exports; unset, they are off
# TENANT_STORAGE_GATE=               # default: follows TENANT_FEATURE_GATE (off)
# TENANT_STORAGE_BILLING=off         # no effect self-hosted: storage is not billed
# TENANT_STORAGE_INTEGRITY=shadow    # default: shadow - weekly report, no changes
# TENANT_STORAGE_PURGE=off           # no effect self-hosted: never lapses
# GOOGLE_WEB_RISK_API_KEY=
# URL_SAFETY_ENABLED=true            # default: true
# URL_SAFETY_LOG_ONLY=false          # default: false - a malicious destination
#                                    # is refused as soon as the key is set
# URL_SAFETY_CLEAN_TTL_SECONDS=3600
# WEB_RISK_TIMEOUT_MS=5000
# BREACHED_PASSWORD_CHECK=on         # default: on; off when the server cannot
#                                    # reach api.pwnedpasswords.com
# TURNSTILE_SITE_KEY=                # bot protection on your auth domain;
# TURNSTILE_SECRET_KEY=              # unset leaves it to each org's own keys
# SMS_NUMBER_HOURLY_MAX=5            # phone codes to one number an hour
# SMS_NUMBER_DAILY_MAX=10            # phone codes to one number a day
# SMS_IP_HOURLY_MAX=20               # phone codes from one IP an hour
# SMS_IP_DAILY_MAX=50                # phone codes from one IP a day
# SENDER_VERIFY_ON_SAVE=false        # only when the mail host is unreachable:
#                                    # skips the login check on saving a sender
# Commerce: selling through Stripe Connect. Unset keeps each one off.
# TENANT_MARKETPLACE=off             # on (keys follow the environment) or off;
#                                    # test is legacy (test keys only)
# LIVE_SELLING_PILOT=on              # off: the plan or an admin exception opens
#                                    # live selling; on: only listed orgs sell live
# AFFILIATES_PAYPAL=off              # on lets affiliates be paid by PayPal
# GOOGLE_STORAGE_DELIVERABLES_BUCKET_NAME=  # sellers' files; public access
#                                    # prevention on
# CLAMAV_HOST=                       # clamd that scans sellers' files; unset
# CLAMAV_PORT=3310                   # files sell only while the switch is test.
#                                    # The compose file ships one: start it
#                                    # with --profile scanner, set clamav here
# SHIPPING_EASYPOST=off              # on lets an app owner connect EasyPost
# SHIPPING_SHIPPO=off                # on lets an app owner connect Shippo
```

Generate the secrets:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD BULLMQ_DASHBOARD_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
```

Paste the first five lines over the empty ones in the Security block, and add the sixth, `BULLMQ_DASHBOARD_PASSWORD`, which the template has no line for.

> **Five are required, `REDIS_PASSWORD` included.** The compose file interpolates `JWT_PASS`, `DB_ENCRYPTION_KEY`, `SECRET_KEY`, `OAUTH2_SECRET` and `REDIS_PASSWORD` with `${VAR:?message}`, so a missing or empty one aborts `docker compose up` before any container starts - there are no development fallbacks. Compose then prints one line per use of the variable, starting
>
> ```text
> required variable REDIS_PASSWORD is missing a value: REDIS_PASSWORD is required
> ```
>
> and ending with a pointer to the generate-secrets command. Older copies of the published docs printed only four secrets and left `REDIS_PASSWORD` out of both the template and the generate command, so a stack built from them stops here; generate the fifth value and add it.
>
> **The sixth is optional but worth setting.** `BULLMQ_DASHBOARD_PASSWORD` protects the background-job dashboard at `/api/admin/bullmq`. Unset, it falls back to `INSTALLATION_API_KEY` and the server warns at every boot.

Check: five filled secret lines plus `BULLMQ_DASHBOARD_PASSWORD`, and both Installation values. In the quick start the `MONGO_CONNECTION_URL` line is ignored (the compose points at its own MongoDB); leave it.

---

## Step 3 - Save the Docker Compose file

Save as `docker-compose.selfhost.yml`:

```yaml
# Self-Hosted: MongoDB + Redis + Server + Client + Auth
# Save as docker-compose.selfhost.yml
# Usage: docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d

services:
  # ── Infrastructure ──────────────────────────────────────────
  mongodb:
    image: mongo:7.0
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - SETUID
      - SETGID
      - DAC_OVERRIDE
      # The healthcheck runs mongosh as root, which leaves root-owned files
      # in /data/db/.mongodb; without CHOWN the entrypoint cannot hand them
      # back to mongodb and every restart after the first crash-loops.
      - CHOWN
    volumes:
      - mongodb_data:/data/db
    networks:
      - db
    healthcheck:
      # mongosh's own cold start can take most of 5s on a first boot, which
      # failed a first `up` with "container mongodb is unhealthy" while
      # mongod was fine. Same probe as the repo's docker-compose.selfhost.yml.
      test: ['CMD', 'mongosh', '--quiet', '--eval', "db.adminCommand('ping')"]
      interval: 10s
      timeout: 15s
      start_period: 60s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1024M
          cpus: '1.0'
          pids: 256
    logging:
      driver: json-file
      options:
        max-size: '100m'
        max-file: '3'

  redis:
    image: redis:7.4-bookworm
    restart: unless-stopped
    read_only: true
    user: '999:999'
    cap_drop:
      - ALL
    # maxmemory stays well under the 256M limit below: Redis needs memory
    # beyond its data (allocator overhead, fragmentation, the AOF rewrite's
    # fork), and a Redis that reaches the limit is killed instead of refusing
    # writes. To give Redis more, raise both numbers together.
    command: redis-server --appendonly yes --maxmemory-policy noeviction --maxmemory 150mb --requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD is required — run the generate-secrets command from the quick start}
    tmpfs:
      - /tmp
    volumes:
      - redis_data:/data
    networks:
      - db
    healthcheck:
      test:
        [
          'CMD',
          'redis-cli',
          '-a',
          '${REDIS_PASSWORD:?REDIS_PASSWORD is required — run the generate-secrets command from the quick start}',
          'ping',
        ]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
          pids: 64
    logging:
      driver: json-file
      options:
        max-size: '50m'
        max-file: '3'

  # ── Backend ─────────────────────────────────────────────────
  tenant-server:
    image: buildbaseapp/tenant-server:latest
    restart: unless-stopped
    # The workers run in this process. Compose's default of 10 s would kill
    # a running job on every upgrade or restart; the server exits by itself
    # within 150 s, and long jobs hand themselves back as it closes.
    stop_grace_period: 180s
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
      - /var/log
    ports:
      - '${TENANT_SERVER_PORT:-4101}:3000'
    environment:
      - NODE_ENV=production
      - PORT=3000
      # Keep the Node heap below the 1024M container limit — the image
      # default is sized for larger hosts and would get OOM-killed here.
      - NODE_OPTIONS=--max-old-space-size=768
      - SERVER_URL=${TENANT_SERVER_URL:-http://localhost:4101}
      - APPLICATION_URL=${CLIENT_URL:-http://localhost:4100}
      - AUTH_SERVER_URL=${AUTH_URL:-http://localhost:4103}
      # The port is published directly: nothing in front appends to
      # X-Forwarded-For. Set 1 (or more) only once a proxy that appends sits
      # in front, or any caller picks its own address for every per-IP limit.
      - TRUST_PROXY=${TRUST_PROXY:-0}
      - MONGO_CONNECTION_URL=mongodb://mongodb:27017/
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD:?REDIS_PASSWORD is required — run the generate-secrets command from the quick start}
      - INSTALLATION_API_KEY=${INSTALLATION_API_KEY:-}
      - INSTALLATION_ID=${INSTALLATION_ID:-}
      - JWT_PASS=${JWT_PASS:?JWT_PASS is required — run the generate-secrets command from the quick start}
      - OAUTH2_SECRET=${OAUTH2_SECRET:?OAUTH2_SECRET is required — run the generate-secrets command from the quick start}
      - DB_ENCRYPTION_KEY=${DB_ENCRYPTION_KEY:?DB_ENCRYPTION_KEY is required (64 hex chars) — run the generate-secrets command from the quick start}
      - SECRET_KEY=${SECRET_KEY:?SECRET_KEY is required — run the generate-secrets command from the quick start}
      - GOOGLE_AUTH_CLIENT_ID=${GOOGLE_AUTH_CLIENT_ID:-}
      - GOOGLE_AUTH_CLIENT_SECRET=${GOOGLE_AUTH_CLIENT_SECRET:-}
      - GOOGLE_STORAGE_ASSETS_BUCKET_NAME=${GOOGLE_STORAGE_ASSETS_BUCKET_NAME:-}
      # Direct uploads (up to 100 MB, form file fields, SDK uploads). Empty
      # keeps every upload on the 5 MB server route.
      - GOOGLE_STORAGE_STAGING_BUCKET_NAME=${GOOGLE_STORAGE_STAGING_BUCKET_NAME:-}
      - GOOGLE_STORAGE_FINALIZE_TOKEN=${GOOGLE_STORAGE_FINALIZE_TOKEN:-}
      - GOOGLE_STORAGE_USAGE_LOG_BUCKET=${GOOGLE_STORAGE_USAGE_LOG_BUCKET:-}
      - GOOGLE_STORAGE_USAGE_LOG_PREFIX=${GOOGLE_STORAGE_USAGE_LOG_PREFIX:-}
      # Owner data exports. Empty keeps them off (the routes answer 503).
      - EXPORTS_BUCKET=${EXPORTS_BUCKET:-}
      # Storage switches. Empty keeps each one's code default.
      - TENANT_STORAGE_GATE=${TENANT_STORAGE_GATE:-}
      - TENANT_STORAGE_BILLING=${TENANT_STORAGE_BILLING:-}
      - TENANT_STORAGE_INTEGRITY=${TENANT_STORAGE_INTEGRITY:-}
      - TENANT_STORAGE_PURGE=${TENANT_STORAGE_PURGE:-}
      # URL safety. Unset means no reputation checking and links keep working;
      # each tuning var below falls back to its code default when empty.
      - GOOGLE_WEB_RISK_API_KEY=${GOOGLE_WEB_RISK_API_KEY:-}
      - URL_SAFETY_ENABLED=${URL_SAFETY_ENABLED:-}
      - URL_SAFETY_LOG_ONLY=${URL_SAFETY_LOG_ONLY:-}
      - URL_SAFETY_CLEAN_TTL_SECONDS=${URL_SAFETY_CLEAN_TTL_SECONDS:-}
      - WEB_RISK_TIMEOUT_MS=${WEB_RISK_TIMEOUT_MS:-}
      # Breached-password check. Unset means on; off for an install that
      # cannot reach api.pwnedpasswords.com.
      - BREACHED_PASSWORD_CHECK=${BREACHED_PASSWORD_CHECK:-}
      # Bot protection (Cloudflare Turnstile) on this install's sign-in
      # domain. Unset means no challenge unless an org saves its own keys.
      - TURNSTILE_SITE_KEY=${TURNSTILE_SITE_KEY:-}
      - TURNSTILE_SECRET_KEY=${TURNSTILE_SECRET_KEY:-}
      # Phone sign-in code limits per number and per IP. Unset means the
      # defaults (5 and 10 per number, 20 and 50 per IP, an hour and a day).
      - SMS_NUMBER_HOURLY_MAX=${SMS_NUMBER_HOURLY_MAX:-}
      - SMS_NUMBER_DAILY_MAX=${SMS_NUMBER_DAILY_MAX:-}
      - SMS_IP_HOURLY_MAX=${SMS_IP_HOURLY_MAX:-}
      - SMS_IP_DAILY_MAX=${SMS_IP_DAILY_MAX:-}
      # Unset keeps the login check when an email sender is saved; only
      # "false" skips it, for a server that cannot reach the mail host.
      - SENDER_VERIFY_ON_SAVE=${SENDER_VERIFY_ON_SAVE:-}
      # Commerce (selling through Stripe Connect). All off or empty by
      # default: unset keeps selling, PayPal payouts and label providers
      # closed, and file items unavailable.
      - TENANT_MARKETPLACE=${TENANT_MARKETPLACE:-}
      # Unset keeps the live-selling pilot list on; off lets the plan decide.
      - LIVE_SELLING_PILOT=${LIVE_SELLING_PILOT:-}
      - AFFILIATES_PAYPAL=${AFFILIATES_PAYPAL:-}
      - GOOGLE_STORAGE_DELIVERABLES_BUCKET_NAME=${GOOGLE_STORAGE_DELIVERABLES_BUCKET_NAME:-}
      - CLAMAV_HOST=${CLAMAV_HOST:-}
      - CLAMAV_PORT=${CLAMAV_PORT:-}
      - SHIPPING_EASYPOST=${SHIPPING_EASYPOST:-}
      - SHIPPING_SHIPPO=${SHIPPING_SHIPPO:-}
      - CORS_WHITELISTED_DOMAINS=${CLIENT_URL:-http://localhost:4100},${AUTH_URL:-http://localhost:4103}
      # Optional: point APM/log telemetry at YOUR OWN New Relic account.
      # Leave unset (the default) and no telemetry is collected or sent.
      - NEW_RELIC_LICENSE_KEY=${NEW_RELIC_LICENSE_KEY:-}
      - NEW_RELIC_APP_NAME=${NEW_RELIC_APP_NAME:-}
      - LOG_LEVEL=${LOG_LEVEL:-}
      # The job dashboard's password. Unset, it falls back to the
      # installation API key, and the server warns at every boot.
      - BULLMQ_DASHBOARD_PASSWORD=${BULLMQ_DASHBOARD_PASSWORD:-}
    depends_on:
      mongodb:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - db
      - app
    healthcheck:
      test: ['CMD', 'wget', '-qO-', 'http://127.0.0.1:3000/api/ready']
      interval: 15s
      timeout: 5s
      start_period: 45s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1024M
          cpus: '1.0'
          pids: 256
    logging:
      driver: json-file
      options:
        max-size: '100m'
        max-file: '5'

  # ── Frontend ────────────────────────────────────────────────
  client:
    image: buildbaseapp/client:latest
    restart: unless-stopped
    # NOTE: read_only must NOT be set on client or auth. Their entrypoints
    # rewrite __NEXT_PUBLIC_*__ URL placeholders in the JS bundles at
    # startup; a read-only filesystem makes that rewrite fail silently and
    # the app calls the literal placeholder string instead of your URL.
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
      - /var/cache/nginx
      - /var/run
    ports:
      - '${CLIENT_PORT:-4100}:3000'
    environment:
      - NEXT_PUBLIC_SERVER_URL=${TENANT_SERVER_URL:-http://localhost:4101}
      - NEXT_PUBLIC_DEFAULT_TENANT_SERVER_URL=${TENANT_SERVER_URL:-http://localhost:4101}
      - NEXT_PUBLIC_INSTALLATION_ID=${INSTALLATION_ID:-}
      # Optional: browser monitoring against YOUR OWN New Relic account.
      # Account ID and browser key are shared; the app ID is per app.
      - NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID=${NEW_RELIC_BROWSER_ACCOUNT_ID:-}
      - NEXT_PUBLIC_NEW_RELIC_BROWSER_LICENSE_KEY=${NEW_RELIC_BROWSER_LICENSE_KEY:-}
      - NEXT_PUBLIC_NEW_RELIC_APP_ID=${NEW_RELIC_BROWSER_APP_ID_CLIENT:-}
    networks:
      - app
    healthcheck:
      test: ['CMD', 'wget', '-qO-', 'http://127.0.0.1:3000/']
      interval: 15s
      timeout: 5s
      start_period: 30s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
          pids: 128
    logging:
      driver: json-file
      options:
        max-size: '50m'
        max-file: '3'

  auth:
    image: buildbaseapp/auth:latest
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
      - /var/cache/nginx:uid=1001,gid=1001
      - /var/run:uid=1001,gid=1001
    ports:
      - '${AUTH_PORT:-4103}:3000'
    environment:
      - NEXT_PUBLIC_SERVER_URL=${TENANT_SERVER_URL:-http://localhost:4101}
      # Optional: browser monitoring against YOUR OWN New Relic account.
      - NEXT_PUBLIC_NEW_RELIC_ACCOUNT_ID=${NEW_RELIC_BROWSER_ACCOUNT_ID:-}
      - NEXT_PUBLIC_NEW_RELIC_BROWSER_LICENSE_KEY=${NEW_RELIC_BROWSER_LICENSE_KEY:-}
      - NEXT_PUBLIC_NEW_RELIC_APP_ID=${NEW_RELIC_BROWSER_APP_ID_AUTH:-}
    networks:
      - app
    healthcheck:
      test: ['CMD', 'wget', '-qO-', 'http://127.0.0.1:3000/health']
      interval: 15s
      timeout: 5s
      start_period: 30s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
          pids: 128
    logging:
      driver: json-file
      options:
        max-size: '50m'
        max-file: '3'

  # Optional virus scanner for the files sellers sell. Off unless you start
  # the "scanner" profile:
  #   docker compose ... --profile scanner up -d
  # and set CLAMAV_HOST=clamav in .env.selfhost. It needs about 3 GB of
  # memory (clamd keeps its signatures in memory) and outbound internet,
  # since freshclam downloads the signatures; the first start takes a few
  # minutes. Port 3310 is reachable inside the app network only.
  clamav:
    image: clamav/clamav:1.4.6
    profiles: ['scanner']
    restart: unless-stopped
    volumes:
      - clamav_db:/var/lib/clamav
    networks:
      - app
    healthcheck:
      test: ['CMD', '/usr/local/bin/clamdcheck.sh']
      interval: 60s
      timeout: 15s
      start_period: 600s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 3072M
    logging:
      driver: json-file
      options:
        max-size: '20m'
        max-file: '3'

volumes:
  mongodb_data:
  redis_data:
  clamav_db:

# Network segmentation: databases isolated from frontends.
# Only tenant-server bridges both networks.
networks:
  db:
    driver: bridge
    internal: true
  app:
    driver: bridge
```

Things in there worth not "tidying up":

- **`client` and `auth` must not be `read_only`.** Their entrypoints rewrite the `__NEXT_PUBLIC_*__` URL placeholders inside the built JS at startup. On a read-only filesystem that rewrite fails quietly and the app then calls the literal string `__NEXT_PUBLIC_SERVER_URL__` instead of your server. `tenant-server` and `redis` are read-only on purpose (and `nginx` in production).
- **`NODE_OPTIONS=--max-old-space-size=768` on `tenant-server`.** The image default is sized for larger hosts and exceeds the 1024M container limit, so without the cap the container is OOM-killed under load.
- **`stop_grace_period: 180s` on `tenant-server`.** The workers run in this process. Compose's default of 10 s would kill a running job on every upgrade or restart; the server exits by itself within 150 s.
- **`TRUST_PROXY=${TRUST_PROXY:-0}`.** The port is published directly, so nothing in front appends to `X-Forwarded-For`. Raise it only once an appending proxy sits in front; set too high, any caller picks its own address for every per-IP limit.
- **`CHOWN` on `mongodb`, and its slower healthcheck.** Without `CHOWN` every restart after the first crash-loops; the longer `timeout` and `start_period` stop a first `up` failing with "container mongodb is unhealthy" while mongod is fine.
- **Redis `--maxmemory 150mb` under a 256M limit.** A Redis that reaches its container limit is killed instead of refusing writes. To give Redis more, raise both numbers together.
- **The `clamav` service is optional and off.** It scans the files sellers sell, starts only with `--profile scanner` (and `CLAMAV_HOST=clamav` in `.env.selfhost`), needs about 3 GB of memory and outbound internet for its signatures.

Check: `docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost config` parses with no error. Pass `--env-file`, or Compose reports every required variable as missing.

---

## Step 4 - Start the stack

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

---

## Step 5 - Verify

```bash
# Check all services are running
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost ps

# Server should answer {"ready":true,"mongo":"ok","redis":"ready"}
curl http://localhost:4101/api/ready
```

Check: `/api/ready` returns `{"ready":true,"mongo":"ok","redis":"ready"}`, which means MongoDB and Redis are connected. A `503` with `"ready": false` names the connection that is down. Anything else goes to [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md).

The tenant server will not start at all without `INSTALLATION_ID` and `INSTALLATION_API_KEY`; it says which variable is missing.

---

## Step 6 - Connect

1. In the dashboard, create an organization with the **Self-hosted** hosting mode and choose your installation. It shows **Connected** once the server has checked in, within a few minutes of starting.
2. Open the organization's setup, enter your server URL (`http://localhost:4101` for local testing), click **Test connection**, then **Complete setup**.

A local or private address can show **Not checked from this browser**: the dashboard page may not be allowed to reach it. Complete setup anyway if the server is running. BuildBase never connects to a private address itself, so the features where its servers call yours need a public HTTPS URL - see [production.md](./production.md).

---

## Step 7 - Let people sign in

Your end users sign in through the auth portal, and the organization needs three things from you in the console first:

1. **An email sender** (Messaging, then Sender accounts). Sign-up verification codes, password resets and invitations go through it. Without one, the hosted page refuses password sign-up.
2. **A sign-in method**, such as email and password.
3. **That method enabled on your app**, the client your application signs in with.

Services are now at:

- Client: http://localhost:4100
- Server API: http://localhost:4101
- Auth portal: http://localhost:4103

---

## What's next

- Every environment variable -> [../config/env-reference.md](../config/env-reference.md)
- Production (Nginx, replicas, TLS) -> [production.md](./production.md)
- Updating: take the new compose file, then pull the new images -> [../operations/upgrades-backups.md](../operations/upgrades-backups.md)
- Point an app at this stack -> [../handoff/integrating-against-self-host.md](../handoff/integrating-against-self-host.md)
