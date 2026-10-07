# Server-Side SDK

This is the half of the SDK that runs on *your server* - never in the browser - so it can safely touch secrets, talk to the Buildbase API directly, and run without a logged-in user. Reach for it in API routes, background jobs, cron tasks, and webhook handlers. If you're just getting auth working, do [quick-start.md](./quick-start.md) first; this guide goes deeper on everything you build on top of it.

## Contents

- [Overview](#overview) - what the server-side SDK is for
- [Setup (Next.js - Recommended Pattern)](#setup-nextjs--recommended-pattern) - the `BuildBase()` factory with cookies
- [Setup (Express)](#setup-express) - per-request `withSession`
- [Usage in Next.js API Routes](#usage-in-nextjs-api-routes) - auth check + action modules
- [Background Jobs and Webhooks](#background-jobs-and-webhooks) - service-session jobs and crons
- [All Action Modules](#all-action-modules) - table of modules and methods
- [Config Options](#config-options) - `BuildBase()` configuration reference
- [Webhook Verification](#webhook-verification) - `parseWebhookEvent` and replay protection
- [Permissions (Server-Side)](#permissions-server-side) - checking and resolving permissions

## Overview

The `BuildBase()` **factory** (a function you call once that hands back a ready-to-use set of tools) provides a server-side SDK for API routes, background jobs, webhooks, and **cron tasks** (jobs that run on a schedule, not in response to a user). Zero React dependency - works in any Node.js runtime.

Import from `@buildbase/sdk` (not `/react`, which is the browser-side half).

---

## Setup (Next.js - Recommended Pattern)

Configure once, use everywhere. Same pattern as Auth.js. Each named export below is an **action module** - a grouped set of methods for one area (e.g. `workspace.list()`, `subscription.cancel()`):

```ts
// src/lib/buildbase.ts
import BuildBase from '@buildbase/sdk';
import { cookies } from 'next/headers';

export const SESSION_COOKIE_NAME = 'bb-session-id';

export const {
  auth,         // Check if user is authenticated
  workspace,    // Workspace CRUD
  users,        // User management in workspaces
  subscription, // Subscription management
  plans,        // Plan lookup (public + private)
  invoices,     // Invoice listing
  usage,        // Quota usage
  credits,      // Credit system
  features,     // Feature flags
  settings,     // Org settings
  notification, // Send notifications
  permissions,  // Check/resolve a member's permissions (computed locally from three GETs)
  invitations,  // Workspace invitations: list, create, resend, revoke (0.0.71)
  devices,      // The session user's devices: list, rename, signOut, forget (0.0.57)
  sessions,     // The session user's live sessions: list, revoke (0.0.57)
  withSession,  // Create a scoped client for a specific session
  client,       // Low-level API classes
} = BuildBase({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!,
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!,
  getSessionId: async () => {
    const c = await cookies();
    return c.get(SESSION_COOKIE_NAME)?.value ?? null;
  },
});
```

---

## Setup (Express)

`withSession(sessionId)` returns a copy of the SDK tools locked to one specific user's session - handy when you can't rely on a cookie. For Express, call it per-request (passing the session ID off the request) instead of giving `BuildBase()` a `getSessionId` callback:

```ts
// src/lib/buildbase.ts
import BuildBase from '@buildbase/sdk';

const bb = BuildBase({
  serverUrl: process.env.BUILDBASE_URL!,
  orgId: process.env.BUILDBASE_ORG_ID!,
  // No getSessionId - use withSession() per request
});

export const { withSession, plans } = bb;

// Usage in routes
app.get('/api/workspaces', async (req, res) => {
  const sessionId = req.headers['x-session-id'] as string;
  const { workspace } = withSession(sessionId);
  const workspaces = await workspace.list();
  res.json({ workspaces });
});
```

---

## Usage in Next.js API Routes

```ts
// app/api/workspace/route.ts
import { auth, workspace, subscription } from '@/lib/buildbase';
import { NextResponse } from 'next/server';

export async function GET() {
  // 1. Check authentication
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // 2. Use action modules (session resolved automatically from cookie)
  const workspaces = await workspace.list();
  return NextResponse.json({ workspaces });
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { name } = await request.json();
  const newWorkspace = await workspace.create({ name });
  return NextResponse.json({ workspace: newWorkspace });
}
```

---

## Background Jobs and Webhooks

Use `withSession()` with a service session ID for jobs without a user context:

```ts
import { withSession } from '@/lib/buildbase';

// Service account session ID (from token exchange endpoint)
const bb = withSession(process.env.SERVICE_SESSION_ID!);

// In a cron job
export async function dailyCronJob() {
  const workspaces = await bb.workspace.list();
  
  for (const ws of workspaces) {
    await bb.usage.record(ws._id, {
      quotaSlug: 'cron_runs',
      quantity: 1,
      source: 'cron:daily-job',
    });
    
    await bb.notification.send(ws._id, 'daily_digest', undefined, {
      title: 'Daily Digest',
      message: 'Your daily activity summary',
      url: '/dashboard',
    });
  }
}
```

---

## All Action Modules

| Module | Methods |
|--------|---------|
| `workspace` | `list`, `get`, `create`, `update`, `delete`, `permissions(workspaceId)` (the server's `{ role, isOwner, permissions }` for the session's user, 0.0.73), `can(workspaceId, permission \| permission[])` |
| `users` | `list`, `invite` (adds an **existing** account at once and answers 404 when the address has none; use `invitations.create` to reach someone without an account), `remove`, `updateRole`, `getProfile`, `updateProfile` |
| `invitations` | `list(workspaceId)`, `create(workspaceId, email, role, landingUrl?)`, `resend(workspaceId, invitationId)`, `revoke(workspaceId, invitationId)` (0.0.71). Accept and decline belong to the invitee's own session, so they live on the client |
| `subscription` | `get`, `checkout`, `update`, `cancel`, `resume`, `getBillingPortalUrl` |
| `plans` | `getGroup`, `getVersions`, `getPublic`, `getVersion` |
| `invoices` | `list`, `get` |
| `usage` | `record`, `recordBatch`, `getQuota`, `getAll`, `getLogs` |
| `credits` | `getBalance`, `consume`, `purchase`, `getPackages`, `getTransactions`, `getExpiring`, `getBuckets`, `getPublicPackages` |
| `features` | `list`, `update` |
| `settings` | `get` |
| `notification` | `send(workspaceId, event, userId?, data?)` |
| `permissions` | `check(workspaceId, userId, permission)`, `resolve(workspaceId, userId)` - local computation for any member; for the session's own user prefer `workspace.can` |
| `devices` | `list`, `rename(deviceId, name)`, `signOut(deviceId)`, `forget(deviceId)` |
| `sessions` | `list`, `revoke(id)` |

---

## Config Options

```ts
BuildBase({
  serverUrl: '...',              // Required: Buildbase server URL
  orgId: '...',                  // Required: 24-char hex org ID
  version: 'v1',                 // API version (default 'v1'; the ApiVersion type)
  getSessionId: async () => ..., // Session resolver (Next.js pattern)
  
  // Optional
  timeout: 30_000,               // Request timeout ms (default: 30s)
  maxRetries: 2,                 // Retry on 5xx/network (default: 0).
                                 // Since 0.0.54 only GET/HEAD/OPTIONS/PUT/DELETE
                                 // are retried. POST and PATCH are never replayed,
                                 // so a lost response on credits.consume or
                                 // subscription.checkout cannot double-charge.
                                 // Retry those yourself with an idempotencyKey.
  debug: true,                   // Log all requests to console
  headers: { 'X-Source': 'api' }, // Custom headers on every request
  onError: (err, ctx) => {       // Centralized error logging
    Sentry.captureException(err, { extra: ctx });
  },
  fetch: customFetch,            // Replace global fetch
});
```

---

## Webhook Verification

A **webhook** is an HTTP request Buildbase sends *to your server* when something happens (a subscription was created, an invoice paid, etc.) - the reverse of you calling its API. Because anyone could POST to that URL, you must verify each request really came from Buildbase before trusting it.

Both helpers take a **single options object** (not positional args) and require the
`timestamp` header for replay protection (rejecting old, re-sent requests). `parseWebhookEvent` verifies *and* parses in
one step - prefer it over calling `verifyWebhookSignature` separately. The parsed event's
type field is `event.event` (a string), not `event.type`.

```ts
import { parseWebhookEvent } from '@buildbase/sdk';

export async function POST(request: Request) {
  const rawBody = await request.text();

  // Verifies signature + timestamp age, then parses. Returns null if invalid.
  const event = parseWebhookEvent({
    body: rawBody,
    signature: request.headers.get('x-buildbase-signature'),
    timestamp: request.headers.get('x-buildbase-timestamp'),
    secret: process.env.BUILDBASE_WEBHOOK_SECRET!,
  });

  if (!event) {
    return Response.json({ error: 'Invalid webhook' }, { status: 401 });
  }

  // Only names from the catalog in knowledge/http-api/webhook-events.json.
  switch (event.event) {
    case 'payment.failed':
      await flagWorkspace(event.data.workspaceId, event.data.nextRetryAt);
      break;
    case 'subscription.created':
      await handleSubscriptionCreated(event.data);
      break;
    case 'subscription.canceled':
      await handleSubscriptionCanceled(event.data);
      break;
    // ... handle other events
  }

  return Response.json({ received: true });
}
```

**Details confirmed in the official docs ([docs.buildbase.app/webhooks](https://docs.buildbase.app/webhooks/overview)):**
- Headers are `x-buildbase-signature` and `x-buildbase-timestamp`.
- Signatures are valid for **5 minutes** (the `timestamp` check rejects older requests to prevent replay attacks). Override with `maxAgeSeconds` if needed.
- Return **401** when verification fails.
- Webhooks can be delivered more than once, so dedupe before acting. **There is no event id to dedupe on** - deliveries carry only `event`, `timestamp` and `data`, and a retry repeats all three. Hash the raw request body instead.
- A third header, `x-buildbase-event`, carries the event name (e.g. `subscription.upgraded`), so you can route before parsing. Verify before trusting it.
- `x-buildbase-timestamp` is Unix **seconds**, and the signed string is `${timestamp}.${rawBody}`.
- The event names are a fixed catalog of 112: [../http-api/webhooks.md](../http-api/webhooks.md#event-catalog), machine-readable in `webhook-events.json`. `payment.failed` carries `workspaceId, subscriptionId, invoiceId, dunningState, amount, currency, failedAt, nextRetryAt`; the platform already emails the customer about it, so the handler is for your own side effects.
- Verification is runtime-agnostic as of SDK 0.0.50: the HMAC is a dependency-free pure-JS implementation, so it behaves identically on Node (CJS and ESM), bundlers, edge runtimes, Deno, Bun and browsers. Earlier notes calling this "Node.js only" are out of date.

---

## Permissions (Server-Side)

```ts
import { permissions } from '@/lib/buildbase';

// Check a single permission
const canExport = await permissions.check(workspaceId, userId, 'reports:export');

// Check multiple permissions (all must pass)
const canAdmin = await permissions.check(workspaceId, userId, ['users:invite', 'users:remove']);

// Resolve all permissions for a user
const allPermissions = await permissions.resolve(workspaceId, userId);
// Returns Set<string>
```

For the session's own user, prefer the server's answer: `await workspace.can(workspaceId, 'reports:export')` or `await workspace.permissions(workspaceId)` (`GET .../permissions/me`, 0.0.73). `permissions.check` / `permissions.resolve` compute locally and work for any member.

App-level permissions are resolved in three tiers, the same as the server: a workspace override, then the organization's own permission catalog from the console (`settings.workspace.customPermissions`, where an org owner defines keys like `reports:export` and grants them per role), then the `defaultPermissions` prop on `SaaSOSProvider`, which only applies to keys the org has not catalogued:

```tsx
<SaaSOSProvider
  defaultPermissions={{
    admin: ['projects:create', 'projects:delete', 'reports:export'],
    editor: ['projects:create', 'reports:export'],
    member: ['projects:view'],
  }}
>
```
