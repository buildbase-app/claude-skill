# HTTP API — Overview (use Buildbase from any language)

The `@buildbase/sdk` package is a convenience wrapper around a plain HTTP+JSON API. **Nothing about that API is JavaScript-specific** — there's no request signing, no cookies required, no client-side crypto. Any backend language (Python, Go, Ruby, PHP, Java, C#, Rust…) can call it with an HTTP client and a session token in a header.

This section was reverse-engineered directly from the SDK source (`sdk/src/lib/api-base.ts`, `sdk/src/api/services/*.ts`, `sdk/src/lib/server-client.ts`), so it reflects exactly what the SDK actually sends — not docs that may drift.

> **Read next:** [endpoints.md](./endpoints.md) (the full endpoint catalog), [webhooks.md](./webhooks.md) (verify inbound webhooks in any language), [using-from-any-language.md](./using-from-any-language.md) (auth flow + Python/Go examples).

---

## 1. Base URL

```
{serverUrl}/api/{version}/{basePath}/{path}
```

- `serverUrl` — the hosted value is **`https://api.console.buildbase.app`** (or your own origin if self-hosting — point it at your tenant server, e.g. `https://api.yourcompany.com`; everything below is identical. To stand up that stack, use the **`buildbase-selfhost`** skill or see [docs.buildbase.app/self-hosted](https://docs.buildbase.app/self-hosted/overview)).
- `version` — `v1`.
- `basePath` — almost always **`public`**. (`beta` exists for a few beta endpoints; auth's `/auth/request` is the one exception that sits *outside* basePath.)

So a typical call is: `https://api.console.buildbase.app/api/v1/public/workspaces`.

## 2. Authentication — one header

```
x-session-id: <sessionId>
```

That's the whole auth scheme for normal calls. The `sessionId` is obtained once via the login/code-exchange flow (see [using-from-any-language.md](./using-from-any-language.md)) and then sent on every request. There is **no `Authorization` header, no bearer prefix, no request signing.**

**`orgId` is never a header.** Depending on the endpoint it appears as:
- a **path segment** for public/unauthenticated endpoints: `/api/v1/public/{orgId}/plans/{slug}`, `/api/v1/public/{orgId}/credit-packages`, `/api/v1/public/{orgId}/settings`
- a **query param** for beta config (`?orgId=...`)
- a **body field** for the OAuth `auth/request` call

For all normal authenticated calls, orgId is **not sent at all** — the server infers the org from the session.

## 3. Standard headers

| Header | When |
|---|---|
| `x-session-id: <token>` | whenever you have a session (all authenticated calls) |
| `Content-Type: application/json` | only when sending a body |

No `Accept`, no User-Agent required. You may add your own custom headers freely.

## 4. Request & response format

- **Request bodies** are JSON. **GET parameters** are query-string (`?quotaSlug=...&page=1&limit=20`).
- **Path IDs** are interpolated into the URL. Note: in the SDK, `slug`, `groupVersionId`, and `quotaSlug` are URL-encoded; other IDs (`workspaceId`, `userId`, `invoiceId`) are not. When replicating, **URL-encode any value that could contain special characters** to be safe.
- **Responses come in two shapes**, depending on endpoint:
  1. **Bare JSON** — the body *is* the object (most endpoints).
  2. **Enveloped** — `{ "success": true, "data": { ... }, "message": "..." }`. When `success` is present and `false`, treat it as an error using `message`.

  A robust client handles both: if the JSON has a `success` field, unwrap `data`; otherwise use the body directly.

## 5. Errors

- Non-2xx responses carry a JSON body shaped like `{ "message": "..." }` or `{ "error": "..." }`. Read `message` first, then `error`.
- **401** means the session is invalid/expired — re-authenticate. (The SDK fires an `onUnauthorized` callback; there is **no automatic token refresh** — sessions don't refresh, you re-login.)
- **402** on `credits/consume` specifically means insufficient credits; the body includes `available` and `requested`. (The SDK surfaces this as error code `INSUFFICIENT_CREDITS`.)
- The SDK retries only on **5xx and network errors** (never 4xx), with exponential backoff, and only if you opt in (`maxRetries`). Default timeout 30s.

## 6. Idempotency

There is **no idempotency header**. Idempotency is an **optional body field** `idempotencyKey` on the write endpoints that support it: `usage` (single + per-item in batch) and `credits/consume`. Send a stable unique key to make a write safe to retry without double-applying.

## 7. What is NOT pure HTTP (replication caveats)

Almost everything ports cleanly. The few things to know:

- **Permissions are computed client-side, not via an endpoint.** `permissions.check` / `permissions.resolve` in the SDK fetch *three* endpoints — `GET workspaces/{id}`, `GET settings`, `GET workspaces/{id}/users` — then combine the role→permissions matrix locally. To replicate in another language you must fetch those three and apply the same logic (find the user's role in the workspace, union the platform `workspace:*` permissions defined on the workspace/settings with the role's app permissions). See [endpoints.md](./endpoints.md#permissions) for the inputs.
- **The browser login UX** (redirect handling, reading `?code=` off the URL, localStorage) is browser glue. On a backend you do the equivalent server-side: receive the `?code=` at your redirect route and exchange it (see [using-from-any-language.md](./using-from-any-language.md)).
- **Webhook verification** is HMAC-SHA256 — every language has this in its standard library. Recipe in [webhooks.md](./webhooks.md).

That's it. There is no proprietary protocol — if you can make HTTPS requests and compute an HMAC, you can use all of Buildbase from any language.
