# Using Buildbase from Any Backend Language

There is no official Buildbase SDK for Python, Go, Ruby, PHP, Java, etc. — but you don't need one. The SDK is a thin wrapper over HTTP+JSON, so you can do everything it does with your language's HTTP client plus one header. This guide shows the end-to-end flow and minimal examples.

Read [overview.md](./overview.md) and [endpoints.md](./endpoints.md) for the full contract; [webhooks.md](./webhooks.md) for inbound verification.

## Contents

- [The whole model in four facts](#the-whole-model-in-four-facts) — core concepts in brief
- [Step 1 — Log the user in and get a `sessionId`](#step-1--log-the-user-in-and-get-a-sessionid) — OAuth-style login flow
- [Step 2 — Call any endpoint](#step-2--call-any-endpoint) — Python and Go examples
- [Step 3 — Server-to-server, jobs, acting for a user](#step-3--server-to-server-background-jobs-and-acting-for-one-of-your-app-users) — token exchange
- [Step 4 — Webhooks](#step-4--webhooks) — verifying inbound webhooks
- [What you must implement yourself (no single endpoint)](#what-you-must-implement-yourself-no-single-endpoint) — permission and feature checks
- [Honest limits](#honest-limits) — caveats about this reference

---

## The whole model in four facts

1. **Base URL:** `https://api.console.buildbase.app/api/v1/public/<path>` (the hosted value; your own origin if self-hosting).
2. **Auth:** one header — `x-session-id: <sessionId>` — on every authenticated call.
3. **Data:** JSON bodies; query strings for GET params. Responses are JSON, sometimes wrapped in `{ success, data, message }`.
4. **You need two secrets from the dashboard** (console.buildbase.app): `clientId` + `clientSecret` (for the login exchange) and your `orgId`.

The only real "flow" is getting a `sessionId` for a user. After that, it's just authenticated HTTP.

---

## Step 1 — Log the user in and get a `sessionId`

This is the OAuth-style flow. Your backend acts as the confidential client (it holds the `clientSecret`).

1. **Send the user to Buildbase's login.** Either redirect them to your hosted login URL with your `clientId` and a redirect target, or call `POST /api/v1/auth/request` with `{ orgId, clientId, redirect: { success, error } }` and redirect the browser to the returned `data.redirectUrl`.
2. **User authenticates on Buildbase**, then is redirected back to your `redirect.success` URL with a one-time `?code=...`.
3. **Exchange the code for a session, server-side.** POST to the Buildbase token endpoint with your secret:

   ```
   POST https://api.console.buildbase.app/api/v1/auth/token
   Content-Type: application/json

   { "code": "<from ?code>", "clientId": "...", "clientSecret": "...", "orgId": "..." }
   ```

   Response: `{ "data": { "sessionId": "...", "user": { ... } } }`.

   > Source note: this token-exchange endpoint + response shape is taken from the official Next.js starter's server route, not from the SDK client package (the browser SDK uses a simpler client-only path). For a backend in any language, this **server-side exchange is the correct, secure flow** because your backend can safely hold the `clientSecret`.

4. **Store the `sessionId`** in your own session store / signed cookie (treat it like a session token — keep it server-side, e.g. an httpOnly cookie).
5. **Use it** on every subsequent call as `x-session-id`.

To validate a session later, call `GET /api/v1/public/profile` with the header — a 401 means it's no longer valid (re-login; sessions don't auto-refresh).

---

## Step 2 — Call any endpoint

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

Any language with an HTTP client works the same way — set `x-session-id`, send/parse JSON, unwrap `{ success, data }` if present.

---

## Step 3 — Server-to-server, background jobs, and acting for one of your app users

<a id="acting-for-one-of-your-app-users"></a>

You do **not** need a browser login for this. An org API key can be exchanged for a session, which is the supported way for a backend or an agent to act as a user:

```
POST https://api.console.buildbase.app/api/v1/public/token/exchange
Content-Type: application/json

{ "token": "<orgId>:<secret>", "expiresIn": 2592000, "userId": "<optional>" }
```

Response: `{ "sessionId": "..." }`. Then send `x-session-id: <sessionId>` exactly as a browser session would.

Four things to get right:

- **`expiresIn` is seconds, optional, and both defaults to and caps at 30 days.** Get one session and reuse it rather than exchanging per request; the endpoint is rate limited to 10/min.
- **Omit `userId` and the session belongs to the key's creator**, not to a service identity. Pass the `userId` you mean to act as. Mint the key from a least-privilege API role either way, because a session inherits real permissions.
- **This is the org key crossing into the user plane**, so treat it as privileged. Keep the key server-side and never send it from a browser.
- The Node SDK's `withSession(sessionId)` wraps exactly this. There is nothing Node-specific about it.

For an agent acting on behalf of a signed-in user of *your* app, prefer the OAuth path instead, where the user consents and your app mints the token: [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md). Use token exchange for your own backend and jobs.

### Driving the console API instead

If the job is administrative - campaigns, workflows, collections, content, links, assets - that is a different surface with a different auth header, documented in [org-api.md](./org-api.md). Do not try to reach it with `x-session-id`.

---

## Step 4 — Webhooks

Verify inbound webhooks with HMAC-SHA256 — full recipe + Python/Go code in [webhooks.md](./webhooks.md).

---

## What you must implement yourself (no single endpoint)

- **Permission checks.** There's no "can this user do X?" endpoint. Fetch `GET workspaces/{id}`, `GET {orgId}/settings`, and `GET workspaces/{id}/users`, find the caller's role, and check the requested permission against that role's set (platform `workspace:*` perms + your app perms). See [endpoints.md](./endpoints.md#permissions).
- **Feature/quota "checks."** Fetch the feature map (`users/features` or `workspaces/features`) or quota status, then decide in your code. There's no boolean-check endpoint.

---

## Honest limits

- The endpoint catalog here is reverse-engineered from the SDK source, so it is accurate for what the SDK sends, but the server exposes far more than the SDK uses. Two places to confirm against: the package README on npm (`npmjs.com/package/@buildbase/sdk`, and `unpkg.com/@buildbase/sdk/README.md` for the raw file), and [docs.buildbase.app](https://docs.buildbase.app). The console's own REST API is a separate surface entirely, documented in [org-api.md](./org-api.md).
- Request/response field lists reflect what the SDK's TypeScript types declare; servers can return extra fields. Treat responses leniently (ignore unknown fields).
- The token-exchange endpoint shape (`/api/v1/auth/token`) comes from the official starter app, not the SDK package — verify against your dashboard's auth settings if it differs.
