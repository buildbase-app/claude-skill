# Configuration - Environment Variable Reference

Every environment variable for a self-hosted stack, as the docs define them. Where the configuration page and a compose file disagree, both are noted.

> **Source:** `docs/content/self-hosted/configuration.mdx` -> [docs.buildbase.app/self-hosted/configuration](https://docs.buildbase.app/self-hosted/configuration), generated from `ENV_VARS` in `packages/shared/src/constants/self-hosted.ts`, cross-checked against the compose files in [../deploy/quick-start.md](../deploy/quick-start.md) and [../deploy/production.md](../deploy/production.md). A few variables documented on other docs pages are named with their page. Anything not in these docs is flagged **[not documented]** - do not assert it as fact.

---

## Contents

- [Installation (required)](#installation-required)
- [Server (required)](#server-required)
- [What the compose files actually demand](#what-the-compose-files-actually-demand)
- [Client app](#client-app)
- [CORS](#cors)
- [Redis](#redis)
- [Proxy, logging and the job dashboard](#proxy-logging-and-the-job-dashboard)
- [Google Cloud and storage](#google-cloud-and-storage)
- [Email](#email)
- [URL safety](#url-safety)
- [Sign-in protection](#sign-in-protection)
- [Commerce](#commerce)
- [Observability](#observability)
- [Variables named on other pages](#variables-named-on-other-pages)
- [Docker images and IMAGE_TAG](#docker-images-and-image_tag)
- [Generating secrets](#generating-secrets)
- [Not documented - do not assert these](#not-documented---do-not-assert-these)

---

## Installation (required)

Provided by the console when you create an Installation (Account, then Installations).

| Variable | Description |
|---|---|
| `INSTALLATION_API_KEY` | Installation API key (from dashboard) |
| `INSTALLATION_ID` | Installation ID (from dashboard) |

Without either one the tenant server does not start, and says which variable is missing. The quick-start compose passes them as `${VAR:-}` and the production compose through `env_file`, so Compose itself does not stop you: the server does.

---

## Server (required)

| Variable | Description |
|---|---|
| `NODE_ENV` | Set to `production` |
| `PORT` | Server port (default: `3000`) |
| `MONGO_CONNECTION_URL` | MongoDB connection string |
| `REDIS_HOST` | Redis hostname (default: `localhost`) |
| `REDIS_PORT` | Redis port (default: `6379`) |
| `SERVER_URL` | Public URL of the tenant server (default: `http://localhost:4101`). Enterprise single sign-on needs it public and on HTTPS: the WorkOS redirect URI is built from it |
| `APPLICATION_URL` | Public URL of the client app (default: `http://localhost:4100`) |
| `AUTH_SERVER_URL` | Public URL of the auth portal (default: `http://localhost:4103`) |
| `JWT_PASS` | JWT signing secret |
| `DB_ENCRYPTION_KEY` | Database field encryption key |
| `SECRET_KEY` | General application secret |
| `OAUTH2_SECRET` | OAuth2 token secret |

`INSTALLATION_API_KEY` and `INSTALLATION_ID` also appear in the docs' Server table, flagged required there as well.

### What the compose files actually demand

This is the part that decides whether a stack starts, so read it before the tables above.

Both compose files interpolate five secrets as `${VAR:?message}`, which makes Compose abort before starting a container when the variable is unset or empty. **There are no development fallbacks.** The five are:

```text
JWT_PASS  DB_ENCRYPTION_KEY  SECRET_KEY  OAUTH2_SECRET  REDIS_PASSWORD
```

The docs' generate command prints those five and a sixth, `BULLMQ_DASHBOARD_PASSWORD`:

```bash
for i in JWT_PASS DB_ENCRYPTION_KEY SECRET_KEY OAUTH2_SECRET REDIS_PASSWORD BULLMQ_DASHBOARD_PASSWORD; do echo "$i=$(openssl rand -hex 32)"; done
```

The sixth is optional for Compose (`${BULLMQ_DASHBOARD_PASSWORD:-}`), but unset it falls back to `INSTALLATION_API_KEY` and the server warns at every boot. Set it.

> **`REDIS_PASSWORD` is required, not optional.** The Redis table below still describes it as "Password (if required)", which reads as optional and is left over from when the composes had fallbacks. Both composes start Redis with `--requirepass` and pass the same value to the tenant server, so it must be set and identical on both sides. Older published copies of the quick start printed only four secrets and had no line for this one, so a stack built from them aborts with `required variable REDIS_PASSWORD is missing a value`.

How the rest are set in practice:

- `MONGO_CONNECTION_URL` is hard-coded to the bundled Mongo (`mongodb://mongodb:27017/`) in the quick-start compose. In production there is no Mongo container and the value comes from `.env.selfhost` through `env_file` - **omit it there and the server falls back to localhost inside the container and never becomes ready.**
- `REDIS_HOST=redis` / `REDIS_PORT=6379` point at the compose service. The `localhost` default only applies outside that network.
- `SERVER_URL` / `APPLICATION_URL` / `AUTH_SERVER_URL` are mapped from `TENANT_SERVER_URL` / `CLIENT_URL` / `AUTH_URL`. The quick-start compose maps them with localhost fallbacks; the production compose maps them explicitly with no fallback, so all three must be in `.env.selfhost`. Without the mapping the server uses localhost URLs and CORS blocks both frontends.
- The quick-start compose has no `env_file`: a variable reaches `tenant-server` only when its `environment` block names it. It names every variable in the docs' table except `REDIS_DB` and `MAIL_TRACKING_SECRET`, and none of the ones under [Variables named on other pages](#variables-named-on-other-pages), so setting one of those in `.env.selfhost` changes nothing there. The production compose gives `tenant-server` the whole `.env.selfhost` through `env_file`, while `client` and `auth` get only their URL variables.

---

## Client app

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SERVER_URL` | Tenant server URL |
| `NEXT_PUBLIC_DEFAULT_TENANT_SERVER_URL` | Default tenant server URL |
| `NEXT_PUBLIC_INSTALLATION_ID` | Installation ID (for org filtering) |

Both composes set these from `TENANT_SERVER_URL` and `INSTALLATION_ID`; the auth portal takes `NEXT_PUBLIC_SERVER_URL` only.

---

## CORS

| Variable | Description |
|---|---|
| `CORS_WHITELISTED_DOMAINS` | Comma-separated list of allowed origins |

The platform origins (`console.buildbase.app`) are always allowed by default. Both compose files set this to `${CLIENT_URL},${AUTH_URL}`.

What it governs (from the HTTP API's "Base URLs, environments and CORS" page): `/api/v1/*`, `/.well-known/*` and `/org/*` answer **any** origin, so an app's SDK calls never need its origin listed here. The list applies to everything else under `/api` (the organization API), which allows only the server's own URL, BuildBase's apps and, self-hosted, the origins in `CORS_WHITELISTED_DOMAINS`.

---

## Redis

| Variable | Description | Default |
|---|---|---|
| `REDIS_PASSWORD` | Password. Required in practice - see the note above | - |
| `REDIS_DB` | Database number | `0` |

---

## Proxy, logging and the job dashboard

| Variable | Description | Default |
|---|---|---|
| `TRUST_PROXY` | How many proxies sit in front of the server and append to `X-Forwarded-For`. `0` is right when the port is published directly, as in the quick start. The production compose sets `1` for its bundled Nginx. Set it to the number of appending proxies if you put Nginx, a load balancer or Cloudflare in front - too high and every per-IP rate limit is bypassable by a header the caller writes | `0` in the self-hosted image; the quick-start compose sets `0`, production `1` |
| `LOG_LEVEL` | Server log verbosity: `error`, `warn`, `info`, `http`, `verbose`, `debug` or `silly`. Also the New Relic ingest throttle: with `NEW_RELIC_LICENSE_KEY` set, every logged line is ingested, so raise it to `warn` or `error` to cut volume. An unrecognised value is refused at boot and `info` is used | `info` |
| `BULLMQ_DASHBOARD_PASSWORD` | Password for the background-job dashboard at `/api/admin/bullmq`. Unset, it falls back to `INSTALLATION_API_KEY` and the server warns at every boot; set its own value so the two can be rotated apart | - |

---

## Google Cloud and storage

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_AUTH_CLIENT_ID` | Google OAuth client ID (Google vendor + Gmail sender) | - |
| `GOOGLE_AUTH_CLIENT_SECRET` | Google OAuth client secret | - |
| `GOOGLE_STORAGE_ASSETS_BUCKET_NAME` | GCS bucket for file uploads | - |
| `GOOGLE_STORAGE_STAGING_BUCKET_NAME` | GCS bucket browsers upload to directly, before the server checks a file and makes it an asset. Turns on direct uploads up to 100 MB, file fields on forms and uploads by your app's users through the SDK. Unset, every upload goes through the server at 5 MB at most, and form file fields and SDK uploads answer 501. The docs list what the bucket needs: its own bucket in the assets bucket's location, soft delete off, a one-day delete lifecycle rule, CORS allowing PUT from any origin with the signed headers, and credentials that can sign URLs | - |
| `GOOGLE_STORAGE_FINALIZE_TOKEN` | Shared secret in the Pub/Sub push URL for the staging bucket's finalize notifications (`/api/webhooks/storage/finalize?token=...`). Unset answers 404 there, and an upload still completes through its own complete call or the 15-minute sweep | - |
| `GOOGLE_STORAGE_USAGE_LOG_BUCKET` | GCS bucket the assets bucket writes its usage logs to; the hourly bandwidth job reads them. Unset: bandwidth is not measured | - |
| `GOOGLE_STORAGE_USAGE_LOG_PREFIX` | The log object prefix the assets bucket was given (`--log-object-prefix`). Must match, or the bandwidth job finds no logs | `assets` |
| `EXPORTS_BUCKET` | GCS bucket an organization owner's data export is written to and downloaded from. Unset, exports are off and the export routes answer 503. Its own bucket: a 7-day delete lifecycle rule, no retention policy, public access prevention | - |
| `TENANT_STORAGE_GATE` | `off`, `shadow` (log what it would refuse) or `true`. Self-hosted storage has no ceiling, so here it decides only whether a JSON body carrying a `data:` file over 16 KB is refused. Unset follows `TENANT_FEATURE_GATE`, which is off unless set | - |
| `TENANT_STORAGE_BILLING` | Storage billing. No effect on a self-hosted install, where storage is not billed | `off` |
| `TENANT_STORAGE_INTEGRITY` | The weekly check of stored files against asset records. `shadow` logs and changes nothing; `true` also sets aside an unaccounted file older than a day and deletes it 7 days later if still unclaimed; `off` skips it | `shadow` |
| `TENANT_STORAGE_PURGE` | Deleting an organization's files 30 days after its subscription lapsed. A self-hosted organization never counts as lapsed, so in practice no effect | `off` |

---

## Email

| Variable | Description | Default |
|---|---|---|
| `MAIL_TRACKING_SECRET` | Signing key for email open/click tracking links. Derived from `JWT_PASS` when unset; set it to make the tracking key independent of the auth key | - |
| `SENDER_VERIFY_ON_SAVE` | Saving an email sender logs in to its mail server first and refuses credentials the server rejects. Only the literal `false` skips that check; set it only when this server cannot reach your mail host at all | `true` |

There is no `MAILGUN_API_KEY` any more: the docs' variable list, the env template and both composes dropped it. Sign-up codes, password resets and invitations go through the organization's own email sender, set in the console under Messaging, then Sender accounts ([../deploy/quick-start.md](../deploy/quick-start.md) Step 7).

---

## URL safety

| Variable | Description | Default |
|---|---|---|
| `GOOGLE_WEB_RISK_API_KEY` | Google Web Risk key for checking redirect destinations. Unset disables reputation checks; links still work | - |
| `URL_SAFETY_ENABLED` | Master switch. Only the literal `false` turns checks off, and every lookup then returns UNKNOWN | `true` |
| `URL_SAFETY_LOG_ONLY` | Record verdicts without acting on them. Set this true first to measure false positives, because otherwise setting the API key starts refusing malicious destinations straight away | `false` |
| `URL_SAFETY_CLEAN_TTL_SECONDS` | How long a clean verdict may be cached, capped at 86400. A threat verdict honours the expiry Google returns instead | `3600` |
| `WEB_RISK_TIMEOUT_MS` | Timeout for one Web Risk lookup. Lookups are on a background path but must not hang a worker | `5000` |

---

## Sign-in protection

| Variable | Description | Default |
|---|---|---|
| `BREACHED_PASSWORD_CHECK` | Refuse passwords found in known breaches, on register, reset and change. Only the first five characters of the password's SHA-1 hash leave the server (Pwned Passwords range API). Set `off` when the server cannot reach `api.pwnedpasswords.com`, or every password waits out a 2-second timeout | `on` |
| `TURNSTILE_SITE_KEY` | Cloudflare Turnstile site key for this install's own sign-in domain (`AUTH_URL`), used when an org turns bot protection on and has not saved keys of its own. Unset (with the secret) and bot protection stays off unless an org adds its own keys | - |
| `TURNSTILE_SECRET_KEY` | The secret paired with the site key. Only the server reads it, so it needs to reach `challenges.cloudflare.com` | - |
| `SMS_NUMBER_HOURLY_MAX` | Phone sign-in codes sent to one number in an hour, across every org on the install. `DISABLE_RATE_LIMIT` does not switch it off | `5` |
| `SMS_NUMBER_DAILY_MAX` | Codes to one number in a day | `10` |
| `SMS_IP_HOURLY_MAX` | Codes requested from one IP in an hour (stops SMS pumping) | `20` |
| `SMS_IP_DAILY_MAX` | Codes requested from one IP in a day. Each org's own daily cap is a console setting, not a variable | `50` |

---

## Commerce

Selling through Stripe Connect. All closed unless set.

| Variable | Description | Default |
|---|---|---|
| `TENANT_MARKETPLACE` | Kill switch. `on` opens it (non-production environments sell with Stripe test keys only, production may use live keys); `off` keeps it closed; `test` is legacy (test keys only, everywhere). Anything else reads as off | `off` |
| `LIVE_SELLING_PILOT` | `on`: only organizations an admin listed sell with live keys. `off`: the plan, or an admin exception, decides. Only `off` turns it off | `on` |
| `AFFILIATES_PAYPAL` | `on` lets affiliate programs pay out by PayPal from each app owner's own PayPal Business account | `off` |
| `GOOGLE_STORAGE_DELIVERABLES_BUCKET_NAME` | GCS bucket for the files sellers sell, served only through short-lived signed links (turn on public access prevention). Unset, file items answer `FILES_NOT_SET_UP` | - |
| `CLAMAV_HOST` | Host of a ClamAV daemon that scans each seller's file before it can be sold. Unset, files are not scanned and may be sold only in a non-production environment (or while the legacy `TENANT_MARKETPLACE=test` is set). Both composes ship an optional `clamav` service: start it with `--profile scanner` and set `CLAMAV_HOST=clamav` | - |
| `CLAMAV_PORT` | Port of the ClamAV daemon | `3310` |
| `SHIPPING_EASYPOST` | `on` lets an app owner connect their own EasyPost key | `off` |
| `SHIPPING_SHIPPO` | `on` lets an app owner connect their own Shippo token | `off` |

---

## Observability

Telemetry goes to **your own** New Relic account. Unset, which is the default, means nothing is collected or sent.

| Variable | Description |
|---|---|
| `NEW_RELIC_LICENSE_KEY` | Ingest license key for your own account. Unset disables all APM and log telemetry |
| `NEW_RELIC_APP_NAME` | APM application name (defaults to `buildbase-server-selfhost`) |
| `NEW_RELIC_BROWSER_ACCOUNT_ID` | Account ID for browser monitoring of the client and auth frontends, shared across apps |
| `NEW_RELIC_BROWSER_LICENSE_KEY` | Browser license key (`NRJS-...`), shared across apps |
| `NEW_RELIC_BROWSER_APP_ID_CLIENT` | Browser application ID for the client (console) frontend |
| `NEW_RELIC_BROWSER_APP_ID_AUTH` | Browser application ID for the auth frontend |

Where they reach: the quick-start compose maps the server-side pair onto `tenant-server` and the browser three onto `client` and `auth` (as `NEXT_PUBLIC_NEW_RELIC_*`). The production compose gives `tenant-server` the server-side pair through `env_file`, but its `client` and `auth` blocks carry no New Relic variables, so setting the browser three in `.env.selfhost` does not reach the production frontends.

---

## Variables named on other pages

| Variable | Where documented | What it does |
|---|---|---|
| `IP_INFO_MODE` | overview, configuration | Visitor IP addresses go to IPinfo for location lookups unless it is set to `disabled` |
| `READINESS_REDIS_FAIL_OPEN` | production | `true` keeps `/api/ready` answering ready while Redis is down (`"redis": "degraded"`). Off by default |
| `CELL_ID` | production | When set, `/api/ready` also returns `cell` |
| `API_KEY_RATE_LIMIT_MAX`, `ORG_WRITE_RATE_LIMIT_MAX`, `TOKEN_EXCHANGE_PER_MINUTE` | HTTP API, rate limits | A self-hosted install can raise these three code defaults through its environment |
| `DISABLE_RATE_LIMIT` | workspaces, invitations; authentication, phone | Pinned off in a locked build, so the 60-invitations-an-hour limit per workspace holds whatever it says; it never switches the `SMS_*` limits off either |
| `IMAGE_TAG` | configuration | Read by Docker Compose, not the containers; see below |

The server source (`server/src/self-hosted-edition.ts` in the platform repo, not the docs) also refuses to start the self-hosted image with `INTERNAL_API_KEY` or `ORG_IDS` set: the first is the cloud tenant's credential, the second would name organizations no installation was attached to.

---

## Docker images and IMAGE_TAG

| Image | Description | Port | Health check |
|---|---|---|---|
| `buildbaseapp/tenant-server` | Backend API server | 3000 | `GET /api/ready` |
| `buildbaseapp/client` | Web dashboard (Next.js SSR) | 3000 | `GET /` |
| `buildbaseapp/auth` | Auth portal (Next.js) | 3000 | `GET /health` |

All images are multi-arch (`linux/amd64, linux/arm64`) built on **Node.js 22 Alpine**, and `docker pull` selects the right variant automatically. 32-bit ARM (`linux/arm/v7`) is not supported. Note the auth portal's health check is `GET /health`, not `GET /`; the client's is `GET /`.

**Pinning a version.** The `docker-compose.selfhost.yml` in the BuildBase repository names all three images as `:${IMAGE_TAG:-latest}`: set `IMAGE_TAG` in the shell you run `docker compose` from, or in the `--env-file`, to a published tag, and the three run that version; unset, they run `latest`. The compose files on the docs pages (and in this skill) name `latest` directly: to pin them, replace `latest` in the three `image:` lines with a tag. The docs list no tags.

---

## Generating secrets

Every secret should be a unique random string:

```bash
openssl rand -hex 32
```

Or all of them at once, with the six-name command under [What the compose files actually demand](#what-the-compose-files-actually-demand).

---

## Not documented - do not assert these

The docs define what each variable **is** but not its operational behaviour:

- Whether `DB_ENCRYPTION_KEY` can be rotated, or what happens to existing data if it changes. Treat as unknown. Do not tell an operator it is safe or unsafe to rotate.
- The consequences of rotating `JWT_PASS`, `OAUTH2_SECRET` or `SECRET_KEY`. (The Installation API key is the exception: regenerating it in the console keeps the old key working for up to 60 minutes. See [../mental-models/installations.md](../mental-models/installations.md).)
- Value validation rules beyond "unique, random string". The one exception the compose states itself is `DB_ENCRYPTION_KEY`, whose error message asks for 64 hex characters, which is what `openssl rand -hex 32` produces.
- How to configure Google OAuth, the GCS buckets' IAM, or New Relic step by step. The docs name the variables and the bucket settings, not a walkthrough.

The public self-hosted page at [buildbase.app/self-hosted](https://www.buildbase.app/self-hosted) does state that sensitive database fields are encrypted at rest with AES-256-CBC, and mentions per-organization key pairs with key rotation support - but that refers to the central server's ES256 signing keys, not `DB_ENCRYPTION_KEY`. Do not conflate them.

If asked about any of these, say the docs do not cover it and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview).

---

## Read next

- First deploy -> [../deploy/quick-start.md](../deploy/quick-start.md)
- Production -> [../deploy/production.md](../deploy/production.md)
- Diagnostics -> [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
