# Quick Start — From Zero to a Running Stack

The documented path to a running self-hosted stack. Everything is bundled — **MongoDB, Redis, tenant server, client app, and auth portal** in one Docker Compose file. The ✅ checks map to the docs' own verify step.

> **Source (verbatim):** `docs/content/self-hosted/quick-start.mdx` → [docs.buildbase.app/self-hosted/quick-start](https://docs.buildbase.app/self-hosted/quick-start). The `.env.selfhost` and `docker-compose.selfhost.yml` below are reproduced exactly from the docs.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-started/get-docker/) and Docker Compose installed.
- A BuildBase account at **[console.buildbase.app](https://console.buildbase.app)**.

(The Requirements table — Ubuntu 20.04+, 2 GB RAM, 2 vCPU min, Docker Engine 20+/Compose v2, MongoDB 7+, Redis 7+ — is in [../config/env-reference.md](../config/env-reference.md) and the overview docs.)

---

## Step 1 — Create an Organization & Installation

1. Log in to **[console.buildbase.app](https://console.buildbase.app)**.
2. Create a new organization with **Self-Hosted** hosting mode.
3. The setup wizard will guide you to create an **Installation**.
4. Copy your **Installation API Key** and **Installation ID**.

✅ **Check:** You have both values copied. (Concept: [../mental-models/installations.md](../mental-models/installations.md).)

---

## Step 2 — Create your environment file

Save this as `.env.selfhost`:

```bash
# ═══════════════════════════════════════════════════════════════════
# Self-Hosted — Production Environment
# ═══════════════════════════════════════════════════════════════════

# ── Installation (from BuildBase dashboard) ──────────────────────
INSTALLATION_API_KEY=<INSTALLATION_API_KEY>
INSTALLATION_ID=<INSTALLATION_ID>

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

# ── Optional services ────────────────────────────────────────────
# GOOGLE_AUTH_CLIENT_ID=
# GOOGLE_AUTH_CLIENT_SECRET=
# GOOGLE_STORAGE_ASSETS_BUCKET_NAME=
# MAILGUN_API_KEY=
```

Generate all secrets at once:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET; do echo "$i=$(openssl rand -hex 32)"; done
```

> Note from the compose file: if you leave a secret blank, the tenant-server falls back to a `localdev_..._do_not_use_in_production` value so it still boots locally. **Fill them in for any real deployment.** Each var's meaning is in [../config/env-reference.md](../config/env-reference.md).

✅ **Check:** The four secret lines have values, and both Installation values are filled in.

---

## Step 3 — Save the Docker Compose file

Save this as `docker-compose.selfhost.yml` (reproduced verbatim from the docs):

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
    command: redis-server --appendonly yes --maxmemory-policy noeviction --maxmemory 256mb --requirepass ${REDIS_PASSWORD:-redispass}
    tmpfs:
      - /tmp
    volumes:
      - redis_data:/data
    networks:
      - db
    healthcheck:
      test: ['CMD', 'redis-cli', '-a', '${REDIS_PASSWORD:-redispass}', 'ping']
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
      - SERVER_URL=${TENANT_SERVER_URL:-http://localhost:4101}
      - APPLICATION_URL=${CLIENT_URL:-http://localhost:4100}
      - AUTH_SERVER_URL=${AUTH_URL:-http://localhost:4103}
      - MONGO_CONNECTION_URL=mongodb://mongodb:27017/
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD:-redispass}
      - INSTALLATION_API_KEY=${INSTALLATION_API_KEY:-<INSTALLATION_API_KEY>}
      - INSTALLATION_ID=${INSTALLATION_ID:-<INSTALLATION_ID>}
      - JWT_PASS=${JWT_PASS:-localdev_jwt_secret_do_not_use_in_production}
      - OAUTH2_SECRET=${OAUTH2_SECRET:-localdev_oauth2_secret_do_not_use_in_production}
      - DB_ENCRYPTION_KEY=${DB_ENCRYPTION_KEY:-localdev_db_encryption_key_do_not_use_in_production}
      - SECRET_KEY=${SECRET_KEY:-localdev_secret_key_do_not_use_in_production}
      - CORS_WHITELISTED_DOMAINS=${CLIENT_URL:-http://localhost:4100},${AUTH_URL:-http://localhost:4103}
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
    read_only: true
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
    networks:
      - app
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
    read_only: true
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
    networks:
      - app
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

✅ **Check:** `docker compose -f docker-compose.selfhost.yml config` parses with no error.

---

## Step 4 — Start the stack

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

---

## Step 5 — Verify

```bash
# Check all services are running
docker compose -f docker-compose.selfhost.yml ps

# Server should return {"ready": true}
curl http://localhost:4101/api/ready
```

✅ **Check:** `/api/ready` returns `{"ready": true}` — per the docs this means **DB and Redis are connected**. If not, see [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md).

---

## Step 6 — Connect

Go back to the setup wizard in the dashboard, enter your server URL (`http://localhost:4101` for local testing), click **Test Connection**, then **Complete Setup**.

Your services are now running at:
- **Client**: http://localhost:4100
- **Server API**: http://localhost:4101
- **Auth Portal**: http://localhost:4103

---

## What's Next

- **Configuration reference** (all env vars) → [../config/env-reference.md](../config/env-reference.md)
- **Production deployment** (SSL, custom domains, scaling) → [production.md](./production.md)
- **Point your app at this stack** → [../handoff/integrating-against-self-host.md](../handoff/integrating-against-self-host.md)
