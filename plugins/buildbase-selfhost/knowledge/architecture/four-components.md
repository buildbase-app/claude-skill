# Architecture - How Self-Hosted Works

Self-hosting Buildbase uses a **split architecture**: you host three services; Buildbase manages one. Understanding the split explains the data-sovereignty story and why you still need a Buildbase account.

> **Source:** `docs/content/self-hosted/overview.mdx` and the architecture diagram in `configuration.mdx` -> [docs.buildbase.app/self-hosted/overview](https://docs.buildbase.app/self-hosted/overview). Every relationship below is taken from the docs - nothing is inferred.

---

## Contents

- [The split](#the-split-docs-wording)
- [The documented connections](#the-documented-connections)
- [Docker images](#docker-images)
- [Requirements](#requirements-docs-table)
- [What you control vs. what we control](#what-you-control-vs-what-we-control-docs-table)

---

## The split (docs wording)

> "Self-hosted mode lets you run the BuildBase platform on your own infrastructure - your cloud, your data center, or on-premises. You host three services (tenant server, client app, and auth portal) while we manage the central server that handles licensing, organization management, and admin authentication."

- **Central Server** - *Managed by BuildBase.* Handles organization management, admin authentication (Google OAuth), installation licensing, and ES256 key management. **You never host this.**
- **Tenant Server** - *Hosted by you.* Stores and processes all your organization's data - users, emails, workflows, subscriptions, and more.
- **Client App** - *Hosted by you.* The web dashboard your team uses to manage content and data.
- **Auth Portal** - *Hosted by you.* The authentication pages for your app users (login, signup, password reset).

Plus the two data stores you run: **MongoDB** (your data) and **Redis** (sessions & cache). The composes add infrastructure around them - Nginx and autoheal in production, and an optional ClamAV scanner in both - but those are not BuildBase components.

> "Your end users' accounts and application data stay in your own MongoDB. The installation stays connected to BuildBase: the central server signs your team in to the console, manages your organizations, receives a status check-in every five minutes and is told about plan changes. Visitor IP addresses are sent to IPinfo for location lookups unless IP_INFO_MODE is set to disabled, and uploaded files go to a Google Cloud Storage bucket you own."

---

## The documented connections

This is a faithful rendering of the docs' mermaid diagram - these exact arrows are what the docs show:

```
   Your Infrastructure                          BuildBase (managed)
   ┌────────────────────────────────┐           ┌─────────────────────────────┐
   │  Client App  (app.yourco.com)  │           │  Central Server             │
   │  Auth Portal (auth.yourco.com) │           │  central.console.buildbase  │
   │  Tenant Server (api.yourco.com)│           │  • Org management           │
   │       │            │           │           │  • Admin auth · ES256 keys  │
   │       ▼            ▼           │           │  • Installation keys        │
   │   MongoDB        Redis         │           │  • Licensing                │
   └────────────────────────────────┘           └─────────────────────────────┘

   client      ── API calls (HTTPS) ──▶  tenant server
   auth portal ── Auth flows         ──▶  tenant server
   tenant server ── HMAC-signed API  ──▶  central server
   client      ── Org auth (JWT)     ──▶  central server
   tenant server ─▶ MongoDB     tenant server ─▶ Redis
```

**What this means for connectivity:** the stack requires **outbound connectivity to the central server** - it is not a fully isolated or offline deployment. The docs do not use the term "air-gapped"; they describe these connections. What happens when the central server cannot be reached is now documented: your end users are unaffected (sign-in, sessions and your app keep working), existing console sessions keep working, and signing in to the console again waits for BuildBase. The full licensing table is in [../mental-models/installations.md](../mental-models/installations.md).

Other outbound calls the docs name, each tied to a feature:

| Destination | When | Source |
|---|---|---|
| IPinfo | Visitor location lookups, unless `IP_INFO_MODE` is `disabled` | overview |
| Your Google Cloud Storage bucket | Uploaded files | overview |
| `api.pwnedpasswords.com` | `BREACHED_PASSWORD_CHECK` (on by default) | configuration |
| `challenges.cloudflare.com` | Turnstile bot protection, when its keys are set | configuration |
| `api.workos.com` | Enterprise SSO through the app owner's own WorkOS account | overview requirements |
| Your own New Relic account | Only when `NEW_RELIC_*` is set | configuration |
| The internet, for ClamAV signatures | Only when the optional `scanner` profile runs | compose comments |

---

## Docker images

Three official images on Docker Hub. All are multi-arch (`linux/amd64, linux/arm64`) built on **Node.js 22 Alpine**; `docker pull` picks the right variant. 32-bit ARM (`linux/arm/v7`) is not supported: MongoDB 7 does not publish 32-bit ARM builds.

| Image | Description | Port | Health check |
|---|---|---|---|
| `buildbaseapp/tenant-server` | Backend API server | 3000 | `GET /api/ready` |
| `buildbaseapp/client` | Web dashboard (Next.js SSR) | 3000 | `GET /` |
| `buildbaseapp/auth` | Auth portal (Next.js) | 3000 | `GET /health` |

(From `configuration.mdx`. Inside the container each listens on **3000**; the compose files map host ports `4100`/`4101`/`4103`. In production the tenant server's host port goes to Nginx on 8080 instead.) The docs' compose files name `:latest`; pinning a tag is in [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

---

## Requirements (docs table)

| Requirement | Details |
|---|---|
| **Server** | Linux (Ubuntu 20.04+ recommended), 2 GB RAM, 2 vCPU minimum |
| **CPU architecture** | x86-64 (`amd64`) or 64-bit ARM (`arm64`). Apple Silicon, AWS Graviton, Ampere and Raspberry Pi 4/5 on a 64-bit OS all work |
| **Docker** | Docker Engine 20+ and Docker Compose v2 |
| **Database** | MongoDB 7+ (included in quick start, or bring your own) |
| **Redis** | Redis 7+ (included in quick start) |
| **Network** | Public IP or domain name with ports 80/443 for production |
| **Enterprise SSO** (optional) | A public HTTPS `SERVER_URL` and outbound HTTPS to `api.workos.com`; no inbound connection from WorkOS. Any ingress in front must forward the `allowed-company-ids` header unchanged. Detail: [../deploy/production.md](../deploy/production.md) |

---

## What You Control vs. What We Control (docs table)

| You Control | We Control |
|---|---|
| Tenant server, client, auth hosting | Central server hosting |
| Your MongoDB and Redis | Installation API key provisioning |
| Your data, backups, security | Organization management & licensing |
| Custom domains, SSL, network | ES256 signing keys |
| Scaling, replicas, load balancing | Admin authentication (Google OAuth) |
| Environment variables, secrets | Platform updates & security patches |

**Note the docs put "backups" squarely in your column** - and document only one backup step (`mongodump` before an update). See [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

---

## Read next

- The Installation concept -> [../mental-models/installations.md](../mental-models/installations.md)
- Get a stack running -> [../deploy/quick-start.md](../deploy/quick-start.md)
- Integrate your app against it -> [../handoff/integrating-against-self-host.md](../handoff/integrating-against-self-host.md)
