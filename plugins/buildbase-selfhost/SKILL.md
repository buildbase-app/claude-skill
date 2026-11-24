---
name: buildbase-selfhost
description: |-
  Expert guide for DEPLOYING and OPERATING the self-hosted Buildbase platform on
  your own infrastructure (Docker Compose, MongoDB, Redis, Nginx).

  TRIGGER this skill when the user mentions: self-hosting/self-hosted Buildbase,
  on-premises Buildbase, docker-compose.selfhost.yml, .env.selfhost,
  nginx-lb.conf, INSTALLATION_API_KEY, INSTALLATION_ID, tenant-server,
  buildbaseapp/tenant-server, buildbaseapp/client, buildbaseapp/auth, the
  central server, an "Installation", DB_ENCRYPTION_KEY, IMAGE_TAG,
  self-hosted-starter, or "running Buildbase myself / on my own infra".

  Also trigger for deploying, upgrading, migrating or backing up a Buildbase
  stack, or operator errors like "/api/ready is false", "installation shows
  disconnected", "tenant server won't start", "Test connection failed".

  SKIP this skill, and use the `buildbase` SDK skill instead, when the user is
  writing APPLICATION code (SaaSOSProvider, hooks, gates, billing, the HTTP API).
  Self-hosting = running the platform; that skill = building against it.
---

# Buildbase Self-Hosting

You help operators **run the Buildbase platform on their own infrastructure** - deploy it, configure it, harden it for production, upgrade it, and back it up. This is a DevOps/infra task, not application development. Your job is to transfer operational expertise: explain the architecture first, give exact commands second, and **never invent component names, ports, env vars, or behaviour** beyond what the docs document.

## Before you answer anything

**Are they deploying, or integrating?** If the user is writing app code (`SaaSOSProvider`, hooks, gates, billing, webhooks, the HTTP API), this is the wrong skill - route them to the **`buildbase`** SDK-integration skill. This skill stops at the tenant server's edge; the crossover is the `serverUrl` swap, and which SDK version suits the server release, in [knowledge/handoff/integrating-against-self-host.md](knowledge/handoff/integrating-against-self-host.md).

**Establish the architecture first.** Almost every operator confusion dissolves once they understand the four-component split. Read [knowledge/architecture/four-components.md](knowledge/architecture/four-components.md) before giving deploy steps.

**Route to the right knowledge.** Use the table below. Don't answer config or failure questions from memory - open the file.

---

## What self-hosting Buildbase is

Self-hosted mode runs the Buildbase platform on **your** cloud, data center, or on-prem hardware. The documented split:

- **One component stays Buildbase-managed** - the **Central Server** (organization management, admin authentication via Google OAuth, installation licensing, ES256 key management). Your end users' accounts and application data stay in your own MongoDB.
- **You run three services** - **Tenant Server** (`buildbaseapp/tenant-server`, your data + API), **Client App** (`buildbaseapp/client`, the dashboard), **Auth Portal** (`buildbaseapp/auth`) - plus your own **MongoDB 7+** and **Redis 7+**.

**Honest framing, in the docs' words:** "The installation stays connected to BuildBase: the central server signs your team in to the console, manages your organizations, receives a status check-in every five minutes and is told about plan changes." Visitor IPs go to IPinfo unless `IP_INFO_MODE` is `disabled`, and uploaded files go to a Google Cloud Storage bucket the operator owns. So the stack needs **outbound connectivity to the central server**. If BuildBase cannot be reached, end users are unaffected; only console sign-in waits. Don't call it "air-gapped" - the docs never do.

**Official resources** (point operators here; don't guess beyond them):
- Dashboard: **https://console.buildbase.app** - create the Installation (Account, then Installations) and the self-hosted organization here
- Self-hosting docs: **https://docs.buildbase.app/self-hosted** (overview, quick-start, configuration, production)
- The [self-hosted starter](https://github.com/buildbase-app/self-hosted-starter): the same Compose stack as a repo, linked from the docs

---

## How to route questions

| When to load | File |
|---|---|
| **First**, before any deploy advice - the four-component split, outbound calls, responsibility matrix | [knowledge/architecture/four-components.md](knowledge/architecture/four-components.md) |
| The Installation: licence, allowance, licensing states, key regeneration, minimum version | [knowledge/mental-models/installations.md](knowledge/mental-models/installations.md) |
| "How do I deploy?" - zero to running stack, with a check after each step | [knowledge/deploy/quick-start.md](knowledge/deploy/quick-start.md) |
| Production - Nginx LB, replicas, TLS, health checks, Enterprise SSO requirements | [knowledge/deploy/production.md](knowledge/deploy/production.md) |
| "What does env var X do?" / config reference | [knowledge/config/env-reference.md](knowledge/config/env-reference.md) |
| Updating, migrations, pinning a version, what the docs say about backups | [knowledge/operations/upgrades-backups.md](knowledge/operations/upgrades-backups.md) |
| **First** when something won't start, connect or open | [knowledge/failure-library/selfhost-mistakes.md](knowledge/failure-library/selfhost-mistakes.md) |
| "Now how do I point my app at this?" - the seam to the SDK skill | [knowledge/handoff/integrating-against-self-host.md](knowledge/handoff/integrating-against-self-host.md) |

---

## Core mental models

Establish these before showing commands.

**Four components, one of them managed.** Central Server (Buildbase) and your Tenant Server + Client + Auth + Mongo + Redis. The central server holds licensing, keys and your team's console sign-in, never your end users' data. Full detail: [four-components.md](knowledge/architecture/four-components.md).

**An Installation = one running stack, and its ID and API key are its licence.** You create it under Account, then Installations, and get `INSTALLATION_API_KEY` (shown once) + `INSTALLATION_ID`. One Installation can host many orgs; how many installations you may run belongs to your own account's self-hosting plan. Without the two values the tenant server does not start. Detail: [installations.md](knowledge/mental-models/installations.md).

**`/api/ready` is the source of truth.** It answers `200` with `{"ready": true, "mongo": "ok", "redis": "ready"}` when MongoDB and Redis are connected, and `503` with `"ready": false` and the state of each connection when one is down. `/api/health` with `x-internal-api-key: <INSTALLATION_API_KEY>` gives the full report.

**The compose file is part of the release.** The images are tested with the compose file of their release: an update starts by saving the current compose file over the old one, then `pull` and `up -d`. The server runs its own migrations at boot.

**The app side barely changes.** Building against a self-hosted stack is the managed product with `serverUrl` = your tenant server. A self-hosted server is only as new as its image, and the SDK degrades on an older one as its README's "Server compatibility" table says. Everything else is the `buildbase` skill.

---

## Security & operations notes (grounded in docs)

- **Five secrets are required, and the stack will not start without them.** `JWT_PASS`, `DB_ENCRYPTION_KEY`, `SECRET_KEY`, `OAUTH2_SECRET` and `REDIS_PASSWORD`, each a unique `openssl rand -hex 32` value. Both composes interpolate them as `${VAR:?message}`, so Compose aborts before starting a container when one is missing. The docs' generate command also prints a sixth, `BULLMQ_DASHBOARD_PASSWORD`: optional for Compose, but unset it falls back to `INSTALLATION_API_KEY` and the server warns at every boot. Give the operator the six-name command.
- **Backups are your responsibility**, and the docs now document one step: back up MongoDB with `mongodump` against `MONGO_CONNECTION_URL` before an update. There is still no restore procedure, schedule or Redis backup. Don't invent them as Buildbase guidance. See [upgrades-backups.md](knowledge/operations/upgrades-backups.md).
- **Encryption-key / secret-rotation behaviour is NOT documented.** Don't tell operators whether rotating `DB_ENCRYPTION_KEY`, `JWT_PASS`, `OAUTH2_SECRET` or `SECRET_KEY` is safe or destructive. (The Installation API key is the exception: regenerating it keeps the old key working for up to 60 minutes.) See [env-reference.md](knowledge/config/env-reference.md).
- **`TRUST_PROXY` counts appending proxies.** `0` in the quick start (port published directly), `1` in production (its Nginx). Too low behind a proxy and every caller shares one rate-limit bucket; too high and callers pick their own address.
- **Use real public URLs in production.** The docs require a domain + SSL cert. BuildBase never connects to a private address itself, so the features where its servers call yours need a public HTTPS URL; Enterprise SSO also needs `SERVER_URL` public on HTTPS and outbound HTTPS to `api.workos.com` (through the app owner's own WorkOS account).

Detail: [env-reference.md](knowledge/config/env-reference.md), [upgrades-backups.md](knowledge/operations/upgrades-backups.md), [selfhost-mistakes.md](knowledge/failure-library/selfhost-mistakes.md).

---

## First deploy - the order matters

Don't let an operator skip ahead. The sequence (full version with a check after each step: [quick-start.md](knowledge/deploy/quick-start.md)):

1. **Create the Installation** in the dashboard (Account, then Installations, Create installation) and copy `INSTALLATION_API_KEY` + `INSTALLATION_ID`. A new account offers Shared cloud only; self-hosting is enabled by support.
2. **`.env.selfhost`** - Installation values, public URLs, five required `openssl rand -hex 32` secrets plus `BULLMQ_DASHBOARD_PASSWORD`.
3. **Save `docker-compose.selfhost.yml`** (and `nginx-lb.conf` for production) - both are reproduced verbatim from the docs in [quick-start.md](knowledge/deploy/quick-start.md) / [production.md](knowledge/deploy/production.md).
4. **`docker compose -f docker-compose.selfhost.yml --env-file .env.selfhost up -d`**.
5. **Verify** - `docker compose ... ps`, then `curl .../api/ready` returns `{"ready":true,"mongo":"ok","redis":"ready"}`.
6. **Create the self-hosted organization** on the installation (it shows Connected once the server checks in), then its setup: server URL, Test connection, Complete setup.
7. **Let people sign in** - in the console, an email sender (Messaging, then Sender accounts), a sign-in method, and that method enabled on the app.

Production adds Nginx + 2 replicas + TLS + hardening **on top of** a working quick-start, not instead of it: [production.md](knowledge/deploy/production.md).

---

## System requirements (state these up front)

Documented requirements (overview + production docs):

| | Value |
|---|---|
| OS | Linux (Ubuntu 20.04+ recommended) |
| RAM | 2 GB minimum (production docs say 2 GB+) |
| vCPU | 2 minimum (production docs say 2 vCPU+) |
| CPU architecture | x86-64 (`amd64`) or 64-bit ARM (`arm64`); images are multi-arch, Node.js 22 Alpine. 32-bit ARM unsupported |
| Docker | Engine 20+, Compose v2 |
| MongoDB | 7+ (bundled in quick-start; **external** like Atlas for production) |
| Redis | 7+ (bundled in quick-start) |
| Network | Public IP/domain, ports 80/443 for production; domain + SSL cert |
| Enterprise SSO (optional) | Public HTTPS `SERVER_URL`, outbound HTTPS to `api.workos.com`; an ingress in front must forward `allowed-company-ids` unchanged |

> The production compose sets per-service memory *limits* that sum to about 3 GB (two 1024M replicas plus Redis, client, auth, Nginx and autoheal), and the optional ClamAV scanner adds 3072M when its `scanner` profile runs. Size the host with headroom. (That sum is arithmetic on the compose limits, not a separately documented figure.)

---

## What not to do

- Do **not** invent compose-file contents, env vars, ports, error strings, or procedures. The real `.env.selfhost`, `docker-compose.selfhost.yml`, and `nginx-lb.conf` are reproduced verbatim in the deploy files; if a detail isn't in the docs, say so and point to [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview).
- Do **not** tell an operator to set `MAILGUN_API_KEY`: it is gone from the docs. Email goes through each organization's own sender in the console.
- Do **not** state whether rotating `DB_ENCRYPTION_KEY` (or other secrets) is safe or destructive - the docs don't cover it. Flag it as unknown.
- Do **not** present restore commands (e.g. `mongorestore`), schedules or Redis backups as Buildbase guidance - the docs document only `mongodump` before an update. Offer general practice only if clearly labelled as external.
- Do **not** promise a rollback or a zero-downtime update - neither is documented, and the server migrates its database at boot.
- Do **not** quote a self-hosting price - the docs say it is arranged with BuildBase, per installation.
- Do **not** claim self-hosting is "air-gapped" - describe the documented central-server connection and outbound calls instead.
- Do **not** re-explain SDK/app integration here - route to the `buildbase` skill via [integrating-against-self-host.md](knowledge/handoff/integrating-against-self-host.md).
- Do **not** give production hardening to someone whose quick-start `/api/ready` isn't true yet - fix the basics first.

---

## Reference Library

**Architecture & mental models**
- `knowledge/architecture/four-components.md` - the central/tenant/client/auth split, the connection diagram, the outbound calls, images, requirements, responsibility matrix
- `knowledge/mental-models/installations.md` - Installation = one stack and its licence; allowance, the installation page's actions, licensing states, minimum version

**Deploy**
- `knowledge/deploy/quick-start.md` - zero to running; the real `.env.selfhost` + `docker-compose.selfhost.yml` verbatim, a check after each step, through first sign-in
- `knowledge/deploy/production.md` - the real production compose + `nginx-lb.conf` verbatim; Nginx LB and its rate-limit zones, 2 replicas, TLS, health checks, Enterprise SSO requirements

**Config & operations**
- `knowledge/config/env-reference.md` - every env var exactly as documented, grouped by purpose; what the composes demand; an explicit "not documented" section
- `knowledge/operations/upgrades-backups.md` - the documented update procedure, migrations at boot, pinning a version, the minimum version, the one documented backup step and what is still missing

**Diagnosis & handoff**
- `knowledge/failure-library/selfhost-mistakes.md` - diagnostics that follow directly from documented behaviour and compose comments, plus a list of what the docs do **not** cover
- `knowledge/handoff/integrating-against-self-host.md` - the `serverUrl` change, which SDK version suits the server release, and the hand-off to the `buildbase` SDK skill

---

**Keywords**: Buildbase self-hosted, self-hosting, on-premises, on-prem, Docker Compose, docker-compose.selfhost.yml, .env.selfhost, nginx-lb.conf, self-hosted-starter, INSTALLATION_API_KEY, INSTALLATION_ID, tenant-server, buildbaseapp/tenant-server, buildbaseapp/client, buildbaseapp/auth, central server, Installation, DB_ENCRYPTION_KEY, JWT_PASS, OAUTH2_SECRET, SECRET_KEY, MONGO_CONNECTION_URL, REDIS_PASSWORD, BULLMQ_DASHBOARD_PASSWORD, CORS_WHITELISTED_DOMAINS, TRUST_PROXY, IMAGE_TAG, LOG_LEVEL, READINESS_REDIS_FAIL_OPEN, IP_INFO_MODE, MongoDB, Redis, Nginx, autoheal, ClamAV, /api/ready, /api/health, migrations, certbot, Caddy, data sovereignty, serverUrl, TENANT_SERVER_URL, arm64, Apple Silicon, Graviton, NODE_OPTIONS, __NEXT_PUBLIC_SERVER_URL__, NEW_RELIC_LICENSE_KEY, URL_SAFETY_ENABLED, GOOGLE_WEB_RISK_API_KEY, GOOGLE_STORAGE_STAGING_BUCKET_NAME, EXPORTS_BUCKET, BREACHED_PASSWORD_CHECK, TURNSTILE_SITE_KEY.
