# HTTP API - Overview (use Buildbase from any language)

The `@buildbase/sdk` package is a convenience wrapper around a plain HTTP+JSON API. **Nothing about that API is JavaScript-specific** - there's no request signing, no cookies required, no client-side crypto. Any backend language (Python, Go, Ruby, PHP, Java, C#, Rust…) can call it with an HTTP client and a session token in a header.

This section was read directly from the SDK source at 1.8.0 (`sdk/src/lib/api-base.ts`, `sdk/src/api/services/*-api.ts`, `sdk/src/lib/server-client.ts`, plus the calls that live outside `services/`: `sdk/src/tracking/*`, `sdk/src/analytics/client.ts`, `sdk/src/lib/agent-discovery.ts`, `sdk/src/lib/auth-code-exchange.ts` and the `sdk/src/lib/server-*` clients), and checked against the platform's own HTTP API guides, so it reflects what the SDK actually sends.

**The generated reference.** The docs site has an HTTP API section, [docs.buildbase.app/http-api](https://docs.buildbase.app/http-api), with guides (authentication, base URLs, errors, rate limits, idempotency, versioning) and one reference page per operation, generated from the platform's OpenAPI document (`GET {serverUrl}/api/v1/openapi.json`, also at `https://docs.buildbase.app/openapi/public-v1.json`). To read one operation's exact contract (credential, permission, rate limits, parameters, request schema, responses), open its reference page, or ask the hosted BuildBase MCP server (`https://api.console.buildbase.app/mcp`) with `get_api_operation`, which takes an `operationId` (`workspaces.list`) or `METHOD /path` (`GET /api/v1/public/workspaces`); its `search_docs` also finds operations. When this page and the reference disagree, the reference is generated from the running routes and wins.

> **Read next:** [endpoints.md](./endpoints.md) (the endpoint catalog of what the SDK calls), [webhooks.md](./webhooks.md) (verify inbound webhooks in any language), [using-from-any-language.md](./using-from-any-language.md) (auth flow + Python/Go examples).

## Contents

- [1. Base URL](#1-base-url) - server, version line, basePaths, environments
- [2. Authentication](#2-authentication---one-header-for-the-session-api) - `x-session-id`, `x-org-id`, `x-device-id`, the org-token surfaces
- [3. Standard headers](#3-standard-headers) - every header, CORS, `x-request-id`
- [4. Request & response format](#4-request--response-format) - JSON, path encoding, the two response shapes
- [5. Errors](#5-errors) - codes, 401, 402, 5xx, rate limits, SDK retries
- [6. Idempotency](#6-idempotency) - the `Idempotency-Key` header and the `idempotencyKey` body field
- [7. What is NOT pure HTTP](#7-what-is-not-pure-http-replication-caveats) - permissions, socket, login UX, webhooks

---

## 1. Base URL

```
{serverUrl}/api/{version}/{basePath}/{path}
```

- `serverUrl` - the hosted value is **`https://api.console.buildbase.app`** (or your own origin if self-hosting - point it at your tenant server, e.g. `https://api.yourcompany.com`; everything below is identical. To stand up that stack, use the **`buildbase-selfhost`** skill or see [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview)). An app that hosts many organizations in different regions resolves each one's `serverUrl` at runtime: [../sdk/server-side.md](../sdk/server-side.md#regions-which-serverurl).
- `version` - `v1`. The version in the path is the compatibility line; there is no version header. On `/api/v1` the platform only adds (routes, response fields, optional request fields, error codes, events) and never renames or removes what a published SDK reads, so ignore fields you do not know and keep a default branch for unknown `status` and `code` values.
- `basePath` - almost always **`public`**. The others: `auth` (sign-in, outside `public`), `guest` (buying without signing in), `licenses` (licence-key checks), `beta`, and `server` (the org-token server API).

So a typical call is: `https://api.console.buildbase.app/api/v1/public/workspaces`.

**Environments.** A development or staging environment is a separate tenant known as `<orgId>-<key>` (`key` is eight lowercase letters from the console); production is the bare org id. The address stays the same. A session or API key reaches the environment it was made in; where an org id travels in a path, query or body, send `<orgId>-<key>`. Nothing crosses between environments.

## 2. Authentication - one header for the session API

```
x-session-id: <sessionId>
```

That's the auth scheme for the session API, which is everything in [endpoints.md](./endpoints.md) except the org-token surfaces. The `sessionId` is obtained once via the login/code-exchange flow (see [using-from-any-language.md](./using-from-any-language.md)) and then sent on every request. There is **no request signing**.

Three things a non-Node client should know about headers:
- The SDK also sends **`x-org-id: <tenant>`** on every session call since 1.2.0 (the org id, or `<orgId>-<key>`). It does not select anything: a person's session works without it. It lets the platform refuse an agent's session minted in another environment (401 `AGENT_TENANT_MISMATCH`, which is not a reason to sign anyone out). Send it when you act with agent sessions.
- The browser SDK also sends `x-device-id`, a server-issued device token fetched from `GET public/device-token` after login (0.0.57). It is best-effort: when it is missing nothing breaks, "this device" and per-device sign-out are simply not anchored. A backend client can omit it.
- The **org-token surfaces** use `Authorization` instead of `x-session-id`: the console's own REST API ([org-api.md](./org-api.md), `Authorization: <orgId>:<secret>`, Bearer prefix tolerated), the server API under `/api/v1/server` (email, subscribers, commerce back office), the content routes `@buildbase/sdk/server` reads, and a named person's billing under `/api/subscriptions/users`, all as `Authorization: Bearer <orgId>:<secret>`. Do not send `x-session-id` to those. A session can also come from OAuth 2.0 (an agent or a third-party app, [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md)).

**Where `orgId` travels.** On the session API the server infers the org from the session; the SDK's `x-org-id` above is a guard, not the routing. Elsewhere it appears as:
- a **path segment** for public/unauthenticated endpoints: `/api/v1/public/{orgId}/plans/{slug}`, `/api/v1/public/{orgId}/credit-packages`, `/api/v1/public/{orgId}/settings`, the tracking, analytics, consent, checkout-return, agent-readiness and invitation-preview routes, and the `guest` and `licenses` basePaths
- a **query param** for beta config (`?orgId=...`), `auth/config?org=`, and the tracking config (`?clientId=`, with `orgId` in the path)
- a **body field** for the OAuth `auth/request` call, the code exchange (`auth/token`), the beta submit, and the token exchange (inside the `<orgId>:<secret>` token)

## 3. Standard headers

| Header | When |
|---|---|
| `x-session-id: <token>` | whenever you have a session (all session-authenticated calls) |
| `x-org-id: <orgId or orgId-key>` | sent by the SDK beside `x-session-id` (1.2.0); needed for agent sessions |
| `x-device-id: <deviceToken>` | sent by the browser SDK; optional for any other client |
| `Authorization: Bearer <orgId>:<secret>` | the org-token surfaces only; never alongside `x-session-id` |
| `Idempotency-Key: <unique>` | optional, on the writes that take one (section 6) |
| `x-order-token: <token>` | a guest's order or cart on the `guest` basePath |
| `Content-Type: application/json` | only when sending a body |

No `Accept`, no User-Agent required. You may add your own custom headers freely. The `/api/v1` paths answer CORS for any origin (`Content-Type, Authorization, x-session-id, x-org-id, x-device-id, x-order-token, traceparent, tracestate, Idempotency-Key` are allowed); the rest of `/api` (the org API) does not, on purpose. Every response carries **`x-request-id`**: quote it to support when a call fails.

## 4. Request & response format

- **Request bodies** are JSON. **GET parameters** are query-string (`?quotaSlug=...&page=1&limit=20`).
- **Path IDs** are interpolated into the URL and **every interpolated segment is URL-encoded** (since 0.0.51 the SDK builds paths through one tagged template that encodes each value, and it refuses an id that is `.` or `..`, which `fetch` would resolve into another path). Do the same when replicating.
- **Responses come in two shapes**, depending on endpoint:
  1. **Bare JSON** - the body *is* the object (most endpoints).
  2. **Enveloped** - `{ "success": true, "data": { ... }, "message": "..." }`. When `success` is present and `false`, treat it as an error using `message`, whatever the status (a few older routes answer 200 with `success: false`).

  A robust client handles both: if the JSON has a `success` field, unwrap `data`; otherwise use the body directly. Each route keeps the shape it has.

## 5. Errors

- Non-2xx responses carry a human `message`, and often a **`code`** to branch on (never branch on the message's wording). Common shapes: `{ "error": true, "path": "<field>", "message": "..." }` for a validation 400; `{ "success": false, "message", "code", ... }` for refusals such as the 402 plan refusals; a 401 may be the plain text `Unauthorized` or JSON with a `code` (`session_ended`). Read `message` first, then `error`. Every `code` is listed at [docs.buildbase.app/reference/error-codes](https://docs.buildbase.app/reference/error-codes).
- **401** means the session is invalid/expired - re-authenticate. (The SDK fires an `onUnauthorized` callback; there is **no automatic token refresh** - sessions don't refresh, you re-login.) Exceptions: `AGENT_TENANT_MISMATCH`, and routes that answer 401 for a refusal of their own (an expired code) while the session is fine.
- **402** is a plan refusal (`FEATURE_NOT_IN_PLAN`, `PLAN_LIMIT_REACHED` with `limit` and `current`, `QUOTA_EXHAUSTED`); on `credits/consume` it means insufficient credits, and the body includes `available` and `requested` (the SDK's code `INSUFFICIENT_CREDITS`).
- **500 and 503** are both server errors: an unexpected failure is 500 with `code: "server_error"` and `requestId`; a failure the route caught is 503 `server_error`; a service briefly down is 503 `temporarily_unavailable` with `Retry-After`. Retry logic keyed on 500 alone misses most of them.
- **429** is a rate limit: `{ "success": false, "message", "reason": "rate_limited", "retryAfter" }` plus `Retry-After` and the standard `RateLimit-*` headers. Limits count per IP (500 requests per 3 seconds across `/api`), per API key (1000 a minute), and per route for sign-in, codes, the token exchange (120 a minute) and money-moving routes (credit consumption 30 a minute); the full table is [docs.buildbase.app/http-api/rate-limits](https://docs.buildbase.app/http-api/rate-limits). Limits are the same on every plan.
- The SDK retries **network errors and 5xx** only on idempotent methods (GET, HEAD, OPTIONS, PUT, DELETE) and only if you opt in (`maxRetries`), never a POST or PATCH. A **429 or 503** is retried twice by default (idempotent methods, and writes that carry an `Idempotency-Key`), waiting out `Retry-After` up to 10 seconds. Default timeout 30s.

## 6. Idempotency

Two mechanisms, depending on the route:

- **`Idempotency-Key` header** (1 to 255 printable ASCII characters, optional everywhere). The **billing writes** (`subscription` checkout, change, cancel, pause, resume, convert-to-paid, billing portal, retention-offer accept, invoice pay, `billing/checkout`, card setup, add-on cancel and decrease, `credits/purchase`, `credits/payment-method-setup`, under `workspaces/{id}` or `me`) hand the key to Stripe, so a retry with the same key gets Stripe's first answer instead of a second charge. The **commerce writes** (refunds, part charges, shipments, returns, item-subscription and booking cancels, payout mark-paid, and the server API's commerce writes) store the first 2xx answer for 24 hours and replay it with `Idempotent-Replayed: true`; a key still running answers 409 `IDEMPOTENCY_IN_PROGRESS`, the same key with a different request 422 `IDEMPOTENCY_KEY_REUSED`. `POST /api/v1/server/emails/send` never sends twice under one key. The SDK sends a key (a new UUID per call) on every billing and commerce write; a route that is not listed ignores the header. The list is [docs.buildbase.app/http-api/idempotency](https://docs.buildbase.app/http-api/idempotency).
- **Body field `idempotencyKey`** on usage (single + per-item in batch), `credits/consume` and `credits/reserve`. Send a stable unique key to make a write safe to retry without double-applying.

The body-field form does work - a repeated key does not double-count. What catches people is the shape of the *replay*, because a deduplicated call is reported as a success, not as a conflict:

- **`used` comes back `0` on a replay**, while `consumed` and `available` show the already-applied state. So `used` means "what this call recorded", not "the quantity in the request". Never assert `used === quantity`, or every retry path fails on a correct dedupe.
- **The key is scoped to the workspace and the quota**, not global. The same key against a different `quotaSlug` records again, which is deliberate: one request id can meter several quotas.
- **A replay with a different `quantity` is silently ignored.** First write wins, and the second returns 200 with no indication the numbers differed. Do not "correct" a value by re-sending under the same key.
- **In a batch, a deduplicated item still reports `success: true` and counts toward `succeeded`.** The envelope is identical to a fresh write; only `results[].used === 0` tells them apart. Counting `succeeded` to mean "rows metered" over-reports on any retry.

Credits behave the same way: a repeated `idempotencyKey` on `credits/consume` returns 200 with `balanceAfter` unchanged rather than deducting twice.

## 7. What is NOT pure HTTP (replication caveats)

Almost everything ports cleanly. The few things to know:

- **Permissions have a server answer since 0.0.73.** `GET workspaces/{id}/permissions/me` returns `{ role, isOwner, permissions }` for the caller; from any language that is one GET. The React hooks and `permissions.check` / `permissions.resolve` still compute locally from three endpoints (`GET workspaces/{id}`, `GET {orgId}/settings`, `GET workspaces/{id}/users`), which is also the fallback against an older server. See [endpoints.md](./endpoints.md#permissions).
- **Live inbox updates** ride a socket.io channel, not HTTP. It carries only "your list changed"; a non-Node client polls the `notifications` routes instead.
- **The browser login UX** (redirect handling, reading `?code=` off the URL, localStorage) is browser glue. On a backend you do the equivalent server-side: receive the `?code=` at your redirect route and exchange it (see [using-from-any-language.md](./using-from-any-language.md)).
- **Webhook verification** is HMAC-SHA256 - every language has this in its standard library. Deliveries carry an event `id` to dedupe on, and current platforms also send the Standard Webhooks headers, so a Standard Webhooks library verifies them too. Recipe and the full event catalog in [webhooks.md](./webhooks.md).

That's it. There is no proprietary protocol - if you can make HTTPS requests and compute an HMAC, you can use all of Buildbase from any language.
