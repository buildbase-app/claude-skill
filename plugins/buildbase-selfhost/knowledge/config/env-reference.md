# Configuration — Environment Variable Reference

Every environment variable for a self-hosted stack, **exactly as the docs define them.** Where a default differs between the configuration page and the actual compose file, both are noted.

> **Source (verbatim):** `docs/content/self-hosted/configuration.mdx` → [docs.buildbase.app/self-hosted/configuration](https://docs.buildbase.app/self-hosted/configuration), cross-checked against the compose files in [../deploy/quick-start.md](../deploy/quick-start.md) and [../deploy/production.md](../deploy/production.md). Anything not in these docs is flagged as **[not documented]** — don't assert it as fact.

---

## Installation (Required)

Provided by the BuildBase dashboard when you create an Installation.

| Variable | Description |
|---|---|
| `INSTALLATION_API_KEY` | Installation API key (from dashboard) |
| `INSTALLATION_ID` | Installation ID (from dashboard) |

---

## Server (Required)

| Variable | Description |
|---|---|
| `NODE_ENV` | Set to `production` |
| `PORT` | Server port (default: `3000`) |
| `MONGO_CONNECTION_URL` | MongoDB connection string |
| `REDIS_HOST` | Redis hostname (default: `localhost`) |
| `REDIS_PORT` | Redis port (default: `6379`) |
| `SERVER_URL` | Public URL of the tenant server (default: `http://localhost:4101`) |
| `APPLICATION_URL` | Public URL of the client app (default: `http://localhost:4100`) |
| `AUTH_SERVER_URL` | Public URL of the auth portal (default: `http://localhost:4103`) |
| `JWT_PASS` | JWT signing secret |
| `DB_ENCRYPTION_KEY` | Database field encryption key |
| `SECRET_KEY` | General application secret |
| `OAUTH2_SECRET` | OAuth2 token secret |

> **How these are set in practice (from the compose files):**
> - In the **quick-start** compose, `MONGO_CONNECTION_URL` is hard-coded to the bundled Mongo: `mongodb://mongodb:27017/`. In **production**, the tenant-server uses `env_file: .env.selfhost`, so you provide your external Mongo URL there.
> - `REDIS_HOST=redis` / `REDIS_PORT=6379` are set to the compose service. (The `localhost` default applies only outside that network.)
> - `SERVER_URL` / `APPLICATION_URL` / `AUTH_SERVER_URL` are populated from `TENANT_SERVER_URL` / `CLIENT_URL` / `AUTH_URL` in `.env.selfhost`.
> - The four secrets have `localdev_..._do_not_use_in_production` fallbacks in the quick-start compose so it boots locally with blanks. **Always set real values for production.**

---

## Client App

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SERVER_URL` | Tenant server URL |
| `NEXT_PUBLIC_DEFAULT_TENANT_SERVER_URL` | Default tenant server URL |
| `NEXT_PUBLIC_INSTALLATION_ID` | Installation ID (for org filtering) |

---

## CORS

| Variable | Description |
|---|---|
| `CORS_WHITELISTED_DOMAINS` | Comma-separated list of allowed origins |

The platform origins (`console.buildbase.app`) are always allowed by default. In the quick-start compose this is set automatically to `${CLIENT_URL},${AUTH_URL}`.

---

## Redis

| Variable | Description | Default |
|---|---|---|
| `REDIS_PASSWORD` | Password (if required) | — |
| `REDIS_DB` | Database number | `0` |

> In the **quick-start** compose, Redis is started with `--requirepass ${REDIS_PASSWORD:-redispass}` and the tenant-server is given the matching `REDIS_PASSWORD`, so the effective default password is `redispass` if you don't set one. The **production** compose runs Redis without a password by default.

---

## Optional Services

| Variable | Description |
|---|---|
| `GOOGLE_AUTH_CLIENT_ID` | Google OAuth client ID (for Google vendor + Gmail sender) |
| `GOOGLE_AUTH_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_STORAGE_ASSETS_BUCKET_NAME` | GCS bucket for file uploads |
| `MAILGUN_API_KEY` | Mailgun API key (for transactional emails) |

---

## Generating secrets

All secret values should be unique, random strings:

```bash
openssl rand -hex 32
```

Or all required secrets at once:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET; do echo "$i=$(openssl rand -hex 32)"; done
```

---

## Docker Images

| Image | Description | Port | Health Check |
|---|---|---|---|
| `buildbaseapp/tenant-server` | Backend API server | 3000 | `GET /api/ready` |
| `buildbaseapp/client` | Web dashboard (Next.js SSR) | 3000 | `GET /` |
| `buildbaseapp/auth` | Auth portal (Next.js) | 3000 | `GET /` |

All images: `linux/amd64`, Node.js 20 Alpine.

---

## ⚠️ Not documented (don't assert these)

The docs define what each variable **is**, but do **not** document operational behavior such as:
- Whether `DB_ENCRYPTION_KEY` can be rotated, or what happens to existing data if it changes. *(Treat as unknown — see the gap note in [../operations/upgrades-backups.md](../operations/upgrades-backups.md). Do not tell operators it's safe or unsafe to rotate without confirming with Buildbase.)*
- The consequences of rotating `JWT_PASS` / `OAUTH2_SECRET` / `SECRET_KEY`.
- Any value validation rules (length, format) beyond "unique, random string."

If a user asks about these, say the docs don't cover it and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview).

---

## Read next

- Where these are set on first deploy → [../deploy/quick-start.md](../deploy/quick-start.md)
- Production specifics → [../deploy/production.md](../deploy/production.md)
- Diagnostics → [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
