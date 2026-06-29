# Decision Rules: When to Use What

## Contents

- [Gate Components vs Hooks](#gate-components-vs-hooks) — declarative UI vs logic
- [Client-Side vs Server-Side Usage Recording](#client-side-vs-server-side-usage-recording) — where to record usage
- [Credits vs Quotas](#credits-vs-quotas) — prepaid units vs resetting limits
- [Personal Mode vs Platform Mode](#personal-mode-vs-platform-mode) — solo vs multi-user apps
- [switchToWorkspace vs setCurrentWorkspace](#switchtoworkspace-vs-setcurrentworkspace) — change vs restore workspace
- [Workspace Features vs User Features](#workspace-features-vs-user-features) — per-team vs per-individual
- [onWorkspaceChange vs handleEvent('workspace:changed')](#onworkspacechange-vs-handleeventworkspacechanged) — before vs after load
- [next-auth Pattern vs Custom Auth](#next-auth-pattern-vs-custom-auth) — running alongside next-auth
- [When to Use withSession() vs getSessionId](#when-to-use-withsession-vs-getsessionid) — per-request vs cookie session
- [RBAC: WhenRoles vs WhenWorkspaceRoles](#rbac-whenroles-vs-whenworkspaceroles) — global vs workspace roles

## Gate Components vs Hooks

**Use gate components** (`WhenSubscription`, `WhenQuotaAvailable`, etc.) when:
- Conditionally rendering UI elements
- You just need "show or hide" behavior
- You want declarative, readable JSX

**Use hooks** (`useSubscriptionContext`, `useQuotaUsageContext`, etc.) when:
- You need subscription/quota data (not just the condition)
- You need to trigger a refetch
- You're performing logic in event handlers or async functions
- You need to check multiple conditions

---

## Client-Side vs Server-Side Usage Recording

| Situation | Use |
|-----------|-----|
| User initiates an action in the UI | `useRecordUsage` (client) |
| API route processes a request | `usage.record` (server) |
| Background job or cron | `usage.record` (server) |
| Webhook handler | `usage.record` (server) |
| File upload (server-processed) | `usage.record` (server) |

---

## Credits vs Quotas

| Scenario | Use |
|----------|-----|
| Fixed monthly allocation included in plan | Quota |
| Prepaid units purchased separately | Credits |
| Resets every billing period | Quota |
| Never resets (spend down until refilled) | Credits |
| AI token budget | Credits |
| API call limit | Quota |
| Storage limit | Quota |

---

## Personal Mode vs Platform Mode

| App type | Mode |
|----------|------|
| Solo productivity tool, personal notes, individual subscriptions | Personal Mode |
| Team collaboration, B2B SaaS, multi-user accounts | Platform Mode |
| E-commerce, per-user accounts but with shared resources | Platform Mode |

Configured in Buildbase dashboard — no code changes needed.

---

## switchToWorkspace vs setCurrentWorkspace

| Function | Use when |
|----------|---------|
| `switchToWorkspace(workspace)` | User clicks "Switch to" — runs `onWorkspaceChange` first (pass the workspace object, not an id) |
| `setCurrentWorkspace(workspace)` | Restoring saved state on page load — bypasses callback |

---

## Workspace Features vs User Features

| Feature type | Use when |
|-------------|---------|
| Workspace feature flag | Feature is per-team/plan (e.g., "team has analytics") |
| User feature flag | Feature is per-individual (e.g., "user is in beta") |

---

## onWorkspaceChange vs handleEvent('workspace:changed')

| Callback | Use for |
|----------|---------|
| `onWorkspaceChange` | Work that MUST complete before workspace loads (token generation) |
| `handleEvent('workspace:changed')` | Work that happens AFTER workspace loads (analytics, app state sync) |

---

## next-auth Pattern vs Custom Auth

The Buildbase SDK uses the same session pattern as next-auth:
- httpOnly cookie stores session token
- Server endpoint reads cookie and returns token
- Client-side callback calls server endpoint

If you're already using next-auth, Buildbase runs **alongside** it — they use different cookie names and manage different auth states. Buildbase handles the SaaS platform layer; next-auth can handle your own user auth.

---

## When to Use withSession() vs getSessionId

| Scenario | Use |
|----------|-----|
| Next.js API routes (async request context available) | `getSessionId` callback (reads from cookie) |
| Express / Hono / Fastify | `withSession(req.headers['x-session-id'])` |
| Background jobs / service accounts | `withSession(process.env.SERVICE_SESSION_ID)` |
| Webhook handlers (no user context) | `withSession(serviceToken)` |

---

## RBAC: WhenRoles vs WhenWorkspaceRoles

| Component | Use when |
|-----------|---------|
| `WhenRoles roles={['admin']}` | Checking global user role (super-admin use case) |
| `WhenWorkspaceRoles roles={['owner', 'admin']}` | Checking role within the current workspace |

In most SaaS apps, `WhenWorkspaceRoles` is what you want — users have different roles in different workspaces.
