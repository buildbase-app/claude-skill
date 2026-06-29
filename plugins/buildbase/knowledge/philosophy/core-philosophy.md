# Buildbase Core Philosophy

## Skip the Plumbing, Ship the Product

Buildbase exists because auth, workspaces, billing, and notifications are infrastructure — not product differentiation. Every SaaS developer solves the same problems. Buildbase solves them once.

The cost of building these systems from scratch:
- Auth: 2–4 weeks (OAuth, sessions, email verification, password reset)
- Workspaces: 2–3 weeks (CRUD, invites, roles, permissions)
- Billing: 4–8 weeks (Stripe integration, webhooks, plan management, overage)
- Notifications: 1–2 weeks (email templates, push, preferences)
- Feature flags: 1 week

Total: 3–4 months of infrastructure work before your first line of product code.

Buildbase compresses this to hours.

---

## Design Principles

### 1. Minimal Integration Surface
The entire client-side integration is one provider (`SaaSOSProvider`) + CSS import. You don't need to understand the internals to get value.

### 2. Server-Side by Default (for Security)
In the recommended pattern, your server stores the `sessionId` in an httpOnly cookie (the same approach as next-auth) and the SDK reads it back via your `getSession` callback — so secrets and the session stay off the client. (Note: left to its own devices the browser SDK will fall back to reading the `sessionId` from `localStorage`; the httpOnly-cookie pattern is what you implement on top to avoid that.) Your `clientSecret` is always server-only regardless.

### 3. Progressive Complexity
You can start with just authentication and add features incrementally. Subscription gates, quota tracking, and credits don't require configuration until you need them.

### 4. Render-Prop + Declarative Hybrid
Gate components (`WhenSubscription`, `WhenQuotaAvailable`, etc.) for simple cases. Hooks (`useSubscriptionContext`, `useQuotaUsageContext`) for complex cases. Both are always available.

### 5. Framework-Agnostic Server SDK
The `BuildBase()` factory works in Next.js, Express, Hono, Fastify, or any Node.js runtime. No framework coupling.

### 6. Workspaces as the Unit of Billing
Subscriptions, quotas, and credits belong to workspaces (teams/tenants), not individual users. This matches how SaaS billing works in practice.
