# Buildbase Core Philosophy

## Skip the Plumbing, Ship the Product

Buildbase exists because auth, workspaces, billing, and notifications are infrastructure - not product differentiation. Every SaaS developer solves the same problems. Buildbase solves them once.

The cost of building these systems from scratch:
- Auth: 2 to 4 weeks (OAuth, sessions, email verification, password reset)
- Workspaces: 2 to 3 weeks (CRUD, invites, roles, permissions)
- Billing: 4 to 8 weeks (Stripe integration, webhooks, plan management, overage)
- Notifications: 1 to 2 weeks (email templates, push, preferences)
- Feature flags: 1 week

Total: 3 to 4 months of infrastructure work before your first line of product code.

Buildbase compresses this to hours. `npx @buildbase/sdk init` writes the provider, the auth routes and a webhook route into an existing Next.js, TanStack Start, Vite or Express app, and with no account yet `npx @buildbase/sdk init --claim --yes` starts on a claimable organization that a person claims later.

---

## Design Principles

### 1. Minimal Integration Surface
The entire client-side integration is one provider (`SaaSOSProvider`, or its brand-name alias `BuildBaseProvider`) + CSS import, plus three small auth routes on your server (`init` writes them; `createAuthHandler` is all three as one handler). You don't need to understand the internals to get value.

### 2. Server-Side by Default (for Security)
In the recommended pattern, your server keeps the `sessionId` in an httpOnly cookie (the same approach as next-auth) and the SDK restores it on page load through your `getSession` callback, which is the source of truth. The code exchange that needs your `clientSecret` runs only on your server (`exchangeAuthCode`). (Note: once signed in, the browser SDK keeps its own working copy of the `sessionId` in `localStorage`, `saas-session-id`, to send as the `x-session-id` header on its API calls, so the usual defences against injected scripts still matter.) Your `clientSecret` is always server-only regardless.

### 3. Progressive Complexity
You can start with just authentication and add features incrementally. Subscription gates, quota tracking, and credits don't require configuration until you need them.

### 4. Render-Prop + Declarative Hybrid
Gate components (`WhenEntitled`, `WhenSubscription`, `WhenQuotaAvailable`, etc.) for simple cases. Hooks (`useEntitlement`, `useSubscriptionContext`, `useQuotaUsageContext`) for complex cases. Both are always available.

### 5. Framework-Agnostic Server SDK
The `BuildBase()` factory works in Next.js, TanStack Start, Express, Hono, Fastify, or any server runtime with `fetch`. The root entry has no React and no Node built-ins. No framework coupling.

### 6. Workspaces as the Default Unit of Billing
Subscriptions, quotas, and credits belong to workspaces (teams/tenants) by default, which matches how team SaaS billing works. Since 1.0.0 a plan, a credit wallet and add-ons can also belong to one person (`{ user: true }` on the hooks, the person's own Billing screen), for consumer apps and for what follows a person across workspaces. The two are never merged: every check names whose plan it reads.

### 7. Configuration You Can Review
The console holds the configuration, and since 1.0.0 it can also be one file, `buildbase.blueprint.json`, that an owner or admin validates, plans and applies (`npx @buildbase/sdk blueprint`). Development and staging environments, each with its own database, users and sign-in client, keep test data out of production: the `environment` prop names one, and unset is production.

### 8. A Stable Public API
The SDK follows semver since 1.0.0. Minor releases add; a change in behaviour is flagged in the changelog with a compatibility note.
