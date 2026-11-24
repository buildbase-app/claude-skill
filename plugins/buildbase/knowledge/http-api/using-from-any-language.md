# Using Buildbase from Any Backend Language

There is no official Buildbase SDK for Python, Go, Ruby, PHP, Java, etc. - but you don't need one. The SDK is a thin wrapper over HTTP+JSON, so you can do everything it does with your language's HTTP client plus one header. This guide shows the end-to-end flow and minimal examples.

Read [overview.md](./overview.md) and [endpoints.md](./endpoints.md) for the full contract; [webhooks.md](./webhooks.md) for inbound verification. For one operation's exact contract, the docs site generates a reference page per operation at [docs.buildbase.app/http-api](https://docs.buildbase.app/http-api) from the platform's OpenAPI document (`GET https://api.console.buildbase.app/api/v1/openapi.json`, which a code generator turns into a client in your language), and the hosted BuildBase MCP server's `get_api_operation` tool answers the same contract for `METHOD /path`.

## Contents

- [The whole model in four facts](#the-whole-model-in-four-facts) - core concepts in brief
- [Step 1 - Log the user in and get a `sessionId`](#step-1--log-the-user-in-and-get-a-sessionid) - OAuth-style login flow
- [Step 2 - Call any endpoint](#step-2--call-any-endpoint) - Python and Go examples
- [Step 3 - Server-to-server, jobs, acting for a user](#step-3--server-to-server-background-jobs-and-acting-for-one-of-your-app-users) - token exchange
- [Step 4 - Webhooks](#step-4--webhooks) - verifying inbound webhooks
- [What you must implement yourself (no single endpoint)](#what-you-must-implement-yourself-no-single-endpoint) - permission and feature checks
- [Honest limits](#honest-limits) - caveats about this reference

---

## The whole model in four facts

1. **Base URL:** `https://api.console.buildbase.app/api/v1/public/<path>` (the hosted value; your own origin if self-hosting).
2. **Auth:** one header, `x-session-id: <sessionId>`, on every session-authenticated call (the org-token surfaces use `Authorization` instead; see [overview.md](./overview.md#2-authentication---one-header-for-the-session-api)).
3. **Data:** JSON bodies; query strings for GET params. Responses are JSON, sometimes wrapped in `{ success, data, message }`.
4. **You need two secrets from the dashboard** (console.buildbase.app): `clientId` + `clientSecret` (for the login exchange) and your `orgId`. In a development or staging environment, the org id you send is `<orgId>-<key>`.

The only real "flow" is getting a `sessionId` for a user. After that, it's just authenticated HTTP.

---

## Step 1 - Log the user in and get a `sessionId`

This is the OAuth-style flow. Your backend acts as the confidential client (it holds the `clientSecret`).

1. **Send the user to Buildbase's login.** Either redirect them to your hosted login URL with your `clientId` and a redirect target, or call `POST /api/v1/auth/request` with `{ orgId, clientId, redirect: { success, error } }` and redirect the browser to the returned `data.redirectUrl`.
2. **User authenticates on Buildbase**, then is redirected back to your `redirect.success` URL with a one-time `?code=...`.
3. **Exchange the code for a session, server-side.** POST to the Buildbase token endpoint with your secret:

   ```
   POST https://api.console.buildbase.app/api/v1/auth/token
   Content-Type: application/json

   { "code": "<from ?code>", "clientId": "...", "clientSecret": "...", "orgId": "..." }
   ```

   Response: `{ "success": true, "data": { "sessionId": "...", "user": { ... } } }`. A refusal carries a sentence such as "Invalid client secret" or "Invalid or expired authorization code"; the code is good once.

   > Source note: since SDK 1.6.0 the SDK makes this exact call itself (`exchangeAuthCode` / `BuildBase().exchangeCode`, `sdk/src/lib/auth-code-exchange.ts`), so the body and answer above are what the SDK sends and reads. For a backend in any language, this **server-side exchange is the correct, secure flow** because your backend can safely hold the `clientSecret`. It is rate limited per address (300 a minute), which a backend serving all its users shares.

4. **Store the `sessionId`** in your own session store / signed cookie (treat it like a session token - keep it server-side, e.g. an httpOnly cookie).
5. **Use it** on every subsequent call as `x-session-id`.

To validate a session later, call `GET /api/v1/public/profile` with the header - a 401 means it's no longer valid (re-login; sessions don't auto-refresh).

---

## Step 2 - Call any endpoint

Pick from [endpoints.md](./endpoints.md). Examples:

### Python (`requests`)

```python
import requests

BASE = "https://api.console.buildbase.app/api/v1/public"

def bb_get(path, session_id, **params):
    r = requests.get(f"{BASE}/{path}", headers={"x-session-id": session_id}, params=params)
    r.raise_for_status()
    body = r.json()
    return body.get("data", body) if isinstance(body, dict) and "success" in body else body

def bb_post(path, session_id, payload):
    r = requests.post(f"{BASE}/{path}",
                      headers={"x-session-id": session_id, "Content-Type": "application/json"},
                      json=payload)
    r.raise_for_status()
    body = r.json()
    return body.get("data", body) if isinstance(body, dict) and "success" in body else body

# List the user's workspaces
workspaces = bb_get("workspaces", session_id)

# Record metered usage for a workspace (idempotent)
bb_post(f"workspaces/{ws_id}/subscription/usage", session_id, {
    "quotaSlug": "api_calls", "quantity": 1, "idempotencyKey": request_id,
})

# Consume 5 prepaid credits (handle 402 = insufficient)
import requests as _rq
resp = _rq.post(f"{BASE}/workspaces/{ws_id}/credits/consume",
                headers={"x-session-id": session_id, "Content-Type": "application/json"},
                json={"amount": 5, "idempotencyKey": gen_id})
if resp.status_code == 402:
    info = resp.json()  # { available, requested } → show "buy more credits"
```

### Go (`net/http`)

```go
func bbGet(path, sessionID string) (*http.Response, error) {
    req, _ := http.NewRequest("GET", "https://api.console.buildbase.app/api/v1/public/"+path, nil)
    req.Header.Set("x-session-id", sessionID)
    return http.DefaultClient.Do(req)
}

func bbPost(path, sessionID string, body []byte) (*http.Response, error) {
    req, _ := http.NewRequest("POST", "https://api.console.buildbase.app/api/v1/public/"+path,
        bytes.NewReader(body))
    req.Header.Set("x-session-id", sessionID)
    req.Header.Set("Content-Type", "application/json")
    return http.DefaultClient.Do(req)
}
```

Any language with an HTTP client works the same way - set `x-session-id`, send/parse JSON, unwrap `{ success, data }` if present.

---

## Step 3 - Server-to-server, background jobs, and acting for one of your app users

<a id="acting-for-one-of-your-app-users"></a>

You do **not** need a browser login for this. An org API key can be exchanged for a session, which is the supported way for a backend or an agent to act as a user:

```
POST https://api.console.buildbase.app/api/v1/public/token/exchange
Content-Type: application/json

{ "token": "<orgId>:<secret>", "expiresIn": 2592000, "userId": "<optional>" }
```

Response: `{ "sessionId": "...", "expiresIn": 2592000, "userId": "...", "orgId": "..." }`. Then send `x-session-id: <sessionId>` exactly as a browser session would. The echoed `userId` is worth asserting on in a job: it tells you which identity the session actually acts as, which is the thing that silently differs when `userId` is omitted. The body also takes an optional `workspaceId`: the user must be a member of it (403 `not_a_member` otherwise), and a user with no default workspace yet gets this one.

Five things to get right:

- **`expiresIn` is seconds, optional, and defaults to 30 days (2592000).** Thirty days is also the ceiling, and it is a refusal rather than a clamp: a larger value is rejected with `400 {"error":true,"path":"expiresIn","message":"Expires in must be 2592000 or less"}` and you get no session at all. Ask for less, never more (the floor is 60). Get one session and reuse it rather than exchanging per request; the endpoint is rate limited to 120 a minute per address by default (`TOKEN_EXCHANGE_PER_MINUTE` on a self-hosted server).
- **Omit `userId` and the session belongs to the key's creator**, not to a service identity. Pass the `userId` you mean to act as.
- **Only an `owner` or `admin` key may act for another user.** A key whose role is narrower (`user`, or a custom API role) that names someone else's `userId` is refused with 403 `impersonation_not_allowed`; it can still mint a session for its own user, which is what a single-purpose integration needs. So a job that acts for your app's users needs an admin-role key: keep that key on the server and treat it as the privileged credential it is. A blocked user is never signed in as (403), and naming one of a company's people is recorded in that company's audit trail and refused when the company does not allow it. Refusals answer `{ "success": false, "code", "message" }`.
- **This is the org key crossing into the user plane**, so treat it as privileged. Keep the key server-side and never send it from a browser.
- The Node SDK does **not** call this endpoint for you. `withSession(sessionId)` only binds a session id you already hold to a set of actions; do the exchange with one POST as above, then pass the returned `sessionId` to `withSession`. There is nothing Node-specific about either step.

For an agent acting on behalf of a signed-in user of *your* app, prefer the OAuth path instead, where the user consents and your app mints the token: [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md). Use token exchange for your own backend and jobs.

### Driving the console API instead

If the job is administrative - campaigns, workflows, collections, content, links, assets - that is a different surface with a different auth header, documented in [org-api.md](./org-api.md). Do not try to reach it with `x-session-id`. Sending a transactional email or upserting a subscriber from your backend needs no session either: `POST /api/v1/server/emails/send` and `PUT /api/v1/server/subscribers` with `Authorization: Bearer <orgId>:<secret>` ([endpoints.md](./endpoints.md#org-token-routes-the-sdk-calls)).

---

## Step 4 - Webhooks

Verify inbound webhooks with HMAC-SHA256 - full recipe, Python/Go code and the complete event catalog in [webhooks.md](./webhooks.md). Dedupe on the body's `id` (also the `x-buildbase-event-id` header), falling back to a hash of the raw body when an older platform sent none. Current platforms also send the Standard Webhooks headers, so a Standard Webhooks library in your language verifies a delivery too. Switch only on names from the catalog.

---

## What you must implement yourself (no single endpoint)

- **Permission checks for someone other than the caller.** `GET workspaces/{id}/permissions/me` (0.0.73) answers for the session's own user in one call. For another member there is no endpoint: fetch `GET workspaces/{id}`, `GET {orgId}/settings`, and `GET workspaces/{id}/users`, find their role, and check the permission against that role's set. See [endpoints.md](./endpoints.md#permissions).
- **Feature flag "checks."** Fetch the feature map (`users/features` or `workspaces/features`), then decide in your code; there is no boolean-check endpoint for a feature flag. For what a **plan** allows, read the composed entitlement instead: the subscription read carries it for a workspace, `GET me/subscription/entitlement` for the signed-in person, and with an org API token `GET /api/subscriptions/users/entitlements/check?slug=&subjects=` answers `allowed` per subject ([endpoints.md](./endpoints.md#limits-and-entitlements)).

---

## Honest limits

- The endpoint catalog here is read from the SDK source, so it is accurate for what the SDK sends, but the server exposes far more than the SDK uses. Places to confirm against: the generated API reference at [docs.buildbase.app/http-api](https://docs.buildbase.app/http-api) (or `get_api_operation` on the hosted BuildBase MCP server), the package's own agent docs (`node_modules/@buildbase/sdk/AGENTS.md`), and the README on npm (`npmjs.com/package/@buildbase/sdk`). The console's own REST API is a separate surface entirely, documented in [org-api.md](./org-api.md).
- Request/response field lists reflect what the SDK's TypeScript types declare; servers can return extra fields. Treat responses leniently (ignore unknown fields).
- The code exchange (`/api/v1/auth/token`) is the call the SDK itself makes since 1.6.0, so its body and answer are confirmed from the SDK source and the platform's route. Each operation's full contract, including routes the SDK never calls, is in the generated reference at [docs.buildbase.app/http-api](https://docs.buildbase.app/http-api).
