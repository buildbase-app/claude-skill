# Production Deployment

The documented production deployment: **Nginx load balancer, two tenant-server replicas, external MongoDB, TLS and health monitoring.** Do the [quick-start.md](./quick-start.md) first and confirm `/api/ready` is true before layering this on.

> **Source:** `docs/content/self-hosted/production.mdx` -> [docs.buildbase.app/self-hosted/production](https://docs.buildbase.app/self-hosted/production). The compose file and `nginx-lb.conf` below are generated output of `packages/shared`, reproduced byte-for-byte.

---

## Prerequisites

- Linux (Ubuntu 20.04+ recommended), 2 GB+ RAM, 2 vCPU+.
- `amd64` or `arm64`. ARM servers such as AWS Graviton and Ampere are supported.
- Docker Engine 20+ and Docker Compose v2.
- **MongoDB 7+ external** - managed like Atlas, or self-managed. Production bundles no Mongo container.
- A domain pointed at the host, and a TLS certificate.

> The per-service memory limits below sum to about 3 GB (2x1024M for the replicas, plus 256M each for Redis, client and auth, 128M for Nginx, 64M for autoheal). That is arithmetic on the compose file, not a separate documented figure, but it means the 2 GB minimum is a floor for the quick start rather than a sizing for this file.

---

## Directory layout

```text
your-server/
  .env.selfhost               # environment configuration
  docker-compose.selfhost.yml # service definitions
  nginx-lb.conf               # Nginx load balancer config
```

---

## Step 1 - Environment file

The same `.env.selfhost` as the quick start; see [quick-start.md](./quick-start.md) Step 2 and [../config/env-reference.md](../config/env-reference.md). Generate the secrets:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
```

Two things matter more in production than in the quick start:

- **`MONGO_CONNECTION_URL` is required.** This compose has no Mongo container, and the server otherwise falls back to `localhost` inside the container and never becomes ready. The template ships an Atlas-style SRV example. TLS and replica-set parameters are not documented; see GAPS.md.
- **`REDIS_PASSWORD` is required here too.** This compose starts Redis with `--requirepass` and the tenant server reads the same file, so the value has to be present and identical on both sides.

---

## Step 2 - Docker Compose

```yaml
# Production: external MongoDB, Nginx LB, replicas, all 3 services
# Requires: .env.selfhost + nginx-lb.conf in same directory

services:
  redis:
    image: redis:7.4-alpine
    restart: unless-stopped
    read_only: true
    cap_drop:
      - ALL
    cap_add:
      - SETUID
      - SETGID
    # Same credential as the quick start. The tenant server reads
    # REDIS_PASSWORD from .env.selfhost through env_file, and sends AUTH
    # whenever it is non-empty - so a Redis started without --requirepass
    # here would refuse that AUTH and the server would never become ready.
    command: redis-server --appendonly yes --maxmemory-policy noeviction --maxmemory 256mb --requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD is required — run the generate-secrets command from the quick start}
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
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
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
    image: nginx:1.27-alpine
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    tmpfs:
      - /tmp
      - /var/cache/nginx:uid=101,gid=101
      - /var/run:uid=101,gid=101
    ports:
      - '${TENANT_SERVER_PORT:-4101}:80'
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

volumes:
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

What is deliberate in there:

- **The URL mapping block on `tenant-server`.** `env_file` supplies `TENANT_SERVER_URL`, `CLIENT_URL` and `AUTH_URL`, but the server reads `SERVER_URL`, `APPLICATION_URL` and `AUTH_SERVER_URL`. Without the mapping the server falls back to localhost URLs and CORS blocks both frontends.
- **`client` and `auth` are not `read_only`**, for the placeholder-rewrite reason in the quick start.
- **`replicas: 2`** plus the `autoheal=true` label and the `willfarrell/autoheal:1.2.0` service, which restarts unhealthy containers every 30s.
- **Network segmentation.** `db` is `internal: true`; only `tenant-server` sits on both networks.

There is no `update_config` block, and the docs make no zero-downtime claim. `deploy.update_config` is a Swarm key that `docker compose up` does not implement, so a rolling restart was never something this file delivered.

---

## Step 3 - Nginx configuration

Save as `nginx-lb.conf` beside the compose file:

```nginx
events {
    worker_connections 1024;
}

http {
    # Hide server version
    server_tokens off;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_general:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=api_auth:10m rate=5r/s;

    upstream app_servers {
        server tenant-server:3000;
    }

    server {
        listen 80;
        client_max_body_size 500M;

        # Reject oversized headers
        large_client_header_buffers 4 8k;

        # Rate limiting
        limit_req zone=api_general burst=60 nodelay;
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

        # Health checks (no rate limit, no logging)
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

        location / {
            proxy_pass http://app_servers;
            proxy_next_upstream error timeout http_502 http_503;
            proxy_next_upstream_tries 2;
            proxy_buffering off;
        }
    }
}
```

Note the auth rate-limit zone matches `^/api/(auth|oauth|login|register|password)`. The tenant server's own auth routes live under `/api/v1/auth/*`, which that pattern does not match, so do not describe the 5 r/s zone as protecting login.

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

> `certbot --nginx` configures an Nginx on the **host**. The Nginx in this compose listens on plain `:80` mapped to `TENANT_SERVER_PORT`, with a read-only config mount. How the two fit together - host proxy in front of the published ports - is not described in the docs. Say so rather than guessing at a topology.

## Step 6 - Connect

Enter the public URL (for example `https://api.yourcompany.com`) in the setup wizard and complete setup.

---

## Health checks

| Endpoint | Purpose |
|---|---|
| `GET /api/ready` | Readiness probe. `{"ready": true}` when DB and Redis are connected |
| `GET /api/health` | Full check. Documented as DB status, Redis latency, worker status |

---

## Updating

```bash
docker compose -f docker-compose.selfhost.yml pull
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

`replicas: 2` and `autoheal` reduce the blast radius, but the documented procedure is a pull and a restart. See [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

---

## Read next

- Updating, and what the docs do and do not say about backups -> [../operations/upgrades-backups.md](../operations/upgrades-backups.md)
- Config reference -> [../config/env-reference.md](../config/env-reference.md)
- Diagnostics -> [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
