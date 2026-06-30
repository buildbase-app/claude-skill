# Production Deployment

The documented production deployment: **Nginx load balancer, 2 tenant-server replicas, external MongoDB, SSL, and health monitoring.** Do the [quick-start.md](./quick-start.md) first and confirm `/api/ready` is true before layering this on.

> **Source (verbatim):** `docs/content/self-hosted/production.mdx` → [docs.buildbase.app/self-hosted/production](https://docs.buildbase.app/self-hosted/production). The compose file and `nginx-lb.conf` below are reproduced exactly from the docs.

---

## Prerequisites

- Linux (Ubuntu 20.04+ recommended), **2 GB+ RAM, 2 vCPU+**.
- Docker Engine 20+ and Docker Compose v2.
- **MongoDB 7+** (managed like Atlas, or self-hosted) — note production uses an **external** Mongo, not a bundled container.
- Domain name pointed to your server's public IP.
- SSL certificate (Let's Encrypt or custom).

---

## Directory structure

```
your-server/
  .env.selfhost              # Environment configuration
  docker-compose.selfhost.yml # Service definitions
  nginx-lb.conf              # Nginx load balancer config
```

---

## Step 1 — Environment file

Same `.env.selfhost` as the quick-start (Installation values, public URLs, ports, the four `openssl rand -hex 32` secrets, optional services) — see [quick-start.md](./quick-start.md) Step 2 and [../config/env-reference.md](../config/env-reference.md). Generate secrets:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET; do echo "$i=$(openssl rand -hex 32)"; done
```

> The production tenant-server uses `env_file: .env.selfhost`, so your `MONGO_CONNECTION_URL` for the external database is read from that file. (It is **not** hard-coded to the bundled Mongo as it is in the quick-start.)

---

## Step 2 — Docker Compose

Reproduced verbatim from the docs:

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
    command: redis-server --appendonly yes --maxmemory-policy noeviction --maxmemory 256mb
    tmpfs:
      - /tmp
    volumes:
      - redis_data:/data
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
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
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    labels:
      - 'autoheal=true'
    networks:
      - db
      - app

  # ── Frontend ──────────────────────────────────────────────────
  client:
    image: buildbaseapp/client:latest
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

---

## Step 3 — Nginx configuration

Save as `nginx-lb.conf` in the same directory (verbatim from the docs):

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

---

## Step 4 — Deploy

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

## Step 5 — SSL with Let's Encrypt

```bash
sudo certbot --nginx -d api.yourcompany.com -d app.yourcompany.com -d auth.yourcompany.com
```

Or use [Caddy](https://caddyserver.com/) for automatic HTTPS with zero configuration.

## Step 6 — Connect

Enter your public URL (e.g. `https://api.yourcompany.com`) in the setup wizard and complete the setup.

---

## Health Checks

| Endpoint | Purpose |
|---|---|
| `GET /api/ready` | Readiness probe — returns `{"ready": true}` when DB and Redis are connected |
| `GET /api/health` | Full health check — DB status, Redis latency, worker status |

---

## Updating

Pull the latest images and restart:

```bash
docker compose -f docker-compose.selfhost.yml pull
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

The production tenant-server is configured with `update_config: parallelism: 1, delay: 10s, order: start-first` and runs **2 replicas** — so the rolling restart brings up a new replica before stopping the old one. See [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

---

## What the docs configure for you (don't strip these out)

These are all present in the compose / nginx above — worth knowing they exist:
- **2 tenant-server replicas**, `autoheal=true` label + the `willfarrell/autoheal:1.2.0` service (`AUTOHEAL_INTERVAL=30`).
- **Container hardening:** `read_only`, `cap_drop: ALL`, `no-new-privileges:true`, per-service memory/CPU/PID limits.
- **Nginx:** `server_tokens off`, rate limits (30 r/s general, 5 r/s on auth paths), `client_max_body_size 500M`, `large_client_header_buffers 4 8k`, the 60s/30s timeouts.
- **Network segmentation:** `db` network is `internal: true`; only tenant-server is on both `db` and `app`.

---

## Read next

- Updating + what the docs say (and don't say) about backups → [../operations/upgrades-backups.md](../operations/upgrades-backups.md)
- Config reference → [../config/env-reference.md](../config/env-reference.md)
- Diagnostics → [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
