# Configuration - Environment Variable Reference

Every environment variable for a self-hosted stack, as the docs define them. Where a default differs between the configuration page and the compose file, both are noted.

> **Source:** `docs/content/self-hosted/configuration.mdx` -> [docs.buildbase.app/self-hosted/configuration](https://docs.buildbase.app/self-hosted/configuration), cross-checked against the compose files in [../deploy/quick-start.md](../deploy/quick-start.md) and [../deploy/production.md](../deploy/production.md). Anything not in these docs is flagged **[not documented]** - do not assert it as fact.

---

## Installation (required)

Provided by the console when you create an Installation.

| Variable | Description |
|---|---|
| `INSTALLATION_API_KEY` | Installation API key (from dashboard) |
| `INSTALLATION_ID` | Installation ID (from dashboard) |

---

## Server (required)

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

`INSTALLATION_API_KEY` and `INSTALLATION_ID` also appear in the docs' Server table, flagged required there as well.

### What the compose files actually demand

This is the part that decides whether a stack starts, so read it before the tables above.

Both compose files interpolate their secrets as `${VAR:?message}`, which makes Compose abort before starting a container when the variable is unset or empty. **There are no development fallbacks any more.** The five required values are:

```text
JWT_PASS  DB_ENCRYPTION_KEY  SECRET_KEY  OAUTH2_SECRET  REDIS_PASSWORD
```

Generate all five:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
```

> **`REDIS_PASSWORD` is required, not optional.** The Redis table below describes it as "Password (if required)", which reads as optional and is left over from when the composes had fallbacks. Both composes now start Redis with `--requirepass` and pass the same value to the tenant server, so it must be set and identical on both sides. Older published copies of the quick start printed only four secrets and had no line for this one, so a stack built from them aborts with `REDIS_PASSWORD is required`.

How the rest are set in practice:

- `MONGO_CONNECTION_URL` is hard-coded to the bundled Mongo (`mongodb://mongodb:27017/`) in the quick-start compose. In production there is no Mongo container and the value comes from `.env.selfhost` through `env_file` - **omit it there and the server falls back to localhost inside the container and never becomes ready.**
- `REDIS_HOST=redis` / `REDIS_PORT=6379` point at the compose service. The `localhost` default only applies outside that network.
- `SERVER_URL` / `APPLICATION_URL` / `AUTH_SERVER_URL` are mapped from `TENANT_SERVER_URL` / `CLIENT_URL` / `AUTH_URL`. The quick-start compose maps them with localhost fallbacks; the production compose maps them explicitly with no fallback, so all three must be in `.env.selfhost`. Without the mapping the server uses localhost URLs and CORS blocks both frontends.

---

## Client app

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

Platform origins (`console.buildbase.app`) are always allowed by default. Both compose files set this automatically to `${CLIENT_URL},${AUTH_URL}`.

---

## Redis

| Variable | Description | Default |
|---|---|---|
| `REDIS_PASSWORD` | Password. Required in practice - see the note above | - |
| `REDIS_DB` | Database number | `0` |

---

## Optional services

| Variable | Description |
|---|---|
| `TRUST_PROXY` | How many proxies sit in front of the server and append to `X-Forwarded-For`. Defaults to 0, which is right when the compose publishes the port directly. Set it to the number of appending proxies behind nginx, a load balancer or Cloudflare - too high and every per-IP rate limit is bypassable by a header the caller writes |
| `GOOGLE_AUTH_CLIENT_ID` | Google OAuth client ID (Google vendor + Gmail sender) |
| `GOOGLE_AUTH_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_STORAGE_ASSETS_BUCKET_NAME` | GCS bucket for file uploads |
| `MAILGUN_API_KEY` | Mailgun API key (transactional email) |
| `MAIL_TRACKING_SECRET` | Signing key for email open/click tracking links. Derived from `JWT_PASS` when unset; set it to make the tracking key independent of the auth key |

### URL safety (optional)

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_WEB_RISK_API_KEY` | Google Web Risk key for checking redirect destinations. Unset disables reputation checks; links still work | - |
| `URL_SAFETY_ENABLED` | Master switch. Only the literal `false` turns checks off, and every lookup then returns UNKNOWN | `true` |
| `URL_SAFETY_LOG_ONLY` | Record verdicts without acting on them. Set this true first to measure false positives, because otherwise setting the API key starts refusing malicious destinations straight away | `false` |
| `URL_SAFETY_CLEAN_TTL_SECONDS` | How long a clean verdict may be cached, capped at 86400. A threat verdict honours the expiry Google returns instead | `3600` |
| `WEB_RISK_TIMEOUT_MS` | Timeout for one Web Risk lookup. Lookups are on a background path but must not hang a worker | `5000` |

### Observability (optional)

Telemetry goes to **your own** New Relic account. Unset, which is the default, means nothing is collected or sent.

| Variable | Description |
|---|---|
| `NEW_RELIC_LICENSE_KEY` | Ingest license key for your own account. Unset disables all APM and log telemetry |
| `NEW_RELIC_APP_NAME` | APM application name (defaults to `buildbase-server-selfhost`) |
| `NEW_RELIC_BROWSER_ACCOUNT_ID` | Account ID for browser monitoring of the client and auth frontends, shared across apps |
| `NEW_RELIC_BROWSER_LICENSE_KEY` | Browser license key (`NRJS-...`), shared across apps |
| `NEW_RELIC_BROWSER_APP_ID_CLIENT` | Browser application ID for the client (console) frontend |
| `NEW_RELIC_BROWSER_APP_ID_AUTH` | Browser application ID for the auth frontend |

The compose files pass the server-side pair and the three browser variables through to the right containers, so setting them in `.env.selfhost` is enough for the production stack. The quick-start compose has no `env_file`, so add them under `tenant-server.environment` there.

---

## Docker images

| Image | Description | Port | Health check |
|---|---|---|---|
| `buildbaseapp/tenant-server` | Backend API server | 3000 | `GET /api/ready` |
| `buildbaseapp/client` | Web dashboard (Next.js SSR) | 3000 | `GET /` |
| `buildbaseapp/auth` | Auth portal (Next.js) | 3000 | `GET /health` |

All images are multi-arch (`linux/amd64, linux/arm64`) built on **Node.js 22 Alpine**, and `docker pull` selects the right variant automatically. 32-bit ARM (`linux/arm/v7`) is not supported.

Note the auth portal's health check is `GET /health`, not `GET /`. The client's is `GET /`.

---

## Generating secrets

Every secret should be a unique random string:

```bash
openssl rand -hex 32
```

---

## Not documented - do not assert these

The docs define what each variable **is** but not its operational behaviour:

- Whether `DB_ENCRYPTION_KEY` can be rotated, or what happens to existing data if it changes. Treat as unknown. Do not tell an operator it is safe or unsafe to rotate.
- The consequences of rotating `JWT_PASS`, `OAUTH2_SECRET` or `SECRET_KEY`.
- Value validation rules beyond "unique, random string". The one exception the compose states itself is `DB_ENCRYPTION_KEY`, whose error message asks for 64 hex characters, which is what `openssl rand -hex 32` produces.

The public self-hosted page at [buildbase.app/self-hosted](https://www.buildbase.app/self-hosted) does state that sensitive database fields are encrypted at rest with AES-256-CBC, and mentions per-organization key rotation - but that refers to the central server's ES256 signing keys, not `DB_ENCRYPTION_KEY`. Do not conflate them.

If asked about any of these, say the docs do not cover it and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview).

---

## Read next

- First deploy -> [../deploy/quick-start.md](../deploy/quick-start.md)
- Production -> [../deploy/production.md](../deploy/production.md)
- Diagnostics -> [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
