# Common Errors and Fixes

Checked against `@buildbase/sdk` 1.8.0. The full list of coded errors is `node_modules/@buildbase/sdk/docs/ERROR_CODES.md`; match on an error's `code` and `status`, never on its message.

## Contents

- [Configuration Errors](#configuration-errors) - orgId, serverUrl, version, environment, empty env values, the wrong region
- [Authentication Errors](#authentication-errors) - the code exchange, cookies, cross-site refusals, session restore
- [Billing and Plan Refusals](#billing-and-plan-refusals) - 402 plan refusals, 409 `IDEMPOTENCY_KEY_REUSED`, 429
- [Server, Org API and CLI Errors](#server-org-api-and-cli-errors) - `ADMIN_SCOPE_REQUIRED`, the server client's codes, `init` exit codes
- [Webhook Errors](#webhook-errors) - signature failures and duplicate deliveries
- [Workspace / Gate Issues](#workspace--gate-issues) - gates and feature flags not rendering
- [Styling Issues](#styling-issues) - missing CSS import
- [TypeScript and Build Errors](#typescript-and-build-errors) - missing types and exports, `"use client"` boundaries
- [Performance Issues](#performance-issues) - excessive re-renders

## Configuration Errors

### `Invalid orgId: "...". Must be a valid MongoDB ObjectId (24 hexadecimal characters).`

**Cause**: The provider was given an `orgId` that is not exactly 24 hexadecimal characters.

```tsx
// ❌ Wrong
orgId="my-org"
orgId="123"

// ✅ Correct
orgId="507f1f77bcf86cd799439011"  // 24 hex characters
```

**Where to find it**: the console, **Settings** > **General**, or the dialog shown when you create an auth client.

An env value with whitespace or quotes does the same:

```ts
// Debug
console.log('orgId length:', process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID?.length);
console.log('orgId:', JSON.stringify(process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID));
```

---

### The app renders but BuildBase does nothing (an empty orgId or client id)

**Cause**: an env value is not filled in yet. Since 1.x an empty value no longer crashes the page:

- `SaaSOSProvider` with no `serverUrl` or `orgId` renders the app, warns once in the browser console naming the missing prop, and its hooks report `not_configured` (`NOT_CONFIGURED_CODE`, status 0: nothing was sent).
- The provider `init` writes renders the app without BuildBase at all until org id, client id and redirect URL are all set.
- On the server, `BuildBase({ orgId: '' })` does not throw when called; the first call that reaches the platform throws `BuildBase: orgId is required, and BuildBase({ orgId }) was given an empty value. Set the environment variable it is read from (NEXT_PUBLIC_BUILDBASE_ORG_ID in Next.js, BUILDBASE_ORG_ID on Express or Remix, ...)`. An empty `serverUrl` still throws at once: `BuildBase: serverUrl is required`.

**Fix**: fill in `.env.local` and restart the dev server (env changes do not hot-reload).

---

### `Invalid serverUrl: "...". Must be a valid URL.`

**Cause**: The `serverUrl` must include the protocol.

```tsx
// ❌ Wrong
serverUrl="api.console.buildbase.app"
serverUrl="buildbase.app"

// ✅ Correct (this is the fixed hosted value)
serverUrl="https://api.console.buildbase.app"
// ✅ Or your own tenant server's URL if self-hosting
serverUrl="https://buildbase.example.com"
```

---

### `Invalid version: "...". Only "v1" is currently supported.`

```tsx
// ❌ Wrong
version="v2"
version={2}
version="v1"   // passes at runtime, but fails tsc: the prop is typed as the ApiVersion enum

// ✅ Correct
import { ApiVersion } from '@buildbase/sdk';
version={ApiVersion.V1}
```

Import `ApiVersion` from the root entry, `@buildbase/sdk`. In a server file (a Next.js layout) importing it from `@buildbase/sdk/react` fails `next build`; see [TypeScript and Build Errors](#typescript-and-build-errors).

---

### `Invalid environment: "...". Use the environment's key from the console (eight lowercase letters), or leave it unset for production.`

**Cause**: `environment` (on `SaaSOSProvider`, `BuildBase()`, `createAgentStack` or `BuildBaseTracking`) is not a development or staging environment's key. Pass the key, not the environment's display name, and leave it unset (or empty in `.env.local`, read as `|| undefined`) for production. It is never inferred from `NODE_ENV`.

Calls made in an environment can also answer:

| Code | Status | Meaning |
|---|---|---|
| `ENVIRONMENT_NOT_FOUND` | 404 | The key is not declared, or is archived, for this organization |
| `ENVIRONMENT_UNAVAILABLE` | 503 | The platform could not confirm the environment exists. Retried by the SDK; never a reason to sign out |
| `ENVIRONMENT_PLAN_UNPUBLISHED` | 503 | The plan non-production environments run on is not published |

---

### `BuildBase: apiToken must be an org API token of the form <orgId>:<secret>`

**Cause**: `BuildBase({ apiToken })` was given something other than an org API token (a client secret, a session id, a console token). Create an API key in the console and pass it from a server-only env var.

---

### `421 misdirected_request`

**Cause**: the request went to the wrong cell. The body (no `code`) names the organization's `cellId` and `serverUrl`.

**Fix**: use the `serverUrl` the error names (an app serving one organization bakes it into its build). An app serving many organizations resolves per request with `resolveServerUrl({ orgId, centralUrl, apiKey })` and, on a 421, calls `clearResolvedServerUrl(...)` and resolves again, once. Today every organization is on `https://api.console.buildbase.app`; never guess a regional hostname.

---

## Authentication Errors

### `BuildBase: getSessionId callback is required for authenticated calls.`

**Cause**: You're using an exported action (e.g., `workspace.list()`) without providing `getSessionId` in `BuildBase()` config, and without calling `withSession()`.

```ts
// ❌ Wrong: no getSessionId, calling authenticated method directly
const bb = BuildBase({ serverUrl, orgId });
await bb.workspace.list(); // throws

// ✅ Option 1: provide getSessionId (Next.js)
const bb = BuildBase({ serverUrl, orgId, getSessionId: async () => ... });
await bb.workspace.list();

// ✅ Option 2: use withSession() (Express/background jobs)
const { workspace } = bb.withSession(sessionId);
await workspace.list();
```

---

### Back from sign-in but not signed in: `Sign-in failed (401): Invalid client secret`

**Cause**: the code exchange in your `/api/auth/token` route was refused. The route `init` writes (and [quick-start.md](../sdk/quick-start.md) Step 4) passes the platform's sentence through, and the provider throws it as `Sign-in failed (<status>): <message>`.

`exchangeCode` / `exchangeAuthCode` / `createAuthHandler` throw an `AuthCodeExchangeError` with the platform's `status`, `code` and sentence, never the secret:

| What you see | Cause |
|---|---|
| "Invalid client secret" (401) | `BUILDBASE_CLIENT_SECRET` is wrong. It is shown once, when the client is created; **Regenerate** it on the client if lost |
| "Invalid or expired authorization code" | The code was already used (a reload of the callback URL) or is old: sign in again |
| `not_configured` (status 0) | The org id, client id or secret is empty on the server: nothing was sent |
| `network_error`, `timeout` (status 0) | The platform could not be reached from your server |
| `missing_code` (400) | The route got no `code` in its JSON body |

---

### `/api/auth/token` or `/api/auth/signout` answers 415 or 403

**Cause**: `refuseCrossSiteAuthPost(request)` refused it (login CSRF protection, in the routes `init` writes since 1.x and in `createAuthHandler`): `415` when the body is not `Content-Type: application/json`, `403` when an `Origin` header names another host or is `null`. Neither sets a cookie.

**Fix**: send `headers: { 'Content-Type': 'application/json' }` on **both** the token POST and the sign-out POST in your provider callbacks (a provider written by an older `init` lacks it on sign-out), and call your own routes from your own origin.

---

### "Invalid redirect URL" or "This app has no sign-in methods yet." on the sign-in page

- **Invalid redirect URL**: the `redirectUrl` your provider sent is not on the auth client's **Redirect URLs** in the console. Add it exactly: scheme, host, port and path (a `localhost` address matches any port).
- **No sign-in methods**: add a method on the **Methods** tab of Authentication and tick it on the client.
- **The code or magic link never arrives**: no email sender is connected (**Messaging** > **Sender accounts**).

---

### `OAUTH_STATE_INVALID` reported to `onError`

**Cause**: the page loaded with a `?code=` whose `state` is missing, was not issued by this browser's `signIn()`, or was already used (usually a sign-in link someone else sent). The code is not exchanged and is removed from the URL; whoever was signed in stays signed in. Start sign-in with `signIn()` from your app, not by pasting a hosted sign-in URL.

---

### User can sign in but session doesn't persist on refresh

**Cause**: The token route sets one cookie and the session route reads another, or the cookie is never set.

**Debug steps**:
1. Check that `/api/auth/token` sets the cookie with `httpOnly: true`
2. Check that `/api/auth/session` reads from the same cookie name (both import `SESSION_COOKIE_NAME`)
3. In browser DevTools → Application → Cookies, look for `bb-session-id` (or `bb-session-id-<key>` when `NEXT_PUBLIC_BUILDBASE_ENVIRONMENT` is set)
4. On a plain-`http` host, a cookie set with `secure: true` is dropped by the browser: the routes `init` writes set `secure` from the request's protocol, not from `NODE_ENV`

```ts
// Ensure cookie name is consistent (src/lib/buildbase.ts)
export const SESSION_COOKIE_NAME = 'bb-session-id';

// In /api/auth/token: set it
response.cookies.set(SESSION_COOKIE_NAME, sessionId, { httpOnly: true, ... });

// In /api/auth/session: read it
const sessionId = (await cookies()).get(SESSION_COOKIE_NAME)?.value ?? null;
```

---

### handleAuthentication returns undefined sessionId

**Cause**: Your `/api/auth/token` endpoint isn't returning `sessionId`, or the response shape is wrong.

```ts
// ✅ Your endpoint must return sessionId in the response
return NextResponse.json({ sessionId });

// ✅ Your callback must return { sessionId: string }, and should throw on a failed exchange
handleAuthentication: async (code: string) => {
  const res = await fetch('/api/auth/token', { ... });
  const body = (await res.json()) as { sessionId?: string; message?: string };
  if (!res.ok || !body.sessionId) throw new Error(`Sign-in failed (${res.status}): ${body.message ?? 'no session'}`);
  return { sessionId: body.sessionId };
}
```

---

### "Users get signed out" or "a sign-in prompt flashes" on page load

**Cause**: the app treats `!isAuthenticated` as signed out while the session is still being restored.

- The provider renders the app while it restores a stored session; `useSaaSAuth().isLoading` is `true` until the API answers. Gate on it. Do not redirect to a login page or call `signIn()` while it is `true`.
- `isSessionUnverified: true` means a session is stored but the API could not confirm it (no answer, an 8 s timeout, a gateway page, a 5xx or a 429). The SDK keeps the session and retries with backoff and on the browser's `online` event. Show "can't reach the server"; never sign the user out yourself.
- A session ends only when the API refuses it: a 401, 403 or 404 on the page-load profile check clears it and calls `onSessionExpired('expired')`.

---

### A company refuses access, but the user stays signed in

These are refusals by the user's company network or policy, not by the session. `isAccessRefused(error)` is true for them, they are reported through `onAccessRefused` (or `useAccessRefused()`), and the session is kept, never signed out:

| Code | Status | Meaning |
|---|---|---|
| `ip_not_allowed` | 403 | The request came from outside the company's IP allowlist |
| `tenant_restricted` | 403 | The network's proxy names companies of this app in its `allowed-company-ids` header, and this account is not one of theirs; it works off that network |
| `tenant_header_invalid` | 400 | The network's proxy sent `allowed-company-ids` twice; the company's IT team fixes the proxy |
| `workspace_access_refused` | 403 | The company's stricter rules for one of its workspaces (`reason`, `workspaceId`); the session works in every other workspace. `useWorkspaceAccess(workspaceId)` offers the way back in |

Related session refusals that never sign anyone out: `reauth_required` (403: re-confirm with `useSaaSAuth().requireReverification()`, `isReauthRequired(error)`), `read_only_session` (403: an app owner is viewing as the user) and `AGENT_TENANT_MISMATCH` (401: an agent's token used against another environment than the one it was minted for; connect the agent again from the right environment).

---

## Billing and Plan Refusals

### 402 `PLAN_LIMIT_REACHED`, `QUOTA_EXHAUSTED`, `FEATURE_NOT_IN_PLAN`

**Cause**: the call would go past what the plan allows. The thrown error keeps the platform's numbers; read them typed with `planRefusalOf(err)` (null for any other error) instead of parsing the message:

```ts
import { planRefusalOf } from '@buildbase/sdk';

try {
  await workspace.create({ name: 'Another workspace' });
} catch (err) {
  const refusal = planRefusalOf(err);
  if (refusal?.code === 'PLAN_LIMIT_REACHED') {
    // refusal.limitSlug, refusal.limit, refusal.current, refusal.upgradeTarget, refusal.upgradePath
  } else if (refusal?.code === 'QUOTA_EXHAUSTED') {
    // refusal.quotaSlug, refusal.included, refusal.consumed, refusal.wanted, refusal.resetsAt
  } else if (refusal?.code === 'FEATURE_NOT_IN_PLAN') {
    // refusal.feature
  } else {
    throw err;
  }
}
```

Show an upgrade path, not a generic error. The SDK's own screens already say each one with its numbers in the reader's language. A ceiling the person cannot buy past (the org's own cap) is `403 CEILING_REACHED`, deliberately with no plan or numbers.

---

### 409 `IDEMPOTENCY_KEY_REUSED` on a checkout, plan change or add-on purchase

**Cause**: billing writes (`createCheckoutSession`, `updateSubscription`, `purchaseAddOn`, `purchaseCredits` and the other calls that change a Stripe subscription) send an `Idempotency-Key`, a new one per call unless you pass your own as the last argument. 409 means that key was sent before with a different request (another plan, quantity or body), or the checkout it opened has closed since. Nothing new was created in Stripe.

**Fix**: a retry of the *same* action sends the *same* key and body (the platform answers with the first try's result); a new action takes a new key. Never derive a key from the add-on and quantity, or two purchases of the same add-on read as one. `purchaseAddOn` puts the key it sent on every error it throws (`err.idempotencyKey`).

For metering, pass `idempotencyKey` on `usage.record`, `usage.recordBatch`, `credits.consume` and `credits.reserve`, derived from the unit of work (`gen-<requestId>`), never a fresh UUID per attempt: the SDK does not retry a failed POST for you, and a caller's retry without a key bills twice.

---

### 429 `rate_limited`

Idempotent calls (GET, HEAD, OPTIONS, PUT, DELETE) and writes sent with an `Idempotency-Key` are retried twice on a 429 or a 503, waiting out `Retry-After` up to 10 seconds (`maxRetries` sets the count, `0` turns it off). After that the error carries `code: 'rate_limited'` (`RATE_LIMITED_CODE`) and `retryAfterSeconds`. Back off; do not loop.

---

## Server, Org API and CLI Errors

### 403 `ADMIN_SCOPE_REQUIRED`

**Cause**: an end user's session or sign-in token, or an app-server API key, reached a route that changes what the org sells or how it is set up (the catalog, coupons, Stripe credentials, org settings, blueprints).

**Fix**: use an **admin key** (an org API key issued with the owner or admin role) as `BUILDBASE_API_TOKEN`, for example for `npx @buildbase/sdk blueprint apply`. It is never a 401, so nobody is signed out. Its sibling `CONSOLE_SESSION_REQUIRED` (403) means only a person signed in to the console may call that route; no API key can.

---

### `BuildBaseApiError` from `@buildbase/sdk/server` (`emails`, `subscribers`, `commerce`)

| Code | Status | Fix |
|---|---|---|
| `API_KEY_REQUIRED` | 403 | A console session, not an org API key, called the server API |
| `RECIPIENT_SUPPRESSED` | 422 | The address bounced, is a spam trap or unsubscribed |
| `SEND_LIMIT_REACHED` | 429 | Too many API sends to that address in the last hour, or the org's daily API budget |
| `IDEMPOTENCY_KEY_REUSED` | 422 | The `idempotencyKey` was used in the last 24 hours with a different request; nothing was done (`IdempotencyKeyReusedError`) |
| `IDEMPOTENCY_IN_PROGRESS` | 409 | A request with this key is still running; retry shortly with the same key |
| `UNKNOWN_REFERENCE` | 422 | A tag, list or template id that does not exist; `field` names which |
| `NO_SENDER_CONFIGURED` | 409 | The organization has no working email sender |
| `API_KEYS_SUSPENDED`, `SENDING_SUSPENDED` | 403 | Set by BuildBase on the organization; retrying does not help, contact support |

A missing grant on the key's API role is a plain `401` with no code. Note the status difference: the server API's `IDEMPOTENCY_KEY_REUSED` is a **422**, the billing writes' is a **409**.

---

### `buildbase init` exit codes

| Exit | Meaning |
|---|---|
| `0` | Done, or `already configured` (nothing changed) |
| `1` | An error, such as `.env.local` could not be written |
| `2` | Usage or refusal: no `--org-id` in a non-interactive run (`paste the organization id from console.buildbase.app as --org-id <24 hex chars>`), the framework could not be told from `package.json` (pass `--framework`), an empty directory without `--framework nextjs` / `--yes`, a Pages Router-only Next.js app (init writes App Router files), or `--claim` refused because `.env.local` already names an organization |
| `3` | `--claim`: the daily limit of claimable organizations for that email address |
| `4` | `--claim`: the platform has none to offer (an older platform answered 404) |
| `5` | `claim-code`: the key was refused, because the organization was claimed (the key ends then) or expired. Copy permanent keys from the console or run `npx @buildbase/sdk init --dev` |

Other commands: `blueprint plan` exits `0` when the org matches the file, `2` when it differs and `1` on an error (a usage error included); `login` exits `3` denied and `4` expired; `agent doctor` and `agent-ready check` exit `1` when a check fails and `2` on a usage error. Outside a project with the SDK installed, run `npx @buildbase/sdk <command>`, never `npx buildbase` (the unscoped package is not ours).

---

## Webhook Errors

### Every delivery is 401 / `parseWebhookEvent` returns null

**Causes**, in order of likelihood:
1. The body was parsed before verifying. Verify against the **raw** text: `await request.text()` in a Next.js route, `express.raw({ type: 'application/json' })` in Express. `request.json()` re-serializes and breaks the signature.
2. `BUILDBASE_WEBHOOK_SECRET` is the wrong endpoint's secret, or was rotated (**Rotate secret** signs new events with the new secret at once).
3. The `x-buildbase-timestamp` is older than 5 minutes (`maxAgeSeconds`, default 300): a clock problem on your server, or a replay.

---

### The same event is handled twice

**Cause**: a failed delivery is retried with the same `event`, `timestamp` and `data`.

**Fix**: deduplicate on `event.id` (starts `evt_`, the same on every endpoint and every retry, also sent as the `x-buildbase-event-id` header): store the ids you handled and skip a repeat before any side effect. `id` is optional in the type, because a delivery from a platform release older than event ids has none; fall back to a hash of the raw body then.

---

## Workspace / Gate Issues

### WhenSubscription renders nothing (even though there IS a subscription)

Most likely causes:
1. **Loading state**: the gate returns null while loading. Add `loadingComponent` to verify.
2. **No current workspace**: the gate reads the current workspace's subscription.
3. **Subscription on wrong workspace**: you're checking the wrong workspace.
4. **Not live**: by default only a live subscription counts (active, trialing, or past due while Stripe retries). One suspended by dunning does not; `status="any"` counts every status.

```tsx
// Debug loading vs condition-not-met
<WhenSubscription
  loadingComponent={<span style={{ color: 'orange' }}>LOADING...</span>}
  fallbackComponent={<span style={{ color: 'red' }}>NO SUBSCRIPTION</span>}
>
  <span style={{ color: 'green' }}>HAS SUBSCRIPTION</span>
</WhenSubscription>
```

---

### Feature flags always return false

**Causes**:
1. The slug doesn't match the console's Feature ID exactly
2. The feature is not defined in the console, or is not switched on (a new flag is off for everyone)
3. The feature is not granted to this workspace: not on its plan's published version, or not allowed to it
4. You are checking the wrong kind: workspace features and user features are separate lists

**Fix**:
```tsx
// Debug: log the current workspace's features (for WhenWorkspaceFeatureEnabled)
const { currentWorkspace } = useSaaSWorkspaces();
console.log('Workspace features:', currentWorkspace?.features);

// ...or the user's features (for WhenUserFeatureEnabled)
const { features } = useUserFeatures();
console.log('User features:', features);

// Verify the slug matches the console's Feature ID exactly
<WhenWorkspaceFeatureEnabled slug="advanced-analytics">
```

The feature gates take only `slug` and `children` (`WhenWorkspaceFeatureEnabled` also `whileUnknown`); for the "otherwise" branch use `WhenWorkspaceFeatureDisabled`, not a `fallbackComponent`.

---

## Styling Issues

### SDK components look unstyled

**Cause**: The CSS import is missing.

```tsx
// app/layout.tsx: must be at root level
import '@buildbase/sdk/css';
```

This is required. The SDK uses Tailwind CSS with a prefix, bundled as a separate CSS file.

---

## TypeScript and Build Errors

### Type error: "Property 'xxx' does not exist on type 'IWorkspace'"

Import the types that the package actually exports:

```tsx
import type { ISubscriptionResponse, ISubscription, IPlan } from '@buildbase/sdk';
```

Since SDK 0.0.53 the public model types **are** exported by name from both `@buildbase/sdk` and `@buildbase/sdk/react`: `IUser`, `IWorkspace`, `ISettings` and `TranslationKey`, alongside `ISubscriptionResponse`, `ISubscription`, `IPlan` and the credit, quota and invoice `I*` types. Import them directly. Earlier guidance to infer `IWorkspace` or `IUser` from a hook's return type is obsolete. A profile read (`getProfile()`) resolves to `IUserProfile`: read `profile.id`, not `_id`.

---

### "Module '@buildbase/sdk/react' has no exported member 'xxx'"

Two causes:

1. **It is a server toolkit.** `BuildBase` (the factory), `parseWebhookEvent`, `verifyWebhookSignature`, `isWebhookEvent`, agent discovery and the OAuth2 app bridge exist only in `@buildbase/sdk`, never in `/react`. A client file that needs one (say `isWebhookEvent` in a settings UI) imports it from `@buildbase/sdk`, which has no React and bundles for the browser.
2. **It is newer than your installed version.**

```bash
npm list @buildbase/sdk  # Check installed version
npm install @buildbase/sdk@latest  # Update to latest
```

The installed package's own `node_modules/@buildbase/sdk/AGENTS.md` and `agents/*.md` list every export per entry, checked against the build.

---

### `next build` fails in a layout or other server file that imports from `@buildbase/sdk/react`

**Cause**: `@buildbase/sdk/react` is a `"use client"` boundary. A server layout that reads an enum such as `ApiVersion` from it fails `next build`.

**Fix**: import `ApiVersion` (and every other non-React value) from the root entry, `@buildbase/sdk`, and keep the provider in its own `'use client'` file. Never import `@buildbase/sdk/react` in an API route, server action, webhook or cron: it pulls React in.

---

## Performance Issues

### Component re-renders excessively during workspace switches

**Cause**: Creating new callback functions on every render of a component that re-renders often.

```tsx
// ❌ New functions created on every render
<SaaSOSProvider
  auth={{
    callbacks: {
      getSession: async () => { ... },        // New function every render
      handleAuthentication: async (code) => { ... },  // New function every render
    }
  }}
>

// ✅ Define callbacks outside the component or use useMemo
const authCallbacks = useMemo(() => ({
  getSession: async () => { ... },
  handleAuthentication: async (code: string) => { ... },
  onSignOut: async () => { ... },
}), []);

<SaaSOSProvider auth={{ clientId, redirectUrl, callbacks: authCallbacks }}>
```

The SDK memoizes the callbacks object by each function's reference, so a new object around the same functions costs nothing, but new functions on every render still re-run its effects. The provider `init` writes lives in the root layout, which rarely re-renders, so it is fine as written.
