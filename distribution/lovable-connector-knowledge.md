# BuildBase org API - connector knowledge

BuildBase is one SDK and REST API for SaaS auth, workspaces, Stripe billing, usage credits, lifecycle email and event workflows. This file describes the **organization API**: the token-authenticated REST surface behind the BuildBase console, used to run an organization by API. It is not the end-user sign-in flow; that is the SDK (`@buildbase/sdk`), and an app's users never hold this token.

Position rule:

```text
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

Sources, in order of authority: https://docs.buildbase.app/reference/admin-api, `plugins/buildbase/knowledge/http-api/org-api.md` and `scripts/api-routes.txt` in this repo. Every path below is relative to the base URL and appears in that routes list.

## Base URL

```text
https://api.console.buildbase.app
```

Self-hosted installations use their own tenant server URL instead.

## Authentication

One header. The token is `<orgId>:<secret>`: the organization's 24-hex id, a colon, and a 60-character secret. A `Bearer ` prefix is accepted and stripped.

```text
Authorization: <orgId>:<secret>
```

Create a token in the console under Settings, API tokens, or with `POST /api/tokens`. The full secret is returned once, in that `POST` response only. Give the token a `role`; a token created without one inherits its creator's role, so an admin's keyless token is an admin credential. The role is fixed once issued.

There is no `GET /v1/me`. The real credential and health checks are below.

## Test request

Unauthenticated, no body, returns the text `OK`:

```text
GET /health
```

`GET /api/ready` is also unauthenticated and returns `{ "ready": true, ... }` or a `503` with `{ "ready": false, "reason": ... }`. To check that a token works, call any authenticated read, for example `GET /api/tokens`, which returns the token list with masked previews; a bad token returns `401` with the plain-text body `Unauthorized`.

## Key endpoints

All relative to the base URL. Collection endpoints share one list contract (see Listing).

| Area | Paths |
|---|---|
| Tokens | `GET /api/tokens`, `POST /api/tokens`, `PATCH /api/tokens/:id`, `DELETE /api/tokens/:id` |
| Roles and permissions | `GET /api/access-control/roles?kind=api` (API roles are created in the console under Settings, API Roles, or through `/api/access-control`) |
| Workspaces | `/api/workspaces`, `/api/workspaces/features`, `/api/workspaces/notification-events` |
| App users | `/api/users`, `/api/users-list`, `/api/users/attributes`, `/api/users/tags` |
| Audience | `/api/audience`, `/api/audience-lists`, `/api/audience/attributes`, `/api/audience/tags` |
| Billing | `/api/subscriptions`, `/api/subscriptions/plans`, `/api/subscriptions/groups`, `/api/subscriptions/items`, `/api/subscriptions/logs`, `/api/payments` |
| Credits | `/api/subscriptions/credits`, `/api/subscriptions/credit-packages` |
| Feature flags | `/api/features` |
| Email | `/api/emails`, `/api/emails/campaigns`, `/api/emails/templates`, `/api/emails/senders`, `/api/emails/domains`, `/api/emails/drafts` |
| Workflows | `/api/workflows`, `/api/workflows/definitions`, `/api/workflows/instances`, `/api/workflows/templates` |
| Webhooks | `/api/organizations/webhooks` |
| Push | `/api/organizations/push`, `/api/organizations/push/campaigns` |
| Content | `/api/blogs`, `/api/docs`, `/api/faqs`, `/api/faqs/collections`, `/api/rich-content`, `/api/testimonials` |
| Collections | `/api/collections` |
| Forms | `/api/forms` |
| Short links | `/api/links`, `/api/links-analytics` |
| Assets | `/api/assets` |
| Organization | `/api/organizations/settings`, `/api/organizations/users`, `/api/organizations/users/invitations`, `/api/organizations/auth`, `/api/organizations/config` |

`GET /api/workflows/definitions` is the one self-describing endpoint: it publishes the workflow node catalog with inputs and outputs. There is no OpenAPI document and no endpoint that lists endpoints.

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

{ "name": "changelog-bot", "role": "content-editor" }
```

List the roles a token may be given:

```text
GET /api/access-control/roles?kind=api
Authorization: <orgId>:<secret>
```

## Response shapes

**No envelope.** A success returns the resource directly. Update-style endpoints return `{ "success": true, "message": "updated" }`.

Three error shapes, by which layer rejected the request. Branch on the HTTP status, not the body.

| Shape | When |
|---|---|
| `{ "error": true, "message": "...", "path": "..." }` | Validation and shared error helpers; most 400, 404, 409 |
| `{ "success": false, "message": "..." }` | Rate limiting, read-only impersonation, some handlers |
| Plain text `Unauthorized` | Every 401. No JSON body |

Status codes: `400` bad or extra field, `401` bad token, `402` no active plan (`code: NO_ACTIVE_PLAN`), `403` not allowed, `404` not found, `409` duplicate, `429` rate limited, `503` server error (not 500).

## Listing and pagination

Every collection endpoint takes the same query parameters. Note the `$` on the first two only.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `$page` | number | 1 | 1-indexed page |
| `$limit` | number | controller default | Items per page, clamped to 1000 |
| `filter` | JSON object | `{}` | Mongo-style query; one level of nesting round-trips, deeper paths must be sent as dotted keys |
| `sort` | JSON object | none | Field to direction, for example `{"createdAt":-1}` |
| `populate` | string | `''` | Space-separated reference fields to expand |
| `projection` | JSON object | `{}` | Fields to include or exclude |
| `pagination` | boolean | `true` | `false` returns every match in the same wrapper with `limit: 0` |

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

Rows are always at `docs`, even with `pagination=false`. Page on `hasNextPage`.

## Pitfalls

- **The role is fixed at issue.** `PATCH /api/tokens/:id` changes `name`, `description`, `active`, `archived`, never `role`. To change what a token can do, edit the role's permissions (applies to every token on that role at once) or issue a new token.
- **Omitting `role` is a full token**, not a narrow one.
- **The role governs organization permissions, not workspace ones.** Workspace permissions resolve from the person who created the token.
- **Rate limits count per IP, not per token:** 500 requests per 3 seconds globally, with stricter per-minute limits on auth, usage recording (60/min) and credit consumption (30/min). Read the standard `RateLimit-*` headers on a 429.
- **A 200 does not always mean success.** Some handlers, workflow publishing among them, return `200` with `{ "success": false }`. Check `success` where it appears.
- **`$limit` over 1000 is clamped silently**; the response's `limit` reports what you got.
- **Outbound webhooks** carry `x-buildbase-signature` (`sha256=` HMAC-SHA256 of `{timestamp}.{body}`), `x-buildbase-timestamp` (Unix seconds) and `x-buildbase-event`. Signatures are valid for five minutes. Deliveries have no unique event id; deduplicate on a hash of the raw body.
- **Keep the token server-side.** It carries real permissions and must never reach a browser or a chat log.
