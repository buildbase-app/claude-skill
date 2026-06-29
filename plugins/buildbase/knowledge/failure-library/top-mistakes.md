# Top 30 Integration Mistakes

Organized from most common to most dangerous. Most bugs are in the first two categories.

## Contents

- **Setup & Configuration (1–8)** — orgId format, clientSecret in NEXT_PUBLIC_, missing CSS import, wrong version string, nested provider, missing auth endpoints, cookie name mismatch, env vars not loaded in production
- **Authentication (9–14)** — handleAuthentication return value, getSession undefined vs null, cookie not httpOnly, wrong token URL, signout not clearing cookie, silent code-exchange failure
- **Workspace & Billing (15–19)** — setCurrentWorkspace vs switchToWorkspace, checking features before workspace loads, onWorkspaceChange JWT, workspace mode mismatch, subscription not immediate after checkout
- **Feature Flags & Quota (20–24)** — feature slug missing in dashboard, feature not on plan, quota slug undefined, client-side recording of server-validated actions, missing idempotencyKey
- **Security Vulnerabilities (25–28)** — clientSecret exposed to browser, sessionId in localStorage, no auth check in API routes, webhook not signature-verified
- **Performance & Architecture (29–30)** — BuildBase() called per request, excessive re-renders from subscription context

---

## Setup & Configuration (Mistakes 1–8)

### Mistake 1: Wrong orgId Format

**What the developer did**: Set `orgId="mycompany"` or `orgId="my-app-name"` — a human-readable name.

**Symptom**: App crashes on load: `Error: Invalid orgId. Must be a 24-character hexadecimal string.`

**Why it happens**: The prop name sounds like an identifier you'd name yourself. The 24-hex-char constraint isn't obvious from the prop name alone.

**Detection**: Check `process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID?.length`. Must be exactly 24. Log `JSON.stringify(orgId)` to check for hidden whitespace or quotes.

**Recovery**: Open Buildbase dashboard → Settings → General → Organization ID. Copy the value exactly (it looks like `64a3f5b2c1d4e7890abc1234`). Paste into env var.

---

### Mistake 2: clientSecret in NEXT_PUBLIC_ Env Var

**What the developer did**: Set `NEXT_PUBLIC_BUILDBASE_CLIENT_SECRET=sk_...` in `.env.local`.

**Symptom**: App works normally, but the secret is embedded in the JavaScript bundle and visible to anyone who opens browser DevTools → Sources.

**Why it happens**: All SDK env vars are seen together; developers apply the same `NEXT_PUBLIC_` prefix pattern to all of them.

**Detection**: Run `grep -r "NEXT_PUBLIC_BUILDBASE_CLIENT_SECRET" .` in your project. Check `.env.local` and `.env.production`.

**Recovery**: Rename to `BUILDBASE_CLIENT_SECRET` (no `NEXT_PUBLIC_` prefix). Verify it's used only in server-side code (`/api/auth/token`). Rotate the secret in the Buildbase dashboard if it was already deployed.

---

### Mistake 3: Missing CSS Import

**What the developer did**: Installed and configured the SDK but didn't add `import '@buildbase/sdk/css'` to the root layout.

**Symptom**: SDK UI components (auth modal, workspace settings dialog, pricing page) render with broken or missing styles. Looks like a layout crash.

**Why it happens**: Most npm packages auto-include their styles. Explicit CSS imports are less common in modern tooling.

**Detection**: Search for `buildbase/css` in your codebase: `grep -r "buildbase/css" .`. If no results, the import is missing.

**Recovery**: Add `import '@buildbase/sdk/css'` to `app/layout.tsx` (Next.js App Router) or `pages/_app.tsx` (Pages Router). Must be at the top level, not inside a `'use client'` component.

---

### Mistake 4: Wrong Version String

**What the developer did**: Passed `version="v2"`, `version="1"`, or omitted the `version` prop on `SaaSOSProvider`.

**Symptom**: App throws a validation error on load about an invalid version.

**Why it happens**: The version requirement feels like boilerplate. Developers guess the format.

**Detection**: Check the `version` prop value on `SaaSOSProvider`. Only `'v1'` or `ApiVersion.V1` (imported from `@buildbase/sdk`) are valid.

**Recovery**: Use `version={ApiVersion.V1}` (import `ApiVersion` from `@buildbase/sdk`) or `version="v1"`. The `ApiVersion` enum is preferred as it's refactor-safe.

---

### Mistake 5: SaaSOSProvider Nested Inside Another SaaSOSProvider

**What the developer did**: Added a second `SaaSOSProvider` in a child component (e.g., inside a dashboard layout) with different config.

**Symptom**: Undefined behavior — context values may conflict, workspace state may not update correctly, subscription data may be stale or wrong.

**Why it happens**: React context providers can be nested for different values. Developers try to apply workspace-specific config by nesting.

**Detection**: Search your codebase for `SaaSOSProvider`: `grep -r "SaaSOSProvider" src`. More than one instance is a bug.

**Recovery**: Remove all but the outermost `SaaSOSProvider`. Use `onWorkspaceChange` callback to handle workspace-specific behavior. Use feature flags and permissions for workspace-level customization.

---

### Mistake 6: Missing Auth Endpoints

**What the developer did**: Added `SaaSOSProvider` with `getSession`, `handleAuthentication`, and `onSignOut` callbacks that call `/api/auth/session`, `/api/auth/token`, and `/api/auth/signout` — but never created those route files.

**Symptom**: Clicking "Sign In" redirects to Buildbase OAuth, returns with a `?code=` in the URL, but the user never gets signed in. `isAuthenticated` stays false.

**Why it happens**: The provider callbacks look like configuration, not implementation. Developers assume the SDK creates the routes.

**Detection**: Make a GET request to `/api/auth/session` in the browser. If you get a 404, the route doesn't exist.

**Recovery**: Create three route handlers:
- `app/api/auth/token/route.ts` — POST, exchanges code, sets cookie
- `app/api/auth/session/route.ts` — GET, reads cookie, returns sessionId
- `app/api/auth/signout/route.ts` — POST, clears cookie

See `knowledge/patterns/nextjs-integration.md` for full implementations.

---

### Mistake 7: Wrong Cookie Name Between Routes and Factory

**What the developer did**: Sets the cookie as `session-id` in `/api/auth/token` but reads it as `bb-session-id` in `/api/auth/session` (or vice versa). Or the factory's `getSessionId` reads a different cookie name than what's set.

**Symptom**: Session is set after login but not read back. `getSession` returns null on page refresh. User is logged out on every page reload.

**Why it happens**: The cookie name is a magic string that must be consistent across three places. Developers set it in one place and forget to update the others.

**Detection**: In browser DevTools → Application → Cookies, check what cookie name is actually set after login. Compare to what `/api/auth/session` reads and what the factory's `getSessionId` reads.

**Recovery**: Define the cookie name as a single constant: `export const SESSION_COOKIE_NAME = 'bb-session-id'` in `lib/buildbase.ts`. Import and use it in all three auth routes and the factory.

---

### Mistake 8: Env Vars Not Loaded in Production

**What the developer did**: Set env vars in `.env.local` which is not committed or deployed. Production build has missing env vars.

**Symptom**: App crashes in production with `Invalid orgId`, `Invalid serverUrl`, or `Cannot read properties of undefined` errors. Works fine in local dev.

**Why it happens**: `.env.local` is gitignored by default. Developers forget to set the same vars in their hosting provider (Vercel, Railway, Fly.io).

**Detection**: Check the hosting provider's environment variables dashboard. Log `process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID` in a server route — if undefined, the var isn't set.

**Recovery**: Add all required env vars to your hosting provider's environment variables section. For Vercel: Settings → Environment Variables. Remember: `NEXT_PUBLIC_` vars must also be added there (not just server-side vars).

---

## Authentication (Mistakes 9–14)

### Mistake 9: handleAuthentication Not Returning sessionId

**What the developer did**: Implemented `handleAuthentication` but returned `undefined`, `{}`, or `{ token: data.sessionId }` instead of `{ sessionId: data.sessionId }`.

**Symptom**: Auth flow appears to complete (no error, URL code is processed) but `isAuthenticated` remains false and the session doesn't persist.

**Why it happens**: The return type requirement (`{ sessionId: string }`) isn't enforced at the TypeScript level in all setups. Silent failure.

**Detection**: Add a `console.log` inside `handleAuthentication` to log the return value before returning. Check that it's `{ sessionId: "..." }` with a non-null string.

**Recovery**: The function must return `{ sessionId: string }` where sessionId is the actual Buildbase session token. Make sure `/api/auth/token` returns `{ sessionId: data.sessionId }` and that `handleAuthentication` returns the result correctly.

---

### Mistake 10: getSession Returning Undefined Instead of Null

**What the developer did**: `getSession` callback returns `undefined` when there's no session, instead of `null`.

**Symptom**: SDK may behave unexpectedly. Some internal checks distinguish `null` (no session) from `undefined` (error in callback). Auth state may not initialize correctly.

**Why it happens**: JavaScript developers often treat `undefined` and `null` as equivalent. They're not in this context.

**Detection**: Add logging to `getSession`: `console.log('session:', sessionId)`. If it logs `undefined` when no user is logged in, it's wrong.

**Recovery**: Return `null` explicitly: `return data.sessionId ?? null`. The nullish coalescing operator ensures `undefined` from missing cookie becomes `null`.

---

### Mistake 11: Session Cookie Not HttpOnly

**What the developer did**: Set the session cookie without the `HttpOnly` flag, making it accessible via `document.cookie`.

**Symptom**: No functional symptom — but the session is now vulnerable to XSS theft. Any injected script can steal the session token.

**Why it happens**: Developers copy a cookie-setting snippet that omits the security flags. The app "works" so the mistake isn't caught.

**Detection**: In browser DevTools → Application → Cookies → localhost. Check if the `bb-session-id` cookie has the HttpOnly checkbox checked. If not, it's missing the flag.

**Recovery**: In your `/api/auth/token` route, use `response.cookies.set()` with `{ httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'lax' }`. Never use `document.cookie` to set session cookies.

---

### Mistake 12: Token Endpoint Hitting Wrong Buildbase URL

**What the developer did**: In `/api/auth/token`, called `${serverUrl}/api/v1/auth/oauth2-token` or `${serverUrl}/auth/token` instead of `${serverUrl}/api/v1/auth/token`.

**Symptom**: The token exchange returns a 404 or an error. Auth fails. The developer sees a 401 or 404 in the server logs.

**Why it happens**: The exact URL path isn't prominently documented. Developers guess from the pattern.

**Detection**: Check the fetch call in `/api/auth/token`. Log the full URL being called and the response status.

**Recovery**: The correct endpoint is `${process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL}/api/v1/auth/token`. Body must include `code`, `clientId`, `clientSecret`, and `orgId`.

---

### Mistake 13: Signout Not Clearing the Cookie

**What the developer did**: The `POST /api/auth/signout` route returns `{ success: true }` but doesn't set `Max-Age: 0` on the cookie.

**Symptom**: Clicking "Sign Out" calls the endpoint (200 response), but the user remains signed in. Refreshing the page shows them as still authenticated.

**Why it happens**: Developers implement the "sign out" response but forget that clearing a cookie requires setting it again with `maxAge: 0`.

**Detection**: After clicking sign out, check browser DevTools → Application → Cookies. If `bb-session-id` still exists, the signout isn't clearing it.

**Recovery**: In the signout route, use `response.cookies.set(SESSION_COOKIE_NAME, '', { httpOnly: true, maxAge: 0, path: '/' })`. The `maxAge: 0` tells the browser to delete the cookie.

---

### Mistake 14: Code Exchange Failing Silently

**What the developer did**: The `/api/auth/token` route fails (wrong secret, network error) but returns a 200 response anyway, so the SDK doesn't know auth failed.

**Symptom**: Auth appears to "complete" — the code is processed, no error is shown — but the user isn't actually signed in. `isAuthenticated` stays false.

**Why it happens**: The route catches errors but returns `{ success: false }` with a 200 status instead of a 4xx. The SDK can't distinguish success from failure.

**Detection**: Add logging to the token route. Check what the Buildbase server returns when the code exchange fails. Ensure non-200 responses are returned on failure.

**Recovery**: Return `NextResponse.json({ error: 'Auth failed' }, { status: 401 })` when the exchange fails. The SDK will surface this as an auth error rather than silently doing nothing.

---

## Workspace & Billing (Mistakes 15–19)

### Mistake 15: setCurrentWorkspace Instead of switchToWorkspace

**What the developer did**: When the user clicks "Switch to Workspace", called `setCurrentWorkspace(workspace)` instead of `switchToWorkspace(workspace)`.

**Symptom**: The workspace visually changes in the UI, but `onWorkspaceChange` callback doesn't fire. The internal JWT for the developer's own API isn't refreshed. API calls use a stale workspace token.

**Why it happens**: `setCurrentWorkspace` sounds like the right function — "set the current workspace." The distinction between the two functions isn't obvious from the names.

**Detection**: Add logging to `onWorkspaceChange` callback. If switching workspaces doesn't trigger it, `switchToWorkspace` isn't being used.

**Recovery**: Use `switchToWorkspace(workspace)` (pass the workspace object, not an id) for user-initiated switches. It triggers all callbacks and loading states. Use `setCurrentWorkspace(workspace)` only for programmatic initialization where you don't want callback side effects.

---

### Mistake 16: Checking Workspace Features Before Workspace Loads

**What the developer did**: Checks `isFeatureEnabled('analytics')` or renders `WhenWorkspaceFeatureEnabled` before `currentWorkspace` is set.

**Symptom**: Feature flag always returns false on first load. After workspace selection, it works correctly.

**Why it happens**: Workspace data loads asynchronously. Feature checks before workspace load get the pre-load state (no features enabled).

**Detection**: Log `currentWorkspace` in the component where the feature check fails. If it's null when the check runs, that's the cause.

**Recovery**: Guard feature checks behind workspace loading: `if (!currentWorkspace) return null`. Or use `WhenWorkspaceFeatureEnabled` which handles loading state internally.

---

### Mistake 17: onWorkspaceChange Not Generating Internal JWT

**What the developer did**: Implemented workspace switching but didn't use `onWorkspaceChange` to generate a workspace-scoped JWT for their own API.

**Symptom**: After switching workspaces, API calls to the developer's own backend use the wrong workspace context. Data from the previous workspace appears.

**Why it happens**: The `onWorkspaceChange` callback isn't required for Buildbase API calls (the SDK handles session automatically). Developers don't realize their own API also needs to be informed about the workspace switch.

**Detection**: After switching workspaces, make an API call to your backend. Check what workspace it operates on.

**Recovery**: In `onWorkspaceChange`, call your `/api/auth/workspace-token` endpoint with the new workspace ID. Store the returned token (e.g., in localStorage or a React context). Use this token in Authorization headers for your own API calls.

---

### Mistake 18: Workspace Mode Mismatch

**What the developer did**: Configured Buildbase in Platform mode (multi-tenant) but is building a B2C app where each user has exactly one account. Or vice versa.

**Symptom**: In Platform mode for B2C: workspace creation UI appears for every user, confusing them. Each user has to "set up a workspace" to use the app. In Personal mode for B2B: users can't invite team members or create multiple workspaces.

**Why it happens**: The mode is set in the Buildbase dashboard and feels like a technical detail. Developers choose without understanding the implications.

**Detection**: The workspace setup step in the user onboarding flow reveals the issue. If users see workspace creation prompts when they shouldn't, or can't invite members when they should, the mode is wrong.

**Recovery**: Change workspace mode in Buildbase dashboard → Settings → Workspace. Personal mode = one user, one auto-created workspace (B2C). Platform mode = multi-user, multi-workspace (B2B).

---

### Mistake 19: Assuming Subscription Data Is Immediately Available After Checkout

**What the developer did**: After a user completes checkout, immediately checks `subscription.get(workspaceId)` server-side and expects the new subscription to be present.

**Symptom**: Immediately after checkout, subscription shows as inactive or on the free plan. After a few seconds or a page refresh, it updates correctly.

**Why it happens**: Developers expect checkout to be synchronous. Stripe webhook processing adds latency.

**Detection**: The subscription state is correct after 2-5 seconds but wrong immediately after the Stripe redirect.

**Recovery**: Don't check subscription state immediately after checkout redirect. Either: (1) poll `subscription.get(workspaceId)` with a short delay, (2) handle the server-side webhook (`subscription.created`/`subscription.updated`) to update your own records, or (3) show a "processing..." state for a few seconds before redirecting to a confirmed state. (Note: there is no client `subscription:changed` event via `handleEvent` — use webhooks or polling.)

---

## Feature Flags & Quota (Mistakes 20–24)

### Mistake 20: Feature Slug Doesn't Exist in Dashboard

**What the developer did**: Used `<WhenWorkspaceFeatureEnabled slug="dark-mode">` in code but never created a "dark-mode" feature in the Buildbase dashboard.

**Symptom**: The gate renders nothing — silently. No error. Looks like the feature is disabled for all users.

**Why it happens**: The code-first mental model. The slug feels like a string you just make up. The dashboard step feels optional.

**Detection**: Open Buildbase dashboard → Features. Check if "dark-mode" exists. If not, that's the issue.

**Recovery**: Create the feature in the dashboard first. Name it, set the slug to "dark-mode". Enable it on the relevant plans. Then the code gate will work.

---

### Mistake 21: Feature Exists But Isn't on the Plan

**What the developer did**: Created the feature in the dashboard but didn't add it to any plan.

**Symptom**: Same as above — gate shows nothing for all users even though the feature exists.

**Why it happens**: Creating a feature and assigning it to a plan are two separate steps. Developers do the first but forget the second.

**Detection**: Dashboard → Features → click "dark-mode" → check which plans include it. If none, that's the issue.

**Recovery**: In the Buildbase dashboard, edit each plan that should include the feature. Add the feature to the plan's feature list.

---

### Mistake 22: Quota Slug Not Defined on the Plan

**What the developer did**: Used `<WhenQuotaAvailable slug="api_calls">` but didn't define the "api_calls" quota on the workspace's plan.

**Symptom**: `WhenQuotaAvailable` shows the fallbackComponent for all users, even on paid plans. Or `useQuotaUsageStatus` returns unexpected values.

**Why it happens**: Same pattern as features — quota slugs must be defined on plans in the dashboard before SDK references to them work.

**Detection**: Dashboard → Plans → [plan name] → Quotas. Check if "api_calls" is listed.

**Recovery**: Add the quota to the plan in the dashboard: define the slug, included amount, overage pricing if applicable.

---

### Mistake 23: Recording Usage Client-Side for Server-Validated Actions

**What the developer did**: Used `useRecordUsage` in a React component to record API call usage when a button is clicked.

**Symptom**: Users can bypass quota limits by manipulating the request or calling the endpoint without triggering the React component. Quota data becomes inaccurate.

**Why it happens**: `useRecordUsage` is accessible and easy to use from React. Developers don't think about whether the recording can be manipulated.

**Detection**: Can a user trigger the actual action (e.g., the API call) without triggering the usage recording? If yes, move recording server-side.

**Recovery**: Record usage in the API route that processes the actual action: `await usage.record(workspaceId, { quotaSlug: 'api_calls', quantity: 1, idempotencyKey: requestId })`.

---

### Mistake 24: No idempotencyKey on Critical Usage Recordings

**What the developer did**: Calls `usage.record(...)` without an `idempotencyKey` for an action that might be retried (network error, user double-click, job retry).

**Symptom**: Usage is double-counted. A workspace's quota is consumed twice for a single action.

**Why it happens**: `idempotencyKey` is optional. Developers skip optional parameters.

**Detection**: Trigger the action twice in rapid succession (double-click). Check the quota usage counter — if it increments by 2, there's no idempotency protection.

**Recovery**: Add `idempotencyKey: generateUniqueId()` to every `usage.record` call for user-initiated or retryable actions. Use a UUID tied to the specific request (not the user ID or workspace ID).

---

## Security Vulnerabilities (Mistakes 25–28)

### Mistake 25: clientSecret Exposed to Browser

**What the developer did**: Used `NEXT_PUBLIC_BUILDBASE_CLIENT_SECRET` or imported `process.env.BUILDBASE_CLIENT_SECRET` in a client component.

**Symptom**: No runtime error — the app works. But the secret is embedded in the JavaScript bundle. Anyone can open DevTools → Sources → search for the secret.

**Why it happens**: Fast development pace. Env var copy-paste mistakes. No lint rule catches this.

**Detection**: Build the app (`npm run build`) and search the `.next/static` folder for the secret value. Or check `grep -r "NEXT_PUBLIC" .env.local`.

**Recovery**: Move to `BUILDBASE_CLIENT_SECRET` (no prefix). Use only in server-side code. Rotate the secret in Buildbase dashboard immediately if it was already deployed.

---

### Mistake 26: sessionId in localStorage

**What the developer did**: Stored the sessionId in `localStorage` after receiving it from the `/api/auth/token` response.

**Symptom**: No immediate issue — auth works. But any XSS attack can read `localStorage.getItem('sessionId')` and steal the session.

**Why it happens**: JWT-in-localStorage is common in tutorials. Looks equivalent to cookie storage.

**Detection**: Check `localStorage` in DevTools. If `sessionId` or `bb-session-id` appears there, it's wrong.

**Recovery**: Never store the sessionId in localStorage. The `/api/auth/token` route sets an httpOnly cookie. The `getSession` callback calls `/api/auth/session` to read it server-side. JavaScript never touches the token directly.

---

### Mistake 27: No Auth Check in API Routes

**What the developer did**: Built API routes that perform user-specific actions without checking if the user is authenticated first.

**Symptom**: Unauthenticated requests can access protected data or perform privileged operations.

**Why it happens**: The SDK handles client-side auth state. Developers assume the auth guard at the React layer is sufficient.

**Detection**: Call a protected API route without a session cookie. If you get data back, there's no server-side auth check.

**Recovery**: At the top of every protected API route: `const session = await auth(); if (!session) return Response.json({ error: 'Unauthorized' }, { status: 401 });`. The `auth()` function from the factory reads the session cookie and validates it.

---

### Mistake 28: Webhook Not Signature-Verified

**What the developer did**: Built a webhook handler that processes events without verifying the `x-buildbase-signature` header.

**Symptom**: No immediate issue — the app works. But any malicious party can send fake webhook events (fake subscription.created, fake subscription.canceled) to your endpoint.

**Why it happens**: Signature verification feels like an optional hardening step.

**Detection**: Send a POST request to your webhook endpoint with a fake payload and no signature header. If it processes the event, verification is missing.

**Recovery**: Verify before processing any event. Both webhook helpers take a **single options object** (not positional args) and require the `x-buildbase-timestamp` header for replay protection. Prefer `parseWebhookEvent` — it verifies and parses in one step, returning `null` on failure:

```ts
const event = parseWebhookEvent({
  body: rawBody,
  signature: request.headers.get('x-buildbase-signature'),
  timestamp: request.headers.get('x-buildbase-timestamp'),
  secret: process.env.BUILDBASE_WEBHOOK_SECRET!,
});
if (!event) return Response.json({ error: 'Invalid webhook' }, { status: 401 });
// event.event is the type string; event.data is the payload
```

---

## Performance & Architecture (Mistakes 29–30)

### Mistake 29: BuildBase() Called Per Request Instead of as a Singleton

**What the developer did**: Called `BuildBase({ ... })` inside a function, API route handler, or React component, creating a new factory instance on every call.

**Symptom**: Performance degrades under load. Each request creates new connection pools and configuration objects. In development, this may not be noticeable.

**Why it happens**: Developers follow the pattern of other libraries that are initialized per-request. Or they create the factory inside a component to access env vars.

**Detection**: Search for `BuildBase(` in your codebase. Any occurrence outside a module-level `const` assignment is a problem.

**Recovery**: Call `BuildBase(...)` exactly once at module level in `lib/buildbase.ts`. Export the destructured action modules. Import them in API routes and server components. The factory is a singleton — one instance for the lifetime of the process.

---

### Mistake 30: Excessive Re-renders from Subscription Context

**What the developer did**: Read `useSubscriptionContext()` in many deeply nested components, or structured component trees to cause re-renders whenever subscription data updates.

**Symptom**: The app re-renders frequently when subscription data loads or refetches. Noticeable performance issues on slow networks where subscription data refetches often.

**Why it happens**: React context causes all consumers to re-render when context changes. Subscription data refetches on workspace change and on a regular poll interval.

**Detection**: Use React DevTools Profiler. If many components highlight on subscription data updates, context consumption is too broad.

**Recovery**: Memoize components that use subscription data with `React.memo`. Extract subscription checks into a single gate component (`WhenSubscription`) rather than reading the raw context in many places. Use gate components for rendering decisions — they're optimized for this. Access the raw context only when you genuinely need the subscription data object, not just a boolean.
