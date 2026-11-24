# Mental Model - The Installation

The **Installation** is the unit that ties a self-hosted stack to Buildbase's central server, and its ID and API key are its licence. Everything below is from the overview docs - no added behaviour.

> **Source:** `docs/content/self-hosted/overview.mdx` (Licensing and the connection to BuildBase, Installations, Your installation allowance) -> [docs.buildbase.app/self-hosted/overview](https://docs.buildbase.app/self-hosted/overview).

---

## Contents

- [What an Installation is](#what-an-installation-is-docs-wording)
- [When to create more than one](#when-to-create-more-than-one-docs-list)
- [Where to manage them, and what the page does](#where-to-manage-them-and-what-the-page-does)
- [The allowance](#the-allowance)
- [Licensing states](#licensing-states)
- [The minimum version](#the-minimum-version)
- [How it connects](#how-it-connects)

---

## What an Installation is (docs wording)

> "An **Installation** is a self-hosted server instance - one Docker Compose stack running on your infrastructure."

Each installation:
- **Gets a unique API key** for secure communication with the central server.
- **Can serve multiple organizations** (e.g. different teams, projects, or clients).
- **Has its own database, Redis, and server configuration.**

So the mapping is: **one Installation = one Docker Compose stack**, and that one stack can host **many orgs**. You get two values for it from the dashboard - `INSTALLATION_API_KEY` and `INSTALLATION_ID` (see [../config/env-reference.md](../config/env-reference.md)). The key is shown once.

The order matters: create the installation first, start the stack, and create the self-hosted organization only once the installation has checked in ([../deploy/quick-start.md](../deploy/quick-start.md) Steps 1 and 6).

---

## When to create more than one (docs list)

- **By region** - EU Production, US Production
- **By environment** - Production, Staging
- **Multiple orgs on one server** - simplicity for smaller deployments
- **Dedicated per org** - maximum isolation and throughput

---

## Where to manage them, and what the page does

Installations are managed from the [BuildBase Dashboard](https://console.buildbase.app) under **Account, then Installations**. On an installation's page you can:

- **Assign an organization**, or **Detach** one. Assigning moves it off any other installation. If the two installations use different MongoDB databases, the organization starts on the new one without its data until you migrate it (how to migrate it is not documented). On the same MongoDB and Redis, the move needs no migration.
- **Reattach a detached organization.** A self-hosted organization on no installation runs nowhere: the console will not open it, and its users reach it again only once it is attached. The Installations page lists it under **Detached organizations** with a **Reattach** button.
- **Regenerate the API key.** The old key keeps working for a grace period of up to 60 minutes, while you update `.env.selfhost`. The new key is shown once.
- **Test connection** to the server URL, and see the connection state and the version the installation last reported.
- **Delete the installation.** Its key stops working at once and its organizations are unassigned. Their data is not deleted.

---

## The allowance

How many installations you can run, and how many organizations each can hold, depends on the self-hosting plan on **your own account**: self-hosting is licensed per installation, and the allowance belongs to you, not to an organization. The Installations page shows it as "n of N installations, up to M organizations on each", and creating one past it is refused. Self-host is priced per installation and arranged by talking to BuildBase; at the limit, the page links to **Account > Billing**, or says to contact support where no plan sells more. The docs give no price; do not quote one.

A new account offers **Shared cloud** only. If **Self-hosted** is not among the hosting options, the account needs self-hosting enabled by support.

---

## Licensing states

| State | Your end users | Your team in the console |
|---|---|---|
| No `INSTALLATION_ID` or `INSTALLATION_API_KEY` | The tenant server does not start, and says which variable is missing | - |
| Wrong or regenerated key | Unaffected | The server cannot check in or read its organizations from BuildBase, and the installation shows as disconnected. It logs `[CentralAPI] central refused ...` once, and once more when accepted again. Put the current key in `.env.selfhost` and restart |
| BuildBase cannot be reached | Unaffected: sign-in, sessions and your app keep working | Existing sessions keep working; signing in again waits for BuildBase |
| Self-hosting plan lapsed | Unaffected | Opening the organization can be refused, with a message saying to renew |

---

## The minimum version

BuildBase can set a minimum version for the tenant server. If your installation reports an older image, or none, the console won't open its organizations until you pull the newer image and restart; it names the version to update to. Only the console checks this: the installation keeps serving your end users meanwhile. Updating: [../operations/upgrades-backups.md](../operations/upgrades-backups.md).

---

## How it connects

The installation stays connected to BuildBase: the central server signs your team in to the console, manages your organizations, receives a **status check-in every five minutes** and is told about plan changes. The unique API key is what the **tenant server** uses for its **HMAC-signed API** calls to the central server (per the diagram in [../architecture/four-components.md](../architecture/four-components.md)). The central server handles installation **licensing** and **ES256 key management**; your end users' accounts and application data stay in your own MongoDB.

> The docs do not name the outbound host and port to allow for the check-in. `central.console.buildbase.app` appears only as a label in the configuration page's architecture diagram; do not present it as a documented firewall rule.

---

## Read next

- The components this Installation runs -> [../architecture/four-components.md](../architecture/four-components.md)
- Create one and deploy -> [../deploy/quick-start.md](../deploy/quick-start.md)
- The two Installation env values -> [../config/env-reference.md](../config/env-reference.md)
- What a disconnected installation looks like -> [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md)
