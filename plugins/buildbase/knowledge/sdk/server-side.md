# Server-Side SDK

This is the half of the SDK that runs on *your server* — never in the browser — so it can safely touch secrets, talk to the Buildbase API directly, and run without a logged-in user. Reach for it in API routes, background jobs, cron tasks, and webhook handlers. If you're just getting auth working, do [quick-start.md](./quick-start.md) first; this guide goes deeper on everything you build on top of it.

## Contents

- [Overview](#overview) — what the server-side SDK is for
- [Setup (Next.js — Recommended Pattern)](#setup-nextjs--recommended-pattern) — the `BuildBase()` factory with cookies
- [Setup (Express)](#setup-express) — per-request `withSession`
- [Usage in Next.js API Routes](#usage-in-nextjs-api-routes) — auth check + action modules
- [Background Jobs and Webhooks](#background-jobs-and-webhooks) — service-session jobs and crons
- [All Action Modules](#all-action-modules) — table of modules and methods
- [Config Options](#config-options) — `BuildBase()` configuration reference
- [Webhook Verification](#webhook-verification) — `parseWebhookEvent` and replay protection
- [Permissions (Server-Side)](#permissions-server-side) — checking and resolving permissions

## Overview

The `BuildBase()` **factory** (a function you call once that hands back a ready-to-use set of tools) provides a server-side SDK for API routes, background jobs, webhooks, and **cron tasks** (jobs that run on a schedule, not in response to a user). Zero React dependency — works in any Node.js runtime.

Import from `@buildbase/sdk` (not `/react`, which is the browser-side half).

---

## Setup (Next.js — Recommended Pattern)

Configure once, use everywhere. Same pattern as Auth.js. Each named export below is an **action module** — a grouped set of methods for one area (e.g. `workspace.list()`, `subscription.cancel()`):

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
  permissions,  // Check/resolve workspace permissions (computed client-side)
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

`withSession(sessionId)` returns a copy of the SDK tools locked to one specific user's session — handy when you can't rely on a cookie. For Express, call it per-request (passing the session ID off the request) instead of giving `BuildBase()` a `getSessionId` callback:

```ts
// src/lib/buildbase.ts
import BuildBase from '@buildbase/sdk';

const bb = BuildBase({
  serverUrl: process.env.BUILDBASE_URL!,
  orgId: process.env.BUILDBASE_ORG_ID!,
  // No getSessionId — use withSession() per request
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
| `workspace` | `list`, `get`, `create`, `update`, `delete` |
| `users` | `list`, `invite`, `remove`, `updateRole`, `getProfile`, `updateProfile` |
| `subscription` | `get`, `checkout`, `update`, `cancel`, `resume`, `getBillingPortalUrl` |
| `plans` | `getGroup`, `getVersions`, `getPublic`, `getVersion` |
| `invoices` | `list`, `get` |
| `usage` | `record`, `recordBatch`, `getQuota`, `getAll`, `getLogs` |
| `credits` | `getBalance`, `consume`, `purchase`, `getPackages`, `getTransactions`, `getExpiring`, `getBuckets`, `getPublicPackages` |
| `features` | `list`, `update` |
| `settings` | `get` |
| `notification` | `send(workspaceId, event, userId?, data?)` |
| `permissions` | `check(workspaceId, userId, permission)`, `resolve(workspaceId, userId)` |

---

## Config Options

```ts
BuildBase({
  serverUrl: '...',              // Required: Buildbase server URL
  orgId: '...',                  // Required: 24-char hex org ID
  getSessionId: async () => ..., // Session resolver (Next.js pattern)
  
  // Optional
  timeout: 30_000,               // Request timeout ms (default: 30s)
  maxRetries: 2,                 // Retry on 5xx/network (default: 0)
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

A **webhook** is an HTTP request Buildbase sends *to your server* when something happens (a subscription was created, an invoice paid, etc.) — the reverse of you calling its API. Because anyone could POST to that URL, you must verify each request really came from Buildbase before trusting it.

Both helpers take a **single options object** (not positional args) and require the
`timestamp` header for replay protection (rejecting old, re-sent requests). `parseWebhookEvent` verifies *and* parses in
one step — prefer it over calling `verifyWebhookSignature` separately. The parsed event's
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

  switch (event.event) {
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
- Webhooks can be delivered more than once, so dedupe before acting (e.g. on a unique id in the event payload) — the official docs reference `event.id` for this; confirm the field is present in your payloads.

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

App-level permissions are defined in the `defaultPermissions` prop on `SaaSOSProvider`:

```tsx
<SaaSOSProvider
  defaultPermissions={{
    admin: ['projects:create', 'projects:delete', 'reports:export'],
    editor: ['projects:create', 'reports:export'],
    member: ['projects:view'],
  }}
>
```
