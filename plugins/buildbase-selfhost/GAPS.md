# Self-Hosting Docs — Gaps

Things an operator needs that the self-hosted docs do **not** currently cover. The `buildbase-selfhost` skill is grounded strictly in the four source files below, so each gap is a place where the skill can only say *"not documented"* rather than give an answer.

**Source of truth (the only files the skill draws from):**
- `os/docs/content/self-hosted/overview.mdx` — [docs.buildbase.app/self-hosted/overview](https://docs.buildbase.app/self-hosted/overview)
- `os/docs/content/self-hosted/quick-start.mdx` — [docs.buildbase.app/self-hosted/quick-start](https://docs.buildbase.app/self-hosted/quick-start)
- `os/docs/content/self-hosted/configuration.mdx` — [docs.buildbase.app/self-hosted/configuration](https://docs.buildbase.app/self-hosted/configuration)
- `os/docs/content/self-hosted/production.mdx` — [docs.buildbase.app/self-hosted/production](https://docs.buildbase.app/self-hosted/production)

When a gap is filled in these files, update the matching skill knowledge file (named per row) and remove the "not documented" flag there.

---

## Priority 1 — data-loss / correctness risk

### 1. Backup & restore procedure
- **What's missing:** the responsibility matrix puts *"Your data, backups"* under "You Control", but no procedure exists — no `mongodump`/`mongorestore`, no schedule, no Redis backup, no restore steps, no off-host storage guidance.
- **Why it matters:** the central server holds no copy of customer data; if the operator has no backup, there is no recovery path.
- **Skill file affected:** `knowledge/operations/upgrades-backups.md` (currently flags this as a gap).

### 2. `DB_ENCRYPTION_KEY` lifecycle
- **What's missing:** the config table defines it as "Database field encryption key" and nothing more. Unspecified: can it be rotated? What happens to existing encrypted data if it changes? Does a restore require the *original* key?
- **Why it matters:** if changing the key silently makes existing data unreadable, an operator can destroy their data without warning.
- **Skill file affected:** `knowledge/config/env-reference.md`, `knowledge/operations/upgrades-backups.md`.

### 3. Secret-rotation consequences
- **What's missing:** effects of rotating `JWT_PASS`, `OAUTH2_SECRET`, `SECRET_KEY` (forced re-auth? token/session invalidation? safe or not?).
- **Skill file affected:** `knowledge/config/env-reference.md`.

---

## Priority 2 — operability

### 4. Activation / licensing & central-server connectivity failure states
- **What's missing:** what a wrong or expired `INSTALLATION_API_KEY` produces; how the stack behaves when the central server is **unreachable** (timeout, retry, offline grace period); which exact outbound host/port must be allowed. The host `central.console.buildbase.app` appears only as a diagram label in `configuration.mdx`, never as a stated firewall/egress requirement.
- **Skill file affected:** `knowledge/failure-library/selfhost-mistakes.md`, `knowledge/mental-models/installations.md`.

### 5. External MongoDB connection details
- **What's missing:** production says MongoDB is "external (managed like Atlas, or self-hosted)" but gives no example `MONGO_CONNECTION_URL` with auth, TLS, or replica-set parameters.
- **Skill file affected:** `knowledge/config/env-reference.md`, `knowledge/deploy/production.md`.

### 6. Image tags, upgrades & rollback
- **What's missing:** only `:latest` is shown. No version pinning guidance, no rollback procedure, no migration/breaking-change notes between versions.
- **Skill file affected:** `knowledge/operations/upgrades-backups.md`.

### 7. Logs & monitoring
- **What's missing:** log locations/formats, how to read tenant-server logs, and the exact JSON shape of `GET /api/health` (docs say it returns "DB status, Redis latency, worker status" but don't show the payload).
- **Skill file affected:** `knowledge/failure-library/selfhost-mistakes.md`, `knowledge/deploy/production.md`.

---

## Priority 3 — completeness

### 8. Optional-service setup walkthroughs
- **What's missing:** `GOOGLE_AUTH_CLIENT_ID/SECRET`, `GOOGLE_STORAGE_ASSETS_BUCKET_NAME`, `MAILGUN_API_KEY` are listed as variables, but there's no walkthrough to configure Google OAuth, GCS-backed uploads, or Mailgun email.
- **Skill file affected:** `knowledge/config/env-reference.md`.

### 9. Scaling beyond the fixed 2 replicas
- **What's missing:** the production compose hard-codes `replicas: 2`; no guidance on scaling further, or on sizing MongoDB/Redis for load.
- **Skill file affected:** `knowledge/deploy/production.md`.

### 10. Decommission / data export
- **What's missing:** how to tear down an installation and export data.
- **Skill file affected:** (new file when documented.)

---

## How the skill handles these today

Every file in `knowledge/` is grounded only in the four source `.mdx` files. Where a topic above arises, the skill is instructed (in `SKILL.md` → "What not to do" and per-file "not documented" notes) to say it isn't in the current self-hosted docs and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview) — **never to invent a procedure.**
