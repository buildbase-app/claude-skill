# Decision Rules: When to Use What

## Contents

- [Gate Components vs Hooks](#gate-components-vs-hooks) - declarative UI vs logic
- [Entitlement Checks vs Plan-Name Gates](#entitlement-checks-vs-plan-name-gates) - what the plan allows vs which plan it is
- [Workspace Plan vs Personal Plan](#workspace-plan-vs-personal-plan) - who pays
- [Client-Side vs Server-Side Usage Recording](#client-side-vs-server-side-usage-recording) - where to record usage
- [Credits vs Quotas](#credits-vs-quotas) - prepaid units vs resetting limits
- [Personal Mode vs Platform Mode](#personal-mode-vs-platform-mode) - solo vs multi-user apps
- [switchToWorkspace vs setCurrentWorkspace](#switchtoworkspace-vs-setcurrentworkspace) - change vs set directly
- [Workspace Features vs User Features](#workspace-features-vs-user-features) - per-team vs per-individual
- [onWorkspaceChange vs handleEvent('workspace:changed')](#onworkspacechange-vs-handleeventworkspacechanged) - before vs after load
- [next-auth Pattern vs Custom Auth](#next-auth-pattern-vs-custom-auth) - running alongside next-auth
- [When to Use withSession() vs getSessionId](#when-to-use-withsession-vs-getsessionid) - per-request vs cookie session
- [RBAC: WhenRoles vs WhenWorkspaceRoles](#rbac-whenroles-vs-whenworkspaceroles) - global vs workspace roles
- [Production vs a Development Environment](#production-vs-a-development-environment) - where test data goes
- [BuildBase Console MCP vs Your App's MCP Server](#buildbase-console-mcp-vs-your-apps-mcp-server) - two different servers

## Gate Components vs Hooks

**Use gate components** (`WhenEntitled`, `WhenSubscription`, `WhenQuotaAvailable`, etc.) when:
- Conditionally rendering UI elements
- You just need "show or hide" behavior
- You want declarative, readable JSX

**Use hooks** (`useEntitlement`, `useSubscriptionContext`, `useQuotaUsageContext`, etc.) when:
- You need subscription/quota data (not just the condition)
- You need to trigger a refetch
- You're performing logic in event handlers or async functions
- You need to check multiple conditions

---

## Entitlement Checks vs Plan-Name Gates

| You want to know | Use |
|------------------|-----|
| May they use this feature, or add one more of this limit, right now? | `useEntitlement(slug, { current? })` / `<WhenEntitled slug="...">`, or `useLimit` / `<WhenWithinLimit>` for a ceiling |
| Which plan are they on (a badge, a support note)? | `<WhenSubscriptionToPlans plans={['pro']}>` or `useSubscriptionContext()` |

Prefer the entitlement check to gate a capability: it answers from the server's composed entitlement (the plan plus add-ons and overrides), so a capability sold as an add-on, or moved between plans, needs no code change. It fails open (nothing locks while loading; a slug the plan does not mention is `unknown` and allowed unless `strictAbsent`), so keep the real enforcement on the server (`entitlements.check` in the factory, or the platform's own 402 refusals).

---

## Workspace Plan vs Personal Plan

| The thing being paid for | Subject |
|--------------------------|---------|
| What the team shares: members, seats, the workspace's data | The workspace (the default; omit `subject`, or `{ workspaceId }`) |
| What follows one person: their API keys, connected agents, devices, a consumer app's plan | The person: `{ user: true }` (1.0.0), from a pricing group whose payer is a person |

The two are never merged. A screen that cares about both asks twice. See [../sdk/billing.md](../sdk/billing.md).

---

## Client-Side vs Server-Side Usage Recording

| Situation | Use |
|-----------|-----|
| User initiates an action in the UI | `useRecordUsage` (client) |
| API route processes a request | `usage.record` (server) |
| Background job or cron | `usage.record` (server) |
| Webhook handler | `usage.record` (server) |
| File upload (server-processed) | `usage.record` (server) |

Anything that bills passes an `idempotencyKey` derived from the unit of work (`gen-<requestId>`), the same key on every retry of that work.

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
| Cost known only after the work (an LLM call) | Credits, held first with `credits.reserve` / `credits.withHold`, settled at the real cost |

---

## Personal Mode vs Platform Mode

| App type | Mode |
|----------|------|
| Solo productivity tool, personal notes, individual subscriptions | Personal Mode |
| Team collaboration, B2B SaaS, multi-user accounts | Platform Mode |
| Consumer app that sells each person their own plan | Personal Mode, with the plan sold to the person (`{ user: true }`) |

Configured in the Buildbase dashboard (Workspaces, then Settings, Mode) - no code changes needed. A new org starts in Personal; Platform needs a BuildBase plan that includes it.

---

## switchToWorkspace vs setCurrentWorkspace

| Function | Use when |
|----------|---------|
| `switchToWorkspace(workspace)` | User clicks "Switch to" - runs `onWorkspaceChange` first and switches only when it resolves (pass the workspace object, not an id) |
| `setCurrentWorkspace(workspace)` | Rare: setting it directly with no callback. You do not need it to restore the last workspace on page load; the SDK does that itself, through `onWorkspaceChange` |

---

## Workspace Features vs User Features

| Feature type | Use when |
|-------------|---------|
| Entitlement (`WhenEntitled`, `useEntitlement`) | A capability sold on a plan or an add-on (e.g., "plan includes analytics") |
| Workspace feature flag | A flag on the workspace, tied to its plan or switched in its Features settings (e.g., "team has the new editor") |
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

If you're already using next-auth, Buildbase runs **alongside** it - they use different cookie names and manage different auth states. Buildbase handles the SaaS platform layer; next-auth can handle your own user auth. Before moving an app's existing sign-in to Buildbase, stop and ask; when the person agrees, `npx @buildbase/sdk import --from <clerk|auth0|firebase|supabase> <file>` moves the users in (with `BUILDBASE_API_TOKEN` and `BUILDBASE_SERVER_URL` set; `--dry-run` first).

---

## When to Use withSession() vs getSessionId

| Scenario | Use |
|----------|-----|
| Next.js API routes (async request context available) | `getSessionId` callback (reads from cookie) |
| Express / Hono / Fastify | `withSession(req.headers['x-session-id'])` |
| Background jobs / service accounts | `withSession(process.env.SERVICE_SESSION_ID)` |
| Server work with no person at all (content reads, a transactional email, subscribers, commerce back office) | `createServerClient({ serverUrl, apiToken })` from `@buildbase/sdk/server`, with an org API token |

---

## RBAC: WhenRoles vs WhenWorkspaceRoles

| Component | Use when |
|-----------|---------|
| `WhenRoles roles={['admin']}` | Checking global user role (super-admin use case) |
| `WhenWorkspaceRoles roles={['admin', 'editor']}` | Checking role within the current workspace |

In most SaaS apps, `WhenWorkspaceRoles` is what you want - users have different roles in different workspaces. The built-in roles are `admin`, `editor` and `viewer`; no member's role is ever `owner` (use `usePermissions().isOwner` for the creator). For a specific action, `WhenPermission` / `usePermissions().can(...)` is better than a role list.

---

## Production vs a Development Environment

| Situation | Use |
|-----------|-----|
| Real users, real money | Production: leave `environment` unset |
| Local development, staging, previews | A development or staging environment's key as `environment` (on `SaaSOSProvider`, `BuildBase()`, `createAgentStack`, `BuildBaseTracking`), with its own users, database and sign-in client |

`npx @buildbase/sdk init --dev` wires an app to one after `npx @buildbase/sdk login`; `npx @buildbase/sdk env` lists, creates and compares them. Ask the person before `env create` (it uses one of the plan's environments) and before `env push`.

---

## BuildBase Console MCP vs Your App's MCP Server

| You want | Use |
|----------|-----|
| An agent that sets up or changes the person's BuildBase organization (plans, settings, blueprints, docs lookups) | BuildBase's hosted MCP server, `https://api.console.buildbase.app/mcp` ("BuildBase Console"), signed in as the person; `npx @buildbase/sdk agent setup --console` adds it to local AI clients |
| The app's own users' agents calling the app's features | The app's own MCP server, built with `@buildbase/sdk/mcp` (`createAgentStack`); `npx @buildbase/sdk init --agent` scaffolds it. See [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md) |
