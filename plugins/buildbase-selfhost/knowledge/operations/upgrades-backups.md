# Operations - Updating, Migrations and Backups

What the self-hosted docs document for day-2 operations is **updating**: a MongoDB backup first, the new compose file, then a pull and a restart, with database migrations run by the server itself. Backups beyond that one step have **no documented procedure**; that is flagged below as a gap, not filled in with invented commands.

> **Source:** `docs/content/self-hosted/production.mdx` (Updating, Health Checks), `configuration.mdx` (Pinning a version), `quick-start.mdx` (What's next), and `overview.mdx` (the minimum version, the responsibility matrix). The commands are generated output of `packages/shared/src/constants/self-hosted.ts`, copied byte-for-byte.

---

## Contents

- [Updating (documented)](#updating-documented)
- [Database migrations](#database-migrations)
- [Pinning a version](#pinning-a-version)
- [The minimum version the console accepts](#the-minimum-version-the-console-accepts)
- [Overage on Stripe Billing Meters (one-time)](#overage-on-stripe-billing-meters-one-time)
- [Health checks (documented)](#health-checks-documented)
- [Backups - partly documented](#backups---partly-documented)
- [Rollback - not documented](#rollback---not-documented)

---

## Updating (documented)

In the docs' order:

1. **Back up MongoDB** (`mongodump` against your `MONGO_CONNECTION_URL`).
2. **Save the compose file from the docs over yours**: the production compose, or the quick start's if you run the bundled MongoDB ([../deploy/production.md](../deploy/production.md), [../deploy/quick-start.md](../deploy/quick-start.md)). The images are tested with the compose file of their release, and an update can change it. An install made before release 23 needs this step: its bundled MongoDB lacks `CHOWN` and crash-loops on its next restart, and saving the new file and running `up -d` recovers it with the data intact.
3. **Pull the images and restart:**

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost pull
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

What happens to a running stack:

- `tenant-server` has `stop_grace_period: 180s`: the workers run in the server process, the server exits by itself within 150 s, and long jobs hand themselves back as it closes. Compose's default 10 s would kill a running job on every upgrade.
- The **production** compose runs `replicas: 2`, and the `willfarrell/autoheal:1.2.0` service (`AUTOHEAL_INTERVAL=30`) restarts containers labelled `autoheal=true` when they turn unhealthy, waiting `autoheal.stop.timeout=180` seconds so it does not cut the grace period short.

**There is no rolling restart, and the docs never claim one.** An earlier version of this page described an `update_config: order: start-first` block. `deploy.update_config` is a Swarm-mode key that `docker compose up` - the command the docs give - does not implement, so that behaviour was never delivered. Describe updating as a pull and a restart, with a brief interruption.

Check after updating: `curl .../api/ready` returns `{"ready":true,"mongo":"ok","redis":"ready"}`, and the tenant server logs its migration line (below).

---

## Database migrations

The new tenant server runs its pending database migrations by itself as it starts, without holding up readiness, and logs one line when it is done:

```text
[Migrations] boot run: N ran, N already applied, N manual, not run (...)
```

Existing users, sessions and data carry over. Migrations marked manual are never run at boot; the log names them. List them, and run one by name when its release notes ask you to:

```bash
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost exec -T tenant-server node build/migrations/run.js --status
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost exec -T tenant-server node build/migrations/run.js <name>
```

---

## Pinning a version

The compose files on the docs pages name `:latest`. To move between known versions instead of whatever `latest` is today, replace `latest` in the three `image:` lines with a release tag. The `docker-compose.selfhost.yml` in the BuildBase repository does the same through `IMAGE_TAG` (`:${IMAGE_TAG:-latest}`), which Docker Compose reads from the shell or the `--env-file`; see [../config/env-reference.md](../config/env-reference.md). The docs do not list the published tags.

---

## The minimum version the console accepts

BuildBase can set a minimum version for the tenant server. If your installation reports an older image, or none, the console will not open its organizations until you pull the newer image and restart; it names the version to update to. Only the console checks this: the installation keeps serving your end users meanwhile. The installation's page in the console shows the version it last reported.

---

## Overage on Stripe Billing Meters (one-time)

Overage now reaches the Stripe invoice through Billing Meters instead of Stripe's legacy usage records. Subscriptions created before the update keep billing through the legacy prices until they are moved, so if any of your plans bill overage, run the migration once after the new image is up. It is a dry run by default: it lists the plan versions and subscriptions it would move and writes nothing. Read the list, then run it again with `--apply`. It is safe to interrupt and run again, and makes a few Stripe calls per subscription, so run it off-peak.

```bash
# Dry run: lists what would move, writes nothing
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost exec -T tenant-server node build/migrations/migrate-overage-to-meters.js

# Move them
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost exec -T tenant-server node build/migrations/migrate-overage-to-meters.js --apply
```

---

## Health checks (documented)

| Endpoint | Purpose |
|---|---|
| `GET /api/ready` | Readiness probe. `200` with `{"ready": true, "mongo": "ok", "redis": "ready"}` when MongoDB and Redis are connected (plus `cell` when `CELL_ID` is set); `503` with `"ready": false` and the state of each connection when one is down |
| `GET /api/health` | `{"status", "timestamp"}`, `200` or `503` on the same condition. With `x-internal-api-key: <INSTALLATION_API_KEY>`, the full report: database and Redis state, Redis latency, tenant connections and pool sizes, process memory and uptime |

`READINESS_REDIS_FAIL_OPEN=true` keeps the probe answering ready while the shared Redis is down (`"redis": "degraded"`), so a Redis outage does not take every replica out at once. Off by default. Detail: [../deploy/production.md](../deploy/production.md).

---

## Backups - partly documented

The overview's responsibility matrix lists **"Your data, backups, security"** under *You Control*, and your end users' accounts and application data stay in your own MongoDB. So **only you can back up your data.** What the docs now say:

- **Documented:** back up MongoDB with `mongodump` against your `MONGO_CONNECTION_URL` before an update.
- **Not documented:** the `mongodump` flags, a schedule, off-host storage, a restore procedure (`mongorestore` or otherwise), whether a restore needs the original `DB_ENCRYPTION_KEY`, and any Redis backup beyond what the compose implies (Redis runs with `--appendonly yes` on the `redis_data` volume, AOF persistence, but the docs do not describe backing it up). Uploaded files live in the GCS bucket you own; the docs say nothing about backing that up either.

Give the documented step as Buildbase guidance. Anything past it is general MongoDB, Redis or GCS practice: label it as external, or tell the operator it is not in the current self-hosted docs.

Related and documented: an organization owner's data export is written to `EXPORTS_BUCKET` (unset, exports are off and the export routes answer 503), and deleting an installation in the console unassigns its organizations without deleting their data. Neither is a backup.

---

## Rollback - not documented

Pinning a tag lets you choose which version to run, but the docs say nothing about going back to an older image after the newer one ran its migrations at boot. Do not tell an operator a downgrade is safe. The `mongodump` the docs ask for before an update is the copy they would fall back on, but how to restore it is not documented either.

---

## Read next

- The compose that defines replicas and autoheal -> [../deploy/production.md](../deploy/production.md)
- The secrets involved (and the undocumented rotation behaviour) -> [../config/env-reference.md](../config/env-reference.md)
- Diagnostics -> [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
