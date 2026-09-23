# Quick Start - From Zero to a Running Stack

The documented path to a running self-hosted stack. Everything is bundled - **MongoDB, Redis, tenant server, client app and auth portal** in one Docker Compose file. The checks map to the docs' own verify step.

> **Source:** `docs/content/self-hosted/quick-start.mdx` -> [docs.buildbase.app/self-hosted/quick-start](https://docs.buildbase.app/self-hosted/quick-start). The `.env.selfhost` and `docker-compose.selfhost.yml` below are the generated output of `packages/shared` and are reproduced byte-for-byte. Re-sync them whenever the docs change; see MAINTENANCE.md.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-started/get-docker/) and Docker Compose v2.
- A BuildBase account at **[console.buildbase.app](https://console.buildbase.app)**.
- An `amd64` or `arm64` host. The images are multi-arch and run natively on both, Apple Silicon included.

Full requirements table (Ubuntu 20.04+, 2 GB RAM, 2 vCPU, MongoDB 7+, Redis 7+) is in [../config/env-reference.md](../config/env-reference.md).

---

## Step 1 - Create an organization and Installation

1. Log in to **[console.buildbase.app](https://console.buildbase.app)**.
2. Create an organization with **Self-Hosted** hosting mode.
3. The setup wizard guides you to create an **Installation**.
4. Copy the **Installation API Key** and **Installation ID**.

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
# MAILGUN_API_KEY=
# GOOGLE_WEB_RISK_API_KEY=
# URL_SAFETY_ENABLED=true            # default: true
# URL_SAFETY_LOG_ONLY=false          # default: false - a malicious destination
#                                    # is refused as soon as the key is set
# URL_SAFETY_CLEAN_TTL_SECONDS=3600
# WEB_RISK_TIMEOUT_MS=5000
```

Generate every secret the compose file demands:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
```

Paste those five lines into `.env.selfhost`.

> **All five are required, `REDIS_PASSWORD` included.** The compose file interpolates them with `${VAR:?message}`, so a missing or empty one aborts `docker compose up` before any container starts - there are no development fallbacks any more. If you see
>
> ```text
> REDIS_PASSWORD is required - run the generate-secrets command from the quick start
> ```
>
> then the variable is unset or blank in `.env.selfhost`. Older copies of the published docs printed only four secrets and left `REDIS_PASSWORD` out of both the template and the generate command, so a stack built from them stops here; generate the fifth value and add it.

Check: five filled secret lines, plus both Installation values.

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
    volumes:
      - mongodb_data:/data/db
    networks:
      - db
    healthcheck:
      test: ['CMD', 'mongosh', '--eval', "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      start_period: 20s
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
        max-file: '3'

  redis:
    image: redis:7.4-alpine
    restart: unless-stopped
    read_only: true
    cap_drop:
      - ALL
    cap_add:
      - SETUID
      - SETGID
    command: redis-server --appendonly yes --maxmemory-policy noeviction --maxmemory 256mb --requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD is required — run the generate-secrets command from the quick start}
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
      - MAILGUN_API_KEY=${MAILGUN_API_KEY:-}
      # URL safety. Unset means no reputation checking and links keep working;
      # each tuning var below falls back to its code default when empty.
      - GOOGLE_WEB_RISK_API_KEY=${GOOGLE_WEB_RISK_API_KEY:-}
      - URL_SAFETY_ENABLED=${URL_SAFETY_ENABLED:-}
      - URL_SAFETY_LOG_ONLY=${URL_SAFETY_LOG_ONLY:-}
      - URL_SAFETY_CLEAN_TTL_SECONDS=${URL_SAFETY_CLEAN_TTL_SECONDS:-}
      - WEB_RISK_TIMEOUT_MS=${WEB_RISK_TIMEOUT_MS:-}
      - CORS_WHITELISTED_DOMAINS=${CLIENT_URL:-http://localhost:4100},${AUTH_URL:-http://localhost:4103}
      # Optional: point APM/log telemetry at YOUR OWN New Relic account.
      # Leave unset (the default) and no telemetry is collected or sent.
      - NEW_RELIC_LICENSE_KEY=${NEW_RELIC_LICENSE_KEY:-}
      - NEW_RELIC_APP_NAME=${NEW_RELIC_APP_NAME:-}
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

volumes:
  mongodb_data:
  redis_data:

# Network segmentation: databases isolated from frontends.
# Only tenant-server bridges both networks.
networks:
  db:
    driver: bridge
    internal: true
  app:
    driver: bridge
```

Two things in there worth not "tidying up":

- **`client` and `auth` must not be `read_only`.** Their entrypoints rewrite the `__NEXT_PUBLIC_*__` URL placeholders inside the built JS at startup. On a read-only filesystem that rewrite fails quietly and the app then calls the literal string `__NEXT_PUBLIC_SERVER_URL__` instead of your server. `tenant-server`, `redis` and `nginx` are read-only on purpose.
- **`NODE_OPTIONS=--max-old-space-size=768` on `tenant-server`.** The image default is sized for larger hosts and exceeds the 1024M container limit, so without the cap the container is OOM-killed under load.

Check: `docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost config` parses with no error. Pass `--env-file`, or Compose reports every required variable as missing.

---

## Step 4 - Start the stack

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

---

## Step 5 - Verify

```bash
docker compose -f docker-compose.selfhost.yml ps

curl http://localhost:4101/api/ready
```

Check: `/api/ready` returns `{"ready": true}`, which per the docs means DB and Redis are connected. Anything else goes to [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md).

---

## Step 6 - Connect

Back in the dashboard wizard, enter your server URL (`http://localhost:4101` for local testing), click **Test Connection**, then **Complete Setup**.

Services are now at:

- Client: http://localhost:4100
- Server API: http://localhost:4101
- Auth portal: http://localhost:4103

---

## What's next

- Every environment variable -> [../config/env-reference.md](../config/env-reference.md)
- Production (Nginx, replicas, TLS) -> [production.md](./production.md)
- Point an app at this stack -> [../handoff/integrating-against-self-host.md](../handoff/integrating-against-self-host.md)
