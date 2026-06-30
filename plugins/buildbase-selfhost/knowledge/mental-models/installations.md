# Mental Model — The Installation

The **Installation** is the unit that ties a self-hosted stack to Buildbase's central server. Everything below is from the overview docs — no added behavior.

> **Source (verbatim):** `docs/content/self-hosted/overview.mdx` § Installations → [docs.buildbase.app/self-hosted/overview](https://docs.buildbase.app/self-hosted/overview).

---

## What an Installation is (docs wording)

> "An **Installation** is a self-hosted server instance — one Docker Compose stack running on your infrastructure."

Each installation:
- **Gets a unique API key** for secure communication with the central server.
- **Can serve multiple organizations** (e.g. different teams, projects, or clients).
- **Has its own database, Redis, and server configuration.**

So the mapping is: **one Installation = one Docker Compose stack**, and that one stack can host **many orgs**. You get two values for it from the dashboard — `INSTALLATION_API_KEY` and `INSTALLATION_ID` (see [../config/env-reference.md](../config/env-reference.md)).

---

## When to create more than one (docs list)

You can create multiple installations for different purposes:
- **By region** — EU Production, US Production
- **By environment** — Production, Staging
- **Multiple orgs on one server** — simplicity for smaller deployments
- **Dedicated per org** — maximum isolation and throughput

---

## Where to manage them

> "Installations are managed from the [BuildBase Dashboard](https://console.buildbase.app) under **Settings → Installations**."

---

## How it connects (from the architecture diagram)

The unique API key is what the **tenant server** uses for its **HMAC-signed API** calls to the central server (per the diagram in [../architecture/four-components.md](../architecture/four-components.md)). The central server handles installation **licensing** and **ES256 key management**. Application data never flows to it.

> The docs describe *what* the Installation and its key are for, but do **not** document the activation/handshake error states (e.g. what a wrong key produces). Don't invent specific failure messages — see [../failure-library/selfhost-mistakes.md](../failure-library/selfhost-mistakes.md).

---

## Read next

- The components this Installation runs → [../architecture/four-components.md](../architecture/four-components.md)
- Create one and deploy → [../deploy/quick-start.md](../deploy/quick-start.md)
- The two Installation env values → [../config/env-reference.md](../config/env-reference.md)
