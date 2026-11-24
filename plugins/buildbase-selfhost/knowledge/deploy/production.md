# Production Deployment

The documented production deployment: **Nginx load balancer, two tenant-server replicas, external MongoDB, TLS and health monitoring.** Do the [quick-start.md](./quick-start.md) first and confirm `/api/ready` is true before layering this on.

> **Source:** `docs/content/self-hosted/production.mdx` -> [docs.buildbase.app/self-hosted/production](https://docs.buildbase.app/self-hosted/production), plus the Enterprise SSO row of the requirements table in `overview.mdx`. The compose file, `nginx-lb.conf` and the commands below are generated output of `packages/shared/src/constants/self-hosted.ts`, reproduced byte-for-byte.

---

## Contents

- [Prerequisites](#prerequisites)
- [Directory layout](#directory-layout)
- [Step 1 - Environment file](#step-1---environment-file)
- [Step 2 - Docker Compose](#step-2---docker-compose)
- [Step 3 - Nginx configuration](#step-3---nginx-configuration)
- [Step 4 - Deploy](#step-4---deploy)
- [Step 5 - TLS](#step-5---tls)
- [Step 6 - Connect](#step-6---connect)
- [Health checks](#health-checks)
- [Enterprise SSO on a self-hosted server](#enterprise-sso-on-a-self-hosted-server)
- [Updating](#updating)

---

## Prerequisites

- Linux (Ubuntu 20.04+ recommended), 2 GB+ RAM, 2 vCPU+.
- `amd64` or `arm64`. ARM servers such as AWS Graviton and Ampere are supported.
- Docker Engine 20+ and Docker Compose v2.
- **MongoDB 7+ external** - managed like Atlas, or self-managed. Production bundles no Mongo container.
- A domain pointed at the host, and a TLS certificate (Let's Encrypt or custom).

> The per-service memory limits below sum to about 3 GB (2x1024M for the replicas, plus 256M each for Redis, client and auth, 128M for Nginx, 64M for autoheal), and the optional `clamav` scanner adds 3072M when its profile is started. That is arithmetic on the compose file, not a separate documented figure, but it means the 2 GB minimum is a floor for the quick start rather than a sizing for this file.

---

## Directory layout

```
your-server/
  .env.selfhost              # Environment configuration
  docker-compose.selfhost.yml # Service definitions
  nginx-lb.conf              # Nginx load balancer config
```

---

## Step 1 - Environment file

The same `.env.selfhost` as the quick start; see [quick-start.md](./quick-start.md) Step 2 and [../config/env-reference.md](../config/env-reference.md). Generate the secrets:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD BULLMQ_DASHBOARD_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
```

Things that matter more in production than in the quick start:

- **`MONGO_CONNECTION_URL` is required.** This compose has no Mongo container, and the server otherwise falls back to `localhost` inside the container and never becomes ready. The template ships an Atlas-style SRV example. TLS and replica-set parameters are not documented; see GAPS.md.
- **`REDIS_PASSWORD` is required here too.** This compose starts Redis with `--requirepass` and the tenant server reads the same file, so the value has to be present and identical on both sides.
- **`tenant-server` reads the whole file.** It takes `.env.selfhost` through `env_file`, so every optional variable you set there reaches it. `client` and `auth` do not: they get only the variables their `environment` block names.

---

## Step 2 - Docker Compose

```yaml
# Production: external MongoDB, Nginx LB, replicas, all 3 services
# Requires: .env.selfhost + nginx-lb.conf in same directory

services:
  redis:
    image: redis:7.4-bookworm
    restart: unless-stopped
    read_only: true
    user: '999:999'
    cap_drop:
      - ALL
    # Same credential as the quick start. The tenant server reads
    # REDIS_PASSWORD from .env.selfhost through env_file, and sends AUTH
    # whenever it is non-empty - so a Redis started without --requirepass
    # here would refuse that AUTH and the server would never become ready.
    # maxmemory stays well under the 256M limit below: Redis needs memory
    # beyond its data (allocator overhead, fragmentation, the AOF rewrite's
    # fork), and a Redis that reaches the limit is killed instead of refusing
    # writes. To give Redis more, raise both numbers together.
    command: redis-server --appendonly yes --maxmemory-policy noeviction --maxmemory 150mb --requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD is required — run the generate-secrets command from the quick start}
    tmpfs:
      - /tmp
    volumes:
      - redis_data:/data
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
      retries: 5
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
          pids: 64
    networks:
      - db

  # ── Backend (2 replicas behind Nginx LB) ──────────────────────
  tenant-server:
    image: buildbaseapp/tenant-server:latest
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp
      - /var/log
    env_file: .env.selfhost
    environment:
      - NODE_ENV=production
      - PORT=3000
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - NODE_OPTIONS=--max-old-space-size=768
      # Map the public URLs from .env.selfhost onto the names the server
      # reads. Without these the server falls back to localhost URLs and
      # CORS blocks the client and auth origins.
      - SERVER_URL=${TENANT_SERVER_URL}
      - APPLICATION_URL=${CLIENT_URL}
      - AUTH_SERVER_URL=${AUTH_URL}
      - CORS_WHITELISTED_DOMAINS=${CLIENT_URL},${AUTH_URL}
      # nginx below is the only way in and appends one X-Forwarded-For hop.
      # Self-hosted trusts no proxy by default, so without this every caller
      # is nginx's address: one shared bucket for every per-IP rate limit, and
      # a probe-shield ban takes the whole install offline. Raise it if
      # another appending proxy (a load balancer, Cloudflare) sits in front.
      - TRUST_PROXY=${TRUST_PROXY:-1}
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    # The workers run in each replica. Compose's default of 10 s would kill
    # a running job on every upgrade or restart; the server exits by itself
    # within 150 s, and long jobs hand themselves back as it closes.
    stop_grace_period: 180s
    healthcheck:
      test: ['CMD', 'wget', '-qO-', 'http://127.0.0.1:3000/api/ready']
      interval: 15s
      timeout: 5s
      start_period: 45s
      retries: 3
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1024M
          cpus: '1.0'
          pids: 256
    labels:
      - 'autoheal=true'
      # The readiness check fails while the server shuts down, and autoheal
      # restarts an unhealthy container with Docker's 10 s stop unless told
      # otherwise, which would kill the jobs stop_grace_period lets finish.
      - 'autoheal.stop.timeout=180'
    networks:
      - db
      - app

  # ── Frontend ──────────────────────────────────────────────────
  client:
    image: buildbaseapp/client:latest
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
      - NEXT_PUBLIC_SERVER_URL=${TENANT_SERVER_URL}
      - NEXT_PUBLIC_DEFAULT_TENANT_SERVER_URL=${TENANT_SERVER_URL}
      - NEXT_PUBLIC_INSTALLATION_ID=${INSTALLATION_ID}
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
          pids: 128
    networks:
      - app

  auth:
    image: buildbaseapp/auth:latest
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
      - NEXT_PUBLIC_SERVER_URL=${TENANT_SERVER_URL}
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
          pids: 128
    networks:
      - app

  # ── Load Balancer (tenant server only) ────────────────────────
  nginx:
    image: nginx:1.30-alpine
    # As nginx's own user, on an unprivileged port: with every capability
    # dropped, a root master can neither write the tmpfs below nor switch
    # its workers to that user, and exits at once.
    user: '101:101'
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:uid=101,gid=101
      - /var/cache/nginx:uid=101,gid=101
      - /var/run:uid=101,gid=101
    ports:
      - '${TENANT_SERVER_PORT:-4101}:8080'
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - tenant-server
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
          pids: 64
    networks:
      - app

  autoheal:
    image: willfarrell/autoheal:1.2.0
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    environment:
      - AUTOHEAL_CONTAINER_LABEL=autoheal
      - AUTOHEAL_INTERVAL=30
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'
          pids: 32

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

What is deliberate in there:

- **The URL mapping block on `tenant-server`.** `env_file` supplies `TENANT_SERVER_URL`, `CLIENT_URL` and `AUTH_URL`, but the server reads `SERVER_URL`, `APPLICATION_URL` and `AUTH_SERVER_URL`. Without the mapping the server falls back to localhost URLs and CORS blocks both frontends.
- **`TRUST_PROXY=${TRUST_PROXY:-1}`.** Nginx is the only way in and appends one `X-Forwarded-For` hop. Without it every caller is Nginx's address: one shared bucket for every per-IP rate limit, and a probe-shield ban takes the whole install offline. Raise it if another appending proxy (a load balancer, Cloudflare) sits in front.
- **`stop_grace_period: 180s` and `autoheal.stop.timeout=180`.** The workers run in each replica. The server exits by itself within 150 s and long jobs hand themselves back; the readiness check fails during shutdown, so autoheal is told to wait as long as Compose does.
- **`client` and `auth` are not `read_only`**, for the placeholder-rewrite reason in the quick start. Unlike the quick-start compose, they get no `NEXT_PUBLIC_NEW_RELIC_*` variables here.
- **`replicas: 2`** plus the `autoheal=true` label and the `willfarrell/autoheal:1.2.0` service, which restarts unhealthy containers every 30s.
- **Nginx runs as its own user (`101:101`) on port 8080**, published as `TENANT_SERVER_PORT`. With every capability dropped, a root master could neither write its tmpfs nor switch its workers to that user.
- **Redis runs as `999:999` with `--maxmemory 150mb` under a 256M limit.** Raise both numbers together.
- **The `clamav` service is optional and off** unless started with `--profile scanner`; see the quick start.
- **Network segmentation.** `db` is `internal: true`; only `tenant-server` sits on both networks.

There is no `update_config` block, and the docs make no zero-downtime claim. `deploy.update_config` is a Swarm key that `docker compose up` does not implement, so a rolling restart was never something this file delivered.

---

## Step 3 - Nginx configuration

Save as `nginx-lb.conf` beside the compose file:

```nginx
# Runs as nginx's own user (the compose sets user: 101), so its pid file
# goes where that user can write.
pid /tmp/nginx.pid;

events {
    worker_connections 1024;
}

http {
    # Hide server version
    server_tokens off;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_general:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=api_auth:10m rate=5r/s;
    # The SDK API, per person: the address and the session the SDK sends, so
    # an office behind one NAT is not one caller. An app start is nine calls.
    # The caller picks the header, so only the two shapes the server mints
    # (35 letters and digits, or an org id and then 35) count as a session;
    # anything else keys on the address alone, and the key length stays
    # bounded. A new id on every call still gets a new bucket, so api_sdk_ip
    # is the real per-address cap.
    map $http_x_session_id $sdk_session {
        "~^([0-9a-f]{24})?[0-9A-Za-z]{35}$" $http_x_session_id;
        default "";
    }
    limit_req_zone $binary_remote_addr$sdk_session zone=api_sdk_session:20m rate=20r/s;
    limit_req_zone $binary_remote_addr zone=api_sdk_ip:10m rate=200r/s;

    upstream app_servers {
        # Sticky by client address: socket.io opens with polling and upgrades
        # to a WebSocket, and the upgrade has to reach the replica that holds
        # the session. Without this, two replicas drop every other connection.
        hash $remote_addr consistent;
        server tenant-server:3000;
    }

    server {
        # Unprivileged: the container holds no capability to bind below 1024.
        listen 8080;
        client_max_body_size 500M;

        # Reject oversized headers
        large_client_header_buffers 4 8k;

        # Rate limiting. Each location sets its own limit_req: one set here
        # applies to every location without one, health checks included.
        limit_req_status 429;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        client_body_timeout 60s;
        client_header_timeout 30s;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Health checks (no rate limit, no logging). A load balancer's check
        # must never get a 429: it comes from one address, often the same
        # one as the traffic it fronts, and a refused check takes the
        # replica out of service.
        location /ready  { access_log off; proxy_pass http://app_servers/api/ready; }
        location /health { access_log off; proxy_pass http://app_servers/api/health; }

        # Stricter rate limit on auth endpoints
        location ~ ^/api/(auth|oauth|login|register|password) {
            limit_req zone=api_auth burst=10 nodelay;
            proxy_pass http://app_servers;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # The SDK's sign-in steps (login, register, codes, reset, token) stay
        # on the auth tier, as on cloud. The pattern above never matched
        # /api/v1/auth, so without this they fell to the SDK zones below.
        location /api/v1/auth {
            limit_req zone=api_auth burst=10 nodelay;
            proxy_pass http://app_servers;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # The SDK API (customer apps): per person, with an address-wide guard.
        location /api/v1/ {
            limit_req zone=api_sdk_session burst=60 nodelay;
            limit_req zone=api_sdk_ip burst=500 nodelay;
            proxy_pass http://app_servers;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            limit_req zone=api_general burst=60 nodelay;
            proxy_pass http://app_servers;
            proxy_next_upstream error timeout http_502 http_503;
            proxy_next_upstream_tries 2;
            proxy_buffering off;
        }
    }
}
```

What the zones do:

| Location | Limit | Why |
|---|---|---|
| `/ready`, `/health` | none, no access log | Proxy to `/api/ready` and `/api/health`. A load balancer's check must never get a 429 |
| `~ ^/api/(auth\|oauth\|login\|register\|password)` | `api_auth`, 5 r/s, burst 10 | Stricter limit on auth endpoints |
| `/api/v1/auth` | `api_auth`, 5 r/s, burst 10 | The SDK's sign-in steps (login, register, codes, reset, token), which the pattern above never matched |
| `/api/v1/` | `api_sdk_session` 20 r/s burst 60, and `api_sdk_ip` 200 r/s burst 500 | The SDK API, per person (address plus a well-formed `x-session-id`) with an address-wide guard |
| `/` | `api_general`, 30 r/s, burst 60 | Everything else; on an error, timeout, 502 or 503 it tries the upstream once more (`proxy_next_upstream_tries 2`) |

A refused request gets `429`. The upstream is sticky by client address (`hash $remote_addr consistent`): socket.io upgrades to a WebSocket, and the upgrade has to reach the replica that holds the session, so without it two replicas drop every other connection.

---

## Step 4 - Deploy

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

## Step 5 - TLS

```bash
sudo certbot --nginx -d api.yourcompany.com -d app.yourcompany.com -d auth.yourcompany.com
```

Or [Caddy](https://caddyserver.com/) for automatic HTTPS.

> `certbot --nginx` configures an Nginx on the **host**. The Nginx in this compose listens on plain HTTP (8080 inside the container, published on `TENANT_SERVER_PORT`) with a read-only config mount. How the two fit together - a host proxy in front of the published ports - is not described in the docs. Say so rather than guessing at a topology, and if a host proxy does sit in front, `TRUST_PROXY` has to count it.

## Step 6 - Connect

Enter the public URL (for example `https://api.yourcompany.com`) in the setup wizard and complete setup.

---

## Health checks

| Endpoint | Purpose |
|---|---|
| `GET /api/ready` | Readiness probe. `200` with `{"ready": true, "mongo": "ok", "redis": "ready"}` when MongoDB and Redis are connected (plus `cell` when `CELL_ID` is set); `503` with `"ready": false` and the state of each connection when one is down |
| `GET /api/health` | Health check. `{"status", "timestamp"}`, `200` when MongoDB and Redis are connected and `503` when one is down. Send `x-internal-api-key: <INSTALLATION_API_KEY>` for the full report: database and Redis state, Redis latency, tenant connections and pool sizes, process memory and uptime |

Every replica shares one Redis, so a Redis outage fails every replica's probe at the same moment. `READINESS_REDIS_FAIL_OPEN=true` keeps the probe answering ready while Redis is down, reported as `"redis": "degraded"`, so whatever acts on the probe does not take every replica out at once; the routes that need Redis then answer `503` on their own. It is off by default: Redis is required for readiness.

Through this Nginx the probes are also reachable as `/ready` and `/health`, with no rate limit.

---

## Enterprise SSO on a self-hosted server

Optional, and it works through the app owner's own WorkOS account. The docs' requirements:

- A public HTTPS `SERVER_URL`, so WorkOS can send the browser back to the sign-in callback, and outbound HTTPS to `api.workos.com`. No inbound connection from WorkOS is needed.
- A company's log streams sent by BuildBase need outbound access to its own SIEM (an HTTPS endpoint, Datadog's logs intake, or a Splunk HTTP Event Collector); a self-hosted server may also send to a private address over HTTP. With company audit logs on, the trail goes to `api.workos.com` too, and a WorkOS log stream is sent by WorkOS from its own addresses, never from your server.
- Any ingress or load balancer in front of the server must forward the `allowed-company-ids` request header unchanged.

---

## Updating

Back up MongoDB, save the current compose file over yours, then pull and restart:

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost pull
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

The full procedure (the backup, why the compose file comes first, migrations at boot, manual migrations, pinning a version, the overage migration) is in [../operations/upgrades-backups.md](../operations/upgrades-backups.md). `replicas: 2` and `autoheal` reduce the blast radius, but the documented procedure is a pull and a restart.

---

## Read next

- Updating, backups and migrations -> [../operations/upgrades-backups.md](../operations/upgrades-backups.md)
- Config reference -> [../config/env-reference.md](../config/env-reference.md)
- Diagnostics -> [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
