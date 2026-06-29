# Developer Experience Stages

Five progressive stages of Buildbase expertise. The same question means different things at different stages. Tailor explanations to where the developer actually is.

## Contents

- [Stage 1: Explorer](#stage-1-explorer) — evaluating, hasn't installed yet
- [Stage 2: Beginner](#stage-2-beginner) — getting auth working first time
- [Stage 3: Builder](#stage-3-builder) — adding billing and feature flags
- [Stage 4: Advanced](#stage-4-advanced) — server-side, webhooks, edge cases
- [Stage 5: Power User](#stage-5-power-user) — production across multiple apps

---

## Stage 1: Explorer

**The developer hasn't installed anything yet. They're evaluating whether to use Buildbase.**

### What they know
- There's a product called Buildbase
- It seems to handle auth and billing
- There's an npm package called `@buildbase/sdk`
- They've probably read the README headline

### What they don't know yet
- That there are two entry points (`@buildbase/sdk` vs `@buildbase/sdk/react`)
- That the Buildbase dashboard must be configured before most features work
- What `orgId` is or where it comes from
- That they need to implement three auth API endpoints themselves
- The difference between workspace modes
- That the SDK reads sessions from a cookie they must set

### What they're likely trying to do
- Decide if Buildbase is the right choice for their project
- Understand the integration complexity before committing
- Figure out if this replaces Auth0, Stripe, or both

### The single most valuable thing to teach them
**The mental model, not the API.** Explain: "Buildbase is a managed SaaS layer. You connect your app to it via the SDK. Buildbase handles auth, billing, and workspaces. Your app handles your actual product. The SDK is the bridge."

Then explain the dashboard-first requirement: almost everything in the SDK references something configured in the dashboard. Feature slugs, plan slugs, quota slugs — they all must exist in the dashboard first.

### Signs they're ready to advance
- They've decided to use Buildbase for their project
- They have a Buildbase account and can see the dashboard
- They understand roughly why each piece exists (auth endpoints, provider, factory)

---

## Stage 2: Beginner

**Installed the SDK, working on getting auth to function for the first time.**

### What they know
- The package is installed
- There's a `SaaSOSProvider` that needs to wrap the app
- They need environment variables
- They've seen the README code examples

### What they don't know yet
- That three auth API routes are required (not optional)
- What exactly `handleAuthentication` does — and crucially that it must return `{ sessionId }`
- That the `getSession` callback is called on every page load (not just after login)
- That `orgId` must be exactly 24 hexadecimal characters
- That `import '@buildbase/sdk/css'` is required for any SDK UI to render correctly
- The difference between `@buildbase/sdk` and `@buildbase/sdk/react` (and that importing from the wrong one in a Next.js API route will fail)

### What they're likely trying to do
- Get the sign-in flow working end-to-end
- See `isAuthenticated` become `true` after clicking the sign-in button
- Understand why nothing happens after they return from the OAuth redirect

### The single most valuable thing to teach them
**The auth triangle.** Three pieces must all work together: (1) `handleAuthentication` calls `/api/auth/token` which exchanges the code and sets the cookie; (2) `getSession` calls `/api/auth/session` which reads the cookie; (3) `onSignOut` calls `/api/auth/signout` which clears it. If any one of these three is missing or wrong, auth will appear to silently fail.

Also: show them the actual implementation of all three routes, not just the provider config.

### Signs they're ready to advance
- A real user can sign in and their session persists on page refresh
- `useSaaSAuth().isAuthenticated` returns `true` reliably
- They understand why each of the three auth routes exists

---

## Stage 3: Builder

**Auth works. Now they're adding billing, feature flags, and workspace features.**

### What they know
- Auth integration pattern (the three routes)
- The provider setup
- Basic hooks (`useSaaSAuth`, `useSaaSWorkspaces`)
- How to wrap JSX in `WhenAuthenticated`

### What they don't know yet
- That every gate slug must be configured in the dashboard first
- The difference between workspace features and user features
- When to use a gate component vs a hook
- That `WhenSubscription` has loading state — it doesn't "show nothing" because the user is unsubscribed, it shows nothing because it's loading
- The difference between `switchToWorkspace` and `setCurrentWorkspace`
- That the `onWorkspaceChange` callback is the correct place to generate their own internal JWT

### What they're likely trying to do
- Show premium features only to paying users
- Set up a pricing page
- Implement feature flags for their product features
- Handle workspace-scoped permissions

### The single most valuable thing to teach them
**Dashboard-first, code second.** Before writing a single gate component, create the thing it references in the dashboard. Create the plan. Add the feature to the plan. Define the quota. Then write the code. Code that references a slug not in the dashboard does nothing — no error, just silence.

### Signs they're ready to advance
- At least one billing gate is working (subscription, plan, or trial)
- At least one feature flag is working end-to-end (dashboard → code → UI)
- They understand why `WhenSubscription` shows nothing during loading vs. when the user has no subscription

---

## Stage 4: Advanced

**Core integration is complete. Now solving edge cases, server-side needs, webhooks, and non-Next.js environments.**

### What they know
- Full client-side integration pattern
- Gate components and hooks for all major features
- Workspace mode concepts
- Basic billing gates

### What they don't know yet
- How to use `BuildBase()` factory without `getSessionId` for background jobs
- How `withSession` works for per-request session binding (Express pattern)
- Webhook verification with `verifyWebhookSignature` and `parseWebhookEvent`
- `recordBatch` for bulk usage recording (max 100 items)
- How to use `idempotencyKey` to prevent duplicate usage recordings
- Server-side subscription and workspace lookups for authorization in API routes
- The `credits.getExpiring(workspaceId, days)` utility
- How service sessions work for background jobs

### What they're likely trying to do
- Record usage server-side in API routes
- Handle billing lifecycle webhooks (subscription created, canceled, renewed)
- Integrate with background job runners or cron
- Build a custom permission system using RBAC
- Set up push notifications with a service worker

### The single most valuable thing to teach them
**Server-side is a different pattern.** The `BuildBase()` factory is a singleton created once at module level. For API routes in Next.js, `getSessionId` reads the cookie automatically. For Express or background jobs, don't use `getSessionId` — use `withSession(sessionId)` per-request to get a scoped set of action modules for that session. The factory is the same; the session binding is different.

### Signs they're ready to advance
- Can handle webhook events and use them to sync state
- Has server-side usage recording working with idempotency keys
- Understands when to use `withSession` vs `getSessionId`

---

## Stage 5: Power User

**Running Buildbase in production across one or more apps. Optimizing, customizing, and maintaining.**

### What they know
- The full integration pattern in depth
- Edge cases in auth, workspace switching, billing
- Server-side patterns for all major features
- Webhook handling and verification
- How to debug the SDK

### What they're likely trying to do
- Reuse the integration pattern across multiple client projects
- Implement custom permission schemes beyond the built-in RBAC
- Optimize performance (eliminating unnecessary re-renders, caching subscription state)
- Set up monitoring for quota and credit exhaustion
- Build a developer onboarding flow that adapts to workspace mode

### The single most valuable thing at this stage
**The `BuildBase()` singleton is your entire server-side API.** Understand every action module and what it exposes. Know when to reach for `withSession` for isolated sessions vs the default `getSessionId` pattern. Know which operations are workspace-scoped vs user-scoped. At this stage the limiting factor isn't knowledge of the API — it's knowing how to compose it cleanly in a production codebase.

### Signs they're at this stage
- Has shipped Buildbase to real users
- Has debugged a production auth issue
- Has handled a billing webhook in a real scenario
- Could explain the full integration pattern to a junior developer in under 30 minutes
