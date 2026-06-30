# Handoff — Integrating Your App Against a Self-Hosted Stack

Once the stack is running ([quick-start.md](../deploy/quick-start.md) → `/api/ready` is true), the application-development side is the same as the managed product, with one change: `serverUrl` points at your tenant server instead of the Buildbase cloud. This file is the seam between this skill (deploy/operate) and the `buildbase` SDK-integration skill (build the app).

> **Grounding:** the self-hosted docs define `SERVER_URL` / `TENANT_SERVER_URL` (the tenant server's public URL) and `CORS_WHITELISTED_DOMAINS`. The SDK/HTTP details below come from the separate **`buildbase`** skill (reverse-engineered from the SDK source), not the self-hosted docs.

---

## The one change

| | Managed (cloud) | Self-hosted |
|---|---|---|
| `serverUrl` | `https://api.console.buildbase.app` | your `TENANT_SERVER_URL` (e.g. `https://api.yourcompany.com`) |
| Everything else | — | **same** — SDK, hooks, gates, HTTP API, webhooks |

The SDK and the raw HTTP API are a thin layer over the tenant server. Point them at your origin and the entire integration surface works unchanged.

```env
# In the APP (not the self-host stack) — managed value, swapped for self-host:
NEXT_PUBLIC_BUILDBASE_SERVER_URL=https://api.yourcompany.com   # your TENANT_SERVER_URL
```

For raw HTTP from any backend, the base URL changes the same way:
```
https://api.yourcompany.com/api/v1/public/...    # instead of https://api.console.buildbase.app/...
```
Auth is still the single `x-session-id` header; the envelope/error rules are unchanged.

---

## What does NOT change — use the `buildbase` skill for all of it

Everything about *building the app* is covered by the separate **`buildbase` SDK-integration skill** (same repo/marketplace). Route there for:
- Auth wiring (`SaaSOSProvider`, the three auth routes, `useSaaSAuth`)
- Workspaces, billing, feature flags, quota/usage, credits, notifications
- Server-side `BuildBase()` factory and webhook verification
- Calling Buildbase from any backend language via raw HTTP

Don't re-explain those here — hand the developer to that skill with the one substitution: **`serverUrl` = your tenant server.**

---

## A few self-host-specific gotchas for the app side

- **CORS (documented):** the browser app's origin must be in the stack's `CORS_WHITELISTED_DOMAINS` ([env-reference.md](../config/env-reference.md)), or client calls are blocked by CORS.
- **TLS in production (documented prereq):** production requires a domain + SSL certificate; use your `https://` public URLs (`TENANT_SERVER_URL`, `CLIENT_URL`, `AUTH_URL`) consistently across the app, the stack, and the setup wizard.
- **`orgId`** rules and SDK validation are unchanged from the managed product — those come from the **`buildbase`** skill, not the self-hosted docs.

---

## Read next

- Get the stack healthy first → [quick-start.md](../deploy/quick-start.md)
- The component your `serverUrl` points at → [four-components.md](../architecture/four-components.md)
- The full app-side integration → the **`buildbase`** skill, or [docs.buildbase.app](https://docs.buildbase.app)
