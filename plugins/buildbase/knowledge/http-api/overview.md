# HTTP API - Overview (use Buildbase from any language)

The `@buildbase/sdk` package is a convenience wrapper around a plain HTTP+JSON API. **Nothing about that API is JavaScript-specific** - there's no request signing, no cookies required, no client-side crypto. Any backend language (Python, Go, Ruby, PHP, Java, C#, Rust…) can call it with an HTTP client and a session token in a header.

This section was reverse-engineered directly from the SDK source at 0.0.78 (`sdk/src/lib/api-base.ts`, `sdk/src/api/services/*.ts`, `sdk/src/lib/server-client.ts`, plus the calls that live outside `services/`: `sdk/src/tracking/*`, `sdk/src/lib/agent-discovery.ts` and `sdk/src/lib/server-content/client.ts`), so it reflects exactly what the SDK actually sends - not docs that may drift.

> **Read next:** [endpoints.md](./endpoints.md) (the full endpoint catalog), [webhooks.md](./webhooks.md) (verify inbound webhooks in any language), [using-from-any-language.md](./using-from-any-language.md) (auth flow + Python/Go examples).

---

## 1. Base URL

```
{serverUrl}/api/{version}/{basePath}/{path}
```

- `serverUrl` - the hosted value is **`https://api.console.buildbase.app`** (or your own origin if self-hosting - point it at your tenant server, e.g. `https://api.yourcompany.com`; everything below is identical. To stand up that stack, use the **`buildbase-selfhost`** skill or see [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview)).
- `version` - `v1`.
- `basePath` - almost always **`public`**. (`beta` exists for a few beta endpoints; auth's `/auth/request` is the one exception that sits *outside* basePath.)

So a typical call is: `https://api.console.buildbase.app/api/v1/public/workspaces`.

## 2. Authentication - one header for the session API

```
x-session-id: <sessionId>
```

That's the auth scheme for the session API, which is everything in [endpoints.md](./endpoints.md) except the two org-token surfaces. The `sessionId` is obtained once via the login/code-exchange flow (see [using-from-any-language.md](./using-from-any-language.md)) and then sent on every request. There is **no request signing**.

Two things a non-Node client should know about headers:
- The browser SDK also sends `x-device-id`, a server-issued device token fetched from `GET public/device-token` after login (0.0.57). It is best-effort: when it is missing nothing breaks, "this device" and per-device sign-out are simply not anchored. A backend client can omit it.
- The **org-token surfaces** use `Authorization` instead of `x-session-id`: the console's own REST API ([org-api.md](./org-api.md), `Authorization: <orgId>:<secret>`, Bearer prefix tolerated) and the `@buildbase/sdk/server` content client (`Authorization: Bearer <orgId>:<secret>`). Do not send `x-session-id` to those.

**`orgId` is never a header.** Depending on the endpoint it appears as:
- a **path segment** for public/unauthenticated endpoints: `/api/v1/public/{orgId}/plans/{slug}`, `/api/v1/public/{orgId}/credit-packages`, `/api/v1/public/{orgId}/settings`, and the tracking, consent, checkout-return, agent-readiness and invitation-preview routes
- a **query param** for beta config (`?orgId=...`) and the tracking config (`?clientId=`, with `orgId` in the path)
- a **body field** for the OAuth `auth/request` call, the beta submit, and the token exchange (inside the `<orgId>:<secret>` token)

For all normal authenticated calls, orgId is **not sent at all** - the server infers the org from the session.

## 3. Standard headers

| Header | When |
|---|---|
| `x-session-id: <token>` | whenever you have a session (all session-authenticated calls) |
| `x-device-id: <deviceToken>` | sent by the browser SDK; optional for any other client |
| `Authorization: Bearer <orgId>:<secret>` | the org-token surfaces only (org API, content client); never alongside `x-session-id` |
| `Content-Type: application/json` | only when sending a body |

No `Accept`, no User-Agent required. You may add your own custom headers freely.

## 4. Request & response format

- **Request bodies** are JSON. **GET parameters** are query-string (`?quotaSlug=...&page=1&limit=20`).
- **Path IDs** are interpolated into the URL and **every interpolated segment is URL-encoded** (since 0.0.51 the SDK builds paths through one tagged template that encodes each value). Do the same when replicating.
- **Responses come in two shapes**, depending on endpoint:
  1. **Bare JSON** - the body *is* the object (most endpoints).
  2. **Enveloped** - `{ "success": true, "data": { ... }, "message": "..." }`. When `success` is present and `false`, treat it as an error using `message`.

  A robust client handles both: if the JSON has a `success` field, unwrap `data`; otherwise use the body directly.

## 5. Errors

- Non-2xx responses carry a JSON body shaped like `{ "message": "..." }` or `{ "error": "..." }`. Read `message` first, then `error`.
- **401** means the session is invalid/expired - re-authenticate. (The SDK fires an `onUnauthorized` callback; there is **no automatic token refresh** - sessions don't refresh, you re-login.)
- **402** on `credits/consume` specifically means insufficient credits; the body includes `available` and `requested`. (The SDK surfaces this as error code `INSUFFICIENT_CREDITS`.)
- The SDK retries only on **5xx and network errors** (never 4xx), with exponential backoff, and only if you opt in (`maxRetries`). Default timeout 30s.

## 6. Idempotency

There is **no idempotency header**. Idempotency is an **optional body field** `idempotencyKey` on the write endpoints that support it: `usage` (single + per-item in batch) and `credits/consume`. Send a stable unique key to make a write safe to retry without double-applying.

It does work - a repeated key does not double-count. What catches people is the shape of the *replay*, because a deduplicated call is reported as a success, not as a conflict:

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
- **Webhook verification** is HMAC-SHA256 - every language has this in its standard library. Recipe and the full event catalog in [webhooks.md](./webhooks.md).

That's it. There is no proprietary protocol - if you can make HTTPS requests and compute an HMAC, you can use all of Buildbase from any language.
