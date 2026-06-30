# Architecture — How Self-Hosted Works

Self-hosting Buildbase uses a **split architecture**: you host three services; Buildbase manages one. Understanding the split explains the data-sovereignty story and why you still need a Buildbase account.

> **Source (verbatim):** `docs/content/self-hosted/overview.mdx` and the architecture diagram in `configuration.mdx` → [docs.buildbase.app/self-hosted/overview](https://docs.buildbase.app/self-hosted/overview). Every relationship below is taken from the docs' own diagram — nothing is inferred.

---

## The split (docs wording)

> "Self-hosted mode lets you run the BuildBase platform on your own infrastructure — your cloud, your data center, or on-premises. You host three services (tenant server, client app, and auth portal) while we manage the central server that handles licensing, organization management, and admin authentication."

- **Central Server** — *Managed by BuildBase.* Handles organization management, admin authentication (Google OAuth), installation licensing, and ES256 key management. **You never host this.**
- **Tenant Server** — *Hosted by you.* Stores and processes all your organization's data — users, emails, workflows, subscriptions, and more.
- **Client App** — *Hosted by you.* The web dashboard your team uses to manage content and data.
- **Auth Portal** — *Hosted by you.* The authentication pages for your app users (login, signup, password reset).

Plus the two data stores you run: **MongoDB** (your data) and **Redis** (sessions & cache).

> "Your data stays on your infrastructure. The central server only handles authentication tokens and organization metadata — it never sees your application data."

---

## The documented connections (from the architecture diagram)

This is a faithful rendering of the docs' mermaid diagram — these exact arrows are what the docs show:

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

**What this means for connectivity:** the diagram shows the **tenant server makes HMAC-signed API calls to the central server**, and the **client authenticates orgs via JWT against the central server**. So your stack requires **outbound connectivity to the central server** — it is not a fully isolated/offline deployment. (The docs do not use the term "air-gapped"; they describe these specific connections.)

---

## Docker Images

Three official images on Docker Hub — all `linux/amd64`, Node.js 20 Alpine:

| Image | Description | Port | Health check |
|---|---|---|---|
| `buildbaseapp/tenant-server` | Backend API server | 3000 | `GET /api/ready` |
| `buildbaseapp/client` | Web dashboard (Next.js SSR) | 3000 | `GET /` |
| `buildbaseapp/auth` | Auth portal (Next.js) | 3000 | `GET /` |

(From `configuration.mdx`. Inside the container each listens on **3000**; the compose files map host ports `4100`/`4101`/`4103`.)

---

## Requirements (docs table)

| Requirement | Details |
|---|---|
| **Server** | Linux (Ubuntu 20.04+ recommended), 2 GB RAM, 2 vCPU minimum |
| **Docker** | Docker Engine 20+ and Docker Compose v2 |
| **Database** | MongoDB 7+ (included in quick start, or bring your own) |
| **Redis** | Redis 7+ (included in quick start) |
| **Network** | Public IP or domain name with ports 80/443 for production |

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

**Note the docs put "backups" squarely in your column** — but they do **not** provide a backup procedure. See the gap note in [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

---

## Read next

- The Installation concept → [../mental-models/installations.md](../mental-models/installations.md)
- Get a stack running → [../deploy/quick-start.md](../deploy/quick-start.md)
- Integrate your app against it → [../handoff/integrating-against-self-host.md](../handoff/integrating-against-self-host.md)
