# BuildBase org API - connector knowledge

BuildBase is one SDK and REST API for SaaS auth, workspaces, Stripe billing, usage credits, lifecycle email and event workflows. This file describes the **organization API**: the token-authenticated REST surface behind the BuildBase console, used to run an organization by API. It is not the end-user sign-in flow; that is the SDK (`@buildbase/sdk`, current version 1.9.0, the npm `latest` tag), and an app's users never hold this token.

Position rule:

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

Sources, in order of authority: the generated OpenAPI document for this API (`GET https://api.console.buildbase.app/api/v1/openapi/org-api.json`), https://docs.buildbase.app/reference/admin-api, `plugins/buildbase/knowledge/http-api/org-api.md` and `scripts/api-routes.txt` in this repo. Every path below is relative to the base URL and appears in that routes list.

## Base URL

```text
https://api.console.buildbase.app
```

Self-hosted installations use their own tenant server URL instead. A development or staging environment uses the same address with its own tokens.

## Authentication

One header. The token is `<orgId>:<secret>`: the organization's 24-hex id, a colon, and a 60-character secret. A `Bearer ` prefix is accepted and stripped.

```text
Authorization: <orgId>:<secret>
```

Create a token in the console under Settings, API keys, or with `POST /api/tokens`. The full secret is returned once, in that `POST` response only. Give the token a `role`; a token created without one inherits its creator's role, so an admin's role-less token is an admin credential. The role is fixed once issued.

Each token also has a type, `keyRole`, fixed at creation: `app-server` (an app's backend; never reaches the admin routes) or `admin` (an owner's or admin's tool; needs the owner or admin role). The admin routes change the billing catalog, coupons, Stripe keys, organization settings, blueprints and environments; an app-server token gets `403 ADMIN_SCOPE_REQUIRED` there. Left out, the type follows the role: owner or admin gives `admin`, anything else `app-server`.

There is no `GET /v1/me`. The real credential and health checks are below.

## Test request

Unauthenticated, no body, returns a small JSON object:

```text
GET /api/ready
```

It answers `{"ready":true,"mongo":"ok","redis":"ready"}`, or a `503` carrying `{"ready":false,...}` when the service is not serving yet. Use this one as the connector's health check, and read only `ready`: the other fields describe dependencies and can change.

`GET /health` also exists and is also unauthenticated, but on the cloud it returns a detailed operational report rather than a short answer, so it is the wrong shape for a connector test. A self-hosted tenant server answers the same path with the plain text `OK`, so the two differ by deployment; `/api/ready` is the same small answer on both. Verified against `https://api.console.buildbase.app` on 2026-11-24.

To check that a token works, call any authenticated read, for example `GET /api/tokens`, which returns the token list with masked previews; a bad token returns `401` with the plain-text body `Unauthorized`.

## Key endpoints

All relative to the base URL. Collection endpoints share one list contract (see Listing).

| Area | Paths |
|---|---|
| Tokens | `GET /api/tokens`, `POST /api/tokens`, `PATCH /api/tokens/:id`, `DELETE /api/tokens/:id` |
| Roles and permissions | `GET /api/access-control/roles?kind=api` (API roles are created in the console under Settings, API Roles, or through `/api/access-control`) |
| Workspaces | `/api/workspaces`, `/api/workspaces/features`, `/api/workspaces/notification-events` |
| App users | `/api/users`, `/api/users-list`, `/api/users/attributes`, `/api/users/tags` |
| Audience | `/api/audience`, `/api/audience-lists`, `/api/audience/attributes`, `/api/audience/tags` |
| Billing | `/api/subscriptions`, `/api/subscriptions/plans`, `/api/subscriptions/groups`, `/api/subscriptions/items`, `/api/subscriptions/logs`, `/api/subscriptions/overrides`, `/api/payments` |
| Add-ons and grants | `/api/subscriptions/offers`, `/api/subscriptions/grants`, `/api/subscriptions/claims` |
| Credits | `/api/subscriptions/credits`, `/api/subscriptions/credit-packages` |
| Feature flags | `/api/features` |
| Email | `/api/emails`, `/api/emails/campaigns`, `/api/emails/templates`, `/api/emails/senders`, `/api/emails/domains`, `/api/emails/drafts`, `/api/emails/health` |
| Workflows | `/api/workflows`, `/api/workflows/definitions`, `/api/workflows/instances`, `/api/workflows/templates` |
| Webhooks | `/api/organizations/webhooks` |
| Push | `/api/organizations/push`, `/api/organizations/push/campaigns` |
| Content | `/api/blogs`, `/api/docs`, `/api/faqs`, `/api/faqs/collections`, `/api/rich-content`, `/api/testimonials` |
| Collections | `/api/collections` |
| Forms | `/api/forms` |
| Short links | `/api/links`, `/api/links-analytics` |
| Assets | `/api/assets`, `/api/storage/usage` |
| Commerce | `/api/marketplace` |
| Blueprints | `/api/blueprint` (an admin-type token) |
| Web analytics | `/api/analytics/web` |
| Organization | `/api/organizations/settings`, `/api/organizations/users`, `/api/organizations/users/invitations`, `/api/organizations/auth`, `/api/organizations/config` |

**Machine-readable catalog.** The platform generates an OpenAPI 3.1 document for this API from its running routes: `GET /api/v1/openapi/org-api.json` on the base URL (no token needed). Each operation names its credential (`x-auth`), the role grant it needs (`x-permission`) and its rate limits (`x-rateLimit`). `GET /api/workflows/definitions` also publishes the workflow node catalog with inputs and outputs.

**Server API.** The same token also reaches `/api/v1/server/*`, a token-only surface for an app's backend: `POST /api/v1/server/emails/send` (one transactional email from a console template or inline content, with an optional `Idempotency-Key` so a retry never sends twice), `PUT /api/v1/server/subscribers` (upsert an audience member by email), and the commerce back office under `/api/v1/server/commerce/`. It takes an API key only, never a console session, and allows 300 requests a minute per key. The role needs `emails_api_sends` (create) to send and `audience` to manage subscribers.

## Request examples

List short links, page 2, 25 per page, active only, newest first:

```text
GET /api/links?$page=2&$limit=25&filter={"active":true}&sort={"createdAt":-1}
Authorization: <orgId>:<secret>
```

Create a token for a bot with a narrow role:

```text
POST /api/tokens
Authorization: <orgId>:<secret>
Content-Type: application/json

{ "name": "changelog-bot", "role": "content-editor", "keyRole": "app-server" }
```

List the roles a token may be given:

```text
GET /api/access-control/roles?kind=api
Authorization: <orgId>:<secret>
```

## Response shapes

**No envelope.** A success returns the resource directly. Update-style endpoints return `{ "success": true, "message": "updated" }`.

Three error shapes, by which layer rejected the request. Branch on the HTTP status (and a `code` where one is sent), not the body shape.

| Shape | When |
|---|---|
| `{ "error": true, "message": "...", "path": "..." }` | Validation and shared error helpers; most 400, 404, 409 |
| `{ "success": false, "message": "...", "code": "..." }` | Rate limiting, plan refusals, read-only impersonation, some handlers |
| Plain text `Unauthorized` | Every 401. No JSON body |

Status codes: `400` bad or extra field, `401` bad token, `402` plan refusal (`code`: `NO_ACTIVE_PLAN`, `FEATURE_NOT_IN_PLAN` or `PLAN_LIMIT_REACHED`), `403` not allowed (`ADMIN_SCOPE_REQUIRED` for an app-server token on an admin route, `API_KEYS_SUSPENDED` when BuildBase suspended the organization's keys), `404` not found, `409` duplicate, `429` rate limited, `503` a server error a handler caught, `500` an unexpected one (`code: "server_error"`, with `requestId`). Treat both `500` and `503` as server errors. Every response carries an `x-request-id` header to quote to support.

## Listing and pagination

Every collection endpoint takes the same query parameters. Note the `$` on the first two only.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `$page` | number | 1 | 1-indexed page |
| `$limit` | number | controller default | Items per page, capped at 500 on current servers |
| `filter` | JSON object | `{}` | Mongo-style query, brackets (`filter[archived]=false`) or one JSON object; one level of nesting round-trips, deeper paths must be sent as dotted keys |
| `sort` | JSON object | none | Field to direction, for example `{"createdAt":-1}` |
| `populate` | string | `''` | Space-separated reference fields to expand |
| `projection` | JSON object | `{}` | Fields to include or exclude |
| `pagination` | boolean | `true` | `false` asks for the largest page (500 rows), still in the same wrapper |

Paged response:

```json
{
  "docs": [],
  "totalDocs": 214,
  "limit": 25,
  "page": 2,
  "totalPages": 9,
  "pagingCounter": 26,
  "hasPrevPage": true,
  "hasNextPage": true,
  "prevPage": 1,
  "nextPage": 3
}
```

Rows are always at `docs`, even with `pagination=false`. Page on `hasNextPage`: on current servers `pagination=false` no longer returns every row in one answer (an older server did, reporting `limit: 0`), so a loop on `hasNextPage` is correct on both.

## Pitfalls

- **The role is fixed at issue.** `PATCH /api/tokens/:id` changes `name`, `description`, `active`, `archived`, never `role` or `keyRole`. To change what a token can do, edit the role's permissions (applies to every token on that role at once) or issue a new token.
- **Omitting `role` is a full token**, not a narrow one.
- **The role governs organization permissions, not workspace ones.** Workspace permissions resolve from the person who created the token.
- **A token acts only on its own organization and its own environment.** Make a development or staging environment's tokens inside that environment.
- **Rate limits stack:** 500 requests per 3 seconds per IP across all of `/api`, 1000 a minute per token, 1200 writes a minute per organization, plus stricter per-minute limits on sign-in, usage recording (60/min) and credit consumption (30/min). The per-IP limit is shared by every token behind one egress address. On a 429 wait `Retry-After` (or the body's `retryAfter`); the standard `RateLimit-*` headers describe the window.
- **A 200 does not always mean success.** Some handlers, workflow publishing among them, return `200` with `{ "success": false }`. Check `success` where it appears.
- **`$limit` over the cap is clamped silently**; the response's `limit` reports what you got.
- **Outbound webhooks** carry `x-buildbase-signature` (`sha256=` HMAC-SHA256 of `{timestamp}.{body}`), `x-buildbase-timestamp` (Unix seconds), `x-buildbase-event` and `x-buildbase-event-id`. Signatures are valid for five minutes. Each delivery's body has an `id` (starting `evt_`, equal to `x-buildbase-event-id`), the same on every endpoint and every retry: deduplicate on it, and fall back to a hash of the raw body only when a delivery from an older platform has no `id`. Current platforms also send the Standard Webhooks headers (`webhook-id`, `webhook-timestamp`, `webhook-signature`), signed with the same secret. Event names come from a fixed catalog (`plugins/buildbase/knowledge/http-api/webhook-events.json`); never invent one.
- **Keep the token server-side.** It carries real permissions and must never reach a browser or a chat log.

## No account yet, or a person at the keyboard

- **Claimable organization.** An agent with no BuildBase account can create one: `POST /api/organizations/agent/identity` on central (`https://central.console.buildbase.app`) with `{ "name": "...", "email": "<optional>" }` answers, once, an API key, a claim URL and a claim code. It works at once on an unclaimed organization's caps and is deleted after 72 hours unless a person claims it. `npx @buildbase/sdk init --claim --yes` does the same and writes the keys to `.env.local`. Keep the key in an environment variable, never in chat; the claim step is always the person's.
- **BuildBase's hosted MCP server.** `https://api.console.buildbase.app/mcp` ("BuildBase Console", Streamable HTTP, OAuth sign-in as the person) manages the person's organizations from an AI tool with no token: `list_orgs`, `console_get`, `console_write` (reversible changes) and `console_destructive_change` (deletes, sends, money, each approved by the person), blueprints, `search_docs`, `fetch_doc` and `get_api_operation` for one HTTP operation's exact contract. It manages BuildBase itself; it is not the app's own MCP server, which an app builds with `@buildbase/sdk/mcp`.
