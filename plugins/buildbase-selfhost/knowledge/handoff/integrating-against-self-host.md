# Handoff - Integrating Your App Against a Self-Hosted Stack

Once the stack is running ([quick-start.md](../deploy/quick-start.md) -> `/api/ready` is true, the organization created on the installation and set up), the application-development side is the same as the managed product, with one change: `serverUrl` points at your tenant server instead of the Buildbase cloud. This file is the seam between this skill (deploy/operate) and the `buildbase` SDK-integration skill (build the app).

> **Grounding:** the self-hosted docs define `SERVER_URL` / `TENANT_SERVER_URL` (the tenant server's public URL) and `CORS_WHITELISTED_DOMAINS`; the docs' HTTP API page "Base URLs, environments and CORS" (`docs/content/http-api/base-urls.mdx`) says which base URL a self-hosted install uses and which paths are open to any origin. The SDK details come from the published `@buildbase/sdk` package (its `AGENTS.md` and `README.md`, "Server compatibility") and the separate **`buildbase`** skill.

---

## The one change

| | Managed (cloud) | Self-hosted |
|---|---|---|
| `serverUrl` / base URL | `https://api.console.buildbase.app` | your tenant server's own public URL, the one its `SERVER_URL` setting names (`TENANT_SERVER_URL` in `.env.selfhost`, e.g. `https://api.yourcompany.com`) |
| Everything else | - | **same** - SDK, hooks, gates, HTTP API, webhooks |

The SDK and the raw HTTP API are a thin layer over the tenant server. Point them at your origin and the integration surface works the same way, within the limits of the server release you run (below).

```env
# In the APP (not the self-host stack) - managed value, swapped for self-host:
NEXT_PUBLIC_BUILDBASE_SERVER_URL=https://api.yourcompany.com   # your TENANT_SERVER_URL
```

For raw HTTP from any backend, the base URL changes the same way:
```
https://api.yourcompany.com/api/v1/public/...    # instead of https://api.console.buildbase.app/...
```
Authentication is unchanged (a session in `x-session-id`, or an org API key on the server), as are the envelope and error rules; the `buildbase` skill has them. The server publishes its own copy of the OpenAPI document at `GET <your server>/api/v1/openapi.json`, naming its own URL.

`orgId` is the self-hosted organization's 24-hex id from the console, as on the cloud. There is no publishable key here either.

---

## Which SDK version to install

A self-hosted server is only as new as the `buildbaseapp/tenant-server` image you pulled, and a few SDK features need a server release that has them. The SDK README's **Server compatibility** table lists each one with the SDK version and server release it needs and what happens **"On an older server"**: the SDK degrades rather than breaking (a route answers 404 and a section hides, a field is absent and a line is not shown, a form says the code could not be checked). Examples from that table: workspace invitations and the notification inbox need server release 22; the paused-invoice line and the trial banner's payment-method sentence need release 23.

So:

- Installing the current SDK (`@buildbase/sdk` 1.8.0, the npm `latest`) against an older self-hosted server is supported, with the degradations the table names. Read `node_modules/@buildbase/sdk/README.md` "Server compatibility" for the installed version.
- To get the routes newer SDK screens call, update the stack ([../operations/upgrades-backups.md](../operations/upgrades-backups.md)). The installation's page in the console shows the version it last reported, and the console may refuse to open its organizations below a minimum version until you update.
- Docs pages say the same thing in places, e.g. an older self-hosted server delivers a scheduled notification's inbox item and email at once, and one older than the permissions change leaves `workspace:delete` out of a creator's list. When an app must support an older self-hosted server, gate on what that server answers.

---

## Settings that do or do not apply on a self-hosted install

- **Regional `serverUrl` (cells).** The SDK's rule that `serverUrl` must be the organization's regional URL, and `resolveServerUrl` with central, is about BuildBase's cloud cells. On a self-hosted install the base URL is your tenant server's own URL, per the docs' base-URL table.
- **`environment`** (a development or staging environment's eight-letter key, on `SaaSOSProvider`, `BuildBase()`, `createAgentStack` and `BuildBaseTracking`) works the same way as on the cloud: the request goes to the same base URL and the SDK sends `<orgId>-<key>`. The self-hosted docs do not say whether a self-hosted organization offers environments; check the console rather than assuming.
- **`npx @buildbase/sdk init`** takes `--server-url <url>` (its default is `https://api.console.buildbase.app`), so wire a self-hosted app with `npx @buildbase/sdk init --org-id <24 hex> --server-url https://api.yourcompany.com`, or correct the server URL it wrote to `.env.local`. `init --claim` creates a claimable organization through a central server's `POST /api/organizations/agent/identity`; a self-hosted organization is instead created in the console on an installation ([quick-start.md](../deploy/quick-start.md) Step 6).

---

## What does NOT change - use the `buildbase` skill for all of it

Everything about *building the app* is covered by the separate **`buildbase` SDK-integration skill** (same repo/marketplace). Route there for:
- Auth wiring (`SaaSOSProvider` or its alias `BuildBaseProvider`, the three auth routes, `useSaaSAuth`)
- Workspaces, billing, feature flags, quota/usage, credits, notifications
- Server-side `BuildBase()` factory, `@buildbase/sdk/server`, and webhook verification
- Calling Buildbase from any backend language via raw HTTP

Don't re-explain those here - hand the developer to that skill with the one substitution: **`serverUrl` = your tenant server.**

---

## Self-host-specific gotchas for the app side

- **CORS (documented):** `/api/v1/*`, `/.well-known/*` and `/org/*` answer any origin, so the SDK's browser calls work from any app origin without touching the stack. `CORS_WHITELISTED_DOMAINS` governs only the rest of `/api` (the organization API), which belongs on your server with an API key, never in a page ([env-reference.md](../config/env-reference.md)).
- **TLS in production (documented prereq):** production requires a domain and SSL certificate; use your `https://` public URLs (`TENANT_SERVER_URL`, `CLIENT_URL`, `AUTH_URL`) consistently across the app, the stack and the setup wizard. Features where BuildBase's servers call yours need a public HTTPS URL; it never connects to a private address. Enterprise SSO needs `SERVER_URL` public and on HTTPS, because the WorkOS redirect URI is built from it.
- **Sign-in needs console setup first:** an email sender, a sign-in method, and that method enabled on the app's client ([quick-start.md](../deploy/quick-start.md) Step 7). Without a sender the hosted page refuses password sign-up and invitations answer 503 `NO_SENDER_CONFIGURED`.
- **Rate limits:** behind the production Nginx, `/api/v1/` is limited per address and session (20 r/s) with an address-wide guard (200 r/s), and `/api/v1/auth` sits on the 5 r/s auth tier ([production.md](../deploy/production.md)). A self-hosted install can also raise `API_KEY_RATE_LIMIT_MAX`, `ORG_WRITE_RATE_LIMIT_MAX` and `TOKEN_EXCHANGE_PER_MINUTE`.
- **`orgId`** rules and SDK validation are unchanged from the managed product - those come from the **`buildbase`** skill, not the self-hosted docs.

---

## Read next

- Get the stack healthy first -> [quick-start.md](../deploy/quick-start.md)
- The component your `serverUrl` points at -> [four-components.md](../architecture/four-components.md)
- Keeping the server new enough -> [upgrades-backups.md](../operations/upgrades-backups.md)
- The full app-side integration -> the **`buildbase`** skill, or [docs.buildbase.app](https://docs.buildbase.app)
