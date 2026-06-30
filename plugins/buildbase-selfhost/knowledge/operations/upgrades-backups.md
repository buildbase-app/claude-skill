# Operations — Updating (and what the docs say about backups)

What the self-hosted docs actually document for day-2 operations is **updating**. Backups are named as your responsibility but **no procedure is given** — that's flagged below as a gap, not filled in with invented commands.

> **Source (verbatim):** `docs/content/self-hosted/production.mdx` § Updating, and the responsibility matrix in `overview.mdx`.

---

## Updating (documented)

> "Pull the latest images and restart:"

```bash
docker compose -f docker-compose.selfhost.yml pull
docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d
```

What makes this low-disruption in the **production** compose (all from the compose file, not added):
- `tenant-server` runs **`replicas: 2`**.
- `update_config: parallelism: 1, delay: 10s, order: start-first` — a new replica starts before the old one stops.
- An `autoheal=true` label + the `willfarrell/autoheal:1.2.0` service (`AUTOHEAL_INTERVAL=30`) restarts unhealthy containers.

✅ **Verify after updating:** `curl .../api/ready` → `{"ready": true}` (DB + Redis connected); `GET /api/health` for DB status, Redis latency, worker status.

---

## Health checks (documented)

| Endpoint | Purpose |
|---|---|
| `GET /api/ready` | Readiness probe — `{"ready": true}` when DB and Redis are connected |
| `GET /api/health` | Full health check — DB status, Redis latency, worker status |

---

## ⚠️ Backups — documented as your responsibility, but NO procedure given

The overview's responsibility matrix lists **"Your data, backups"** under *You Control*, and the central server "never sees your application data." So **only you can back up your data.** However, the self-hosted docs (overview, quick-start, configuration, production) contain:

- **No `mongodump` / `mongorestore` commands or schedule.**
- **No restore procedure.**
- **No guidance on `DB_ENCRYPTION_KEY` and restores** (e.g. whether a restore needs the original key).
- **No Redis backup guidance** beyond what the compose implies (Redis runs with `--appendonly yes` and a `redis_data` volume — AOF persistence — but the docs don't describe backing it up).

**Do not present standard MongoDB backup commands as if they came from Buildbase.** If a user needs a backup runbook, tell them it isn't in the current self-hosted docs and either (a) point them to general MongoDB/Redis backup practice as *external* guidance, clearly labeled, or (b) ask Buildbase to add it. This is a **documentation gap** — see the gaps summary the skill can surface.

---

## Read next

- The compose that defines replicas/autoheal → [../deploy/production.md](../deploy/production.md)
- The secrets involved (and the undocumented rotation behavior) → [../config/env-reference.md](../config/env-reference.md)
- Diagnostics → [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
