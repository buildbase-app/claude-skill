# Server-Side SDK

This is the half of the SDK that runs on *your server* - never in the browser - so it can safely touch secrets, talk to the Buildbase API directly, and run without a logged-in user. Reach for it in API routes, background jobs, cron tasks, and webhook handlers. If you're just getting auth working, do [quick-start.md](./quick-start.md) first; this guide goes deeper on everything you build on top of it.

Checked against `@buildbase/sdk` 1.8.0. The installed package ships its own export map for this half in `node_modules/@buildbase/sdk/agents/server-toolkits.md` (the `BuildBase()` factory, webhooks, regions) and `agents/server.md` (`@buildbase/sdk/server`); where they disagree with this page, the package is right.

## Contents

- [Overview](#overview) - two server clients, and which one you want
- [Setup (Next.js - Recommended Pattern)](#setup-nextjs--recommended-pattern) - the `BuildBase()` factory with cookies
- [Setup (Express)](#setup-express) - per-request `withSession`
- [Usage in Next.js API Routes](#usage-in-nextjs-api-routes) - auth check + action modules
- [Sign-in on your server](#sign-in-on-your-server) - `exchangeCode`, `exchangeAuthCode`, `createAuthHandler`
- [Background Jobs and Webhooks](#background-jobs-and-webhooks) - service-session jobs and crons
- [A named person's billing, with an org API token](#a-named-persons-billing-with-an-org-api-token) - `apiToken`, `users.subscription`, `entitlements`
- [All Action Modules](#all-action-modules) - table of modules and methods
- [Config Options](#config-options) - `BuildBase()` configuration reference
- [Regions: which `serverUrl`](#regions-which-serverurl) - `resolveServerUrl` and the 421
- [Webhook Verification](#webhook-verification) - `parseWebhookEvent`, event ids, Standard Webhooks
- [Permissions (Server-Side)](#permissions-server-side) - checking and resolving permissions
- [`@buildbase/sdk/server`: content, email, subscribers, commerce](#buildbasesdkserver-content-email-subscribers-commerce) - `createServerClient` with an org API token

## Overview

There are two server clients, and they authenticate differently:

| Client | Import | Authenticates as | Use it for |
|---|---|---|---|
| `BuildBase()` factory | `@buildbase/sdk` | A user **session** (`x-session-id`), plus an optional org API token for a named person's billing | Anything a signed-in user does: workspaces, members, subscriptions, usage, credits, notifications, add-ons, enterprise, the buyer and seller side of commerce |
| `createServerClient()` | `@buildbase/sdk/server` | An **org API token** (`<orgId>:<secret>`) only, no user | Reading published content (blogs, docs, FAQs, collections), sending transactional email, managing subscribers, and commerce as the app's own back office |

The `BuildBase()` **factory** (a function you call once that hands back a ready-to-use set of tools) works in API routes, background jobs, webhooks, and **cron tasks** (jobs that run on a schedule, not in response to a user). Zero React dependency - works in any server runtime with `fetch`.

Import it from `@buildbase/sdk` (not `/react`, which is the browser-side half).

---

## Setup (Next.js - Recommended Pattern)

Configure once, use everywhere. Same pattern as Auth.js. Each named export below is an **action module** - a grouped set of methods for one area (e.g. `workspace.list()`, `subscription.cancel()`):

```ts
// src/lib/buildbase.ts
import BuildBase from '@buildbase/sdk';
import { cookies } from 'next/headers';

export const SESSION_COOKIE_NAME = 'bb-session-id';

export const {
  auth,          // Check if user is authenticated
  exchangeCode,  // Trade the hosted sign-in page's ?code= for a session (1.6.0)
  workspace,     // Workspace CRUD, the session user's permissions
  workspaces,    // Workspaces by id: limits and claims
  me,            // The signed-in person's own billing (account-level plans)
  users,         // Members; with apiToken, a named person's billing
  invitations,   // Workspace invitations: list, create, resend, revoke (0.0.71)
  subscription,  // Subscription management
  entitlements,  // What a workspace or a person may do, composed by the server
  plans,         // Plan lookup (public + private)
  invoices,      // Invoice listing
  usage,         // Quota usage
  credits,       // Credit system, holds, auto top-up
  addOns,        // A workspace's add-ons and what it holds beyond its plan
  features,      // Feature flags
  settings,      // Org settings
  notification,  // Send (or schedule) notifications
  permissions,   // Check/resolve a member's permissions (computed locally from three GETs)
  devices,       // The session user's devices: list, rename, signOut, forget (0.0.57)
  sessions,      // The session user's live sessions: list, revoke (0.0.57)
  enterprise,    // A workspace's company: SSO, directory, roles, audit (the owner's own WorkOS account)
  commerce,      // Items, checkout, orders, holdings, item subscriptions, bookings, sales
  checkout,      // Whether a Stripe checkout a buyer came back from is done
  withSession,   // Create a scoped client for a specific session
  client,        // Low-level API classes
} = BuildBase({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!,
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!,
  // environment: process.env.NEXT_PUBLIC_BUILDBASE_ENVIRONMENT, // a dev or staging key; unset is production
  getSessionId: async () => {
    const c = await cookies();
    return c.get(SESSION_COOKIE_NAME)?.value ?? null;
  },
});
```

An empty `orgId` (an env var not filled in yet) does **not** throw when `BuildBase()` is called, so a module that builds the client at import still builds. The first call that reaches the platform throws instead, with a message naming the variable to set (`NEXT_PUBLIC_BUILDBASE_ORG_ID` in Next.js, `BUILDBASE_ORG_ID` on Express).

With `environment` set (eight lowercase letters, the key of a development or staging environment from the console), every request names `<orgId>-<key>`; unset, it is production. `sessionCookieName(environment)` gives `bb-session-id-<key>`, so two environments on one host never read each other's session.

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

Every session call also sends `x-org-id` with the configured tenant (the org id, or `<orgId>-<key>` in an environment) since 1.2.0. An agent's session minted in another environment is refused with 401 `AGENT_TENANT_MISMATCH` (`isAgentTenantMismatch(error)`), which signs nobody out. A proxy in front of the platform must pass that header through.

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

## Sign-in on your server

The one server-side step of sign-in is trading the hosted page's one-time `?code=` for a session with the client secret. The SDK does it for you now; do not hand-write the fetch.

- `bb.exchangeCode({ code, clientId, clientSecret })` (1.6.0) uses the factory's server, org and environment and answers `{ sessionId }`.
- `exchangeAuthCode({ code, orgId, clientId, clientSecret, environment?, serverUrl? })` is the same thing without a factory. It posts to `/api/v1/auth/token`.
- `createAuthHandler(options)` is the three routes the provider calls (`POST /api/auth/token`, `GET /api/auth/session`, `POST /api/auth/signout`) as one `(request: Request) => Promise<Response | null>` handler that keeps the session in an httpOnly `bb-session-id` cookie, for TanStack Start, Workers, Hono or a Vite app's serverless functions. Its `POST`s answer 415 unless the body is `application/json` and 403 for another `Origin`; in a hand-written route call `refuseCrossSiteAuthPost(request)` first.

A refused exchange throws `AuthCodeExchangeError` with the platform's `status`, `code` and sentence ("Invalid client secret"), never the secret. Server-side only: the client secret never reaches a browser bundle.

---

## Background Jobs and Webhooks

Use `withSession()` with a service session ID for jobs without a user context:

```ts
import { withSession } from '@/lib/buildbase';

// Service account session ID (from the token exchange endpoint)
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

The service session comes from `POST /api/v1/public/token/exchange` with an org API token ([../http-api/using-from-any-language.md](../http-api/using-from-any-language.md#acting-for-one-of-your-app-users)). The SDK does not call that endpoint for you; `withSession` only binds a session id you already hold.

---

## A named person's billing, with an org API token

Account-level plans belong to a person, not a workspace. The signed-in person's own billing is `me` (`me.subscription.get()`, `me.usage.record(...)`, `me.credits.consume(...)`). To read or meter **another** person's billing from your backend, give the factory an org API token (since 1.0.0):

```ts
const bb = BuildBase({
  serverUrl: process.env.BUILDBASE_URL!,
  orgId: process.env.BUILDBASE_ORG_ID!,
  apiToken: process.env.BUILDBASE_API_TOKEN, // <orgId>:<secret>, server-side only
});

const sub = await bb.users.subscription.get(userId);
const can = await bb.entitlements.check({ slug: 'exports', user: userId });
if (!can.allowed) { /* refuse */ }
await bb.users.usage.record(userId, { quotaSlug: 'api_calls', quantity: 1 });
```

These calls go to the org-token routes under `/api/subscriptions/users` with `Authorization: Bearer <apiToken>`. The token acts for the whole org, so it stays on the server. Everything else in the factory still runs on the session; `apiToken` is optional.

---

## All Action Modules

| Module | Methods |
|--------|---------|
| `workspace` | `list`, `get`, `create`, `update`, `delete`, `permissions(workspaceId)` (the server's `{ role, isOwner, permissions }` for the session's user, 0.0.73), `can(workspaceId, permission \| permission[])` |
| `workspaces` | `limits.check`, `limits.claim`, `limits.release`, `limits.claims` (by workspace id) |
| `me` | The signed-in person's own billing, with no workspace id: `subscription.get` / `getEntitlement` / `getPlanGroup` / `checkout` / `update` / `cancel` and the rest of `subscription`'s methods except `checkPromotionCode`, `invoices.list` / `get`, `usage.record` / `recordBatch` / `getQuota`, `limits.check` / `claim` / `release` / `claims`, `credits.*` (the `credits` methods except `getPublicPackages`) |
| `users` | `list`, `invite` (adds an **existing** account at once and answers 404 when the address has none; use `invitations.create` to reach someone without an account), `remove`, `updateRole`, `getProfile`, `updateProfile`; with `apiToken`, by user id: `subscription.get` / `getEntitlement`, `usage.record`, `limits.*`, `credits.getBalance` / `getHolds` / `release` |
| `invitations` | `list(workspaceId)`, `create(workspaceId, email, role, landingUrl?)`, `resend(workspaceId, invitationId)`, `revoke(workspaceId, invitationId)` (0.0.71). Accept and decline belong to the invitee's own session, so they live on the client |
| `subscription` | `get`, `checkout`, `update`, `preview`, `getUpcomingInvoice`, `getTrialEligibility`, `selectFreePlan`, `cancel`, `cancelNow`, `resume`, `getRetentionOffer`, `acceptRetentionOffer`, `pause`, `convertToPaid`, `getBillingPortalUrl`, `checkPromotionCode` |
| `entitlements` | `get({ workspaceId } \| { user: true \| userId })`, `check({ slug, workspaceId?, user?, current?, wanted? })` (fails open like `useEntitlement`: `allowed` is false only on an explicit no) |
| `plans` | `getGroup`, `getVersions`, `getPublic`, `getVersion` |
| `invoices` | `list`, `get` |
| `usage` | `record`, `recordBatch`, `getQuota`, `getAll`, `getLogs` |
| `credits` | `getBalance`, `consume`, `purchase`, `getPackages`, `getTransactions`, `getExpiring`, `getBuckets`, `getPublicPackages`, `reserve`, `settle`, `release`, `getHolds`, `getAutoTopUp`, `updateAutoTopUp`, `withHold` |
| `addOns` | `list(workspaceId, { currency? })`, `purchase`, `cancel(workspaceId, grantId)`, `grants(workspaceId)` |
| `features` | `list`, `update` |
| `settings` | `get` |
| `notification` | `send(workspaceId, event, userId?, data?)`, `cancelScheduled(workspaceId, scheduledId)` (1.6.0: a future `data.scheduledAt`, at most 365 days ahead, holds the whole send and answers `scheduledId`) |
| `permissions` | `check(workspaceId, userId, permission)`, `resolve(workspaceId, userId)` - local computation for any member; for the session's own user prefer `workspace.can` |
| `devices` | `list`, `rename(deviceId, name)`, `signOut(deviceId)`, `forget(deviceId)` |
| `sessions` | `list`, `revoke(id)` |
| `enterprise` | A workspace's company, set up through the app owner's own WorkOS account: `status`, `createSetupLink`, SSO routing, policy, people and their sessions, admins, roles, groups, join requests, audit and log streams, connected apps, keys, service accounts, workload identity, agent access, workspace policies. Full method list in the package's `agents/server-toolkits.md` |
| `commerce` | The session's buyer and seller routes: `items`, `item`, `checkout`, `orders`, `order`, `holdings`, `access`, `subscriptions`, `subscription`, `cancelSubscription`, `resumeSubscription`, `previewSubscriptionChange`, `changeSubscription`, `slots`, `bookings`, `booking`, `cancelBooking`, `rescheduleBooking`, and for a seller (`{ user: true }` or a workspace id) `sales`, `sale`, `refundSale`, `fulfilSale`, `commissions` |
| `checkout` | `status(sessionId, { nudge? })` (1.2.0): whether the Stripe checkout a buyer returned from is complete |

`credits.withHold(workspaceId, { amount, ttlSeconds?, onExpired? }, fn)` (1.7.0) reserves, runs `fn`, then settles. When the hold expired before the settle it charges with a plain `consume` by default, which may answer 402 after the work is done; pass `onExpired: 'throw'` for work that must not be charged unheld.

---

## Config Options

```ts
BuildBase({
  serverUrl: '...',              // Required: Buildbase server URL
  orgId: '...',                  // Required: 24-char hex org ID (empty throws on first call, not here)
  environment: 'kxzpqwmr',       // A dev or staging environment's key; unset (or 'production') is production
  version: 'v1',                 // API version (default 'v1'; the ApiVersion type)
  getSessionId: async () => ..., // Session resolver (Next.js pattern)
  apiToken: '...',               // Org API token, for users.subscription / users.usage / entitlements by user id
  region: 'eu',                  // 'us' | 'eu', informational only: logged, never sent, never routes
  
  // Optional
  timeout: 30_000,               // Request timeout ms (default: 30s; 0 disables)
  maxRetries: 2,                 // Retries on network errors and 5xx (default: 0).
                                 // Since 0.0.54 only GET/HEAD/OPTIONS/PUT/DELETE
                                 // are retried. POST and PATCH are never replayed,
                                 // so a lost response on credits.consume or
                                 // subscription.checkout cannot double-charge.
                                 // Retry those yourself with the same idempotency key.
                                 // A 429 or 503 is retried twice even when unset
                                 // (idempotent calls and writes carrying an
                                 // Idempotency-Key), waiting out Retry-After up to
                                 // 10 s; maxRetries: 0 turns that off too.
  debug: true,                   // Log all requests to console
  headers: { 'X-Source': 'api' }, // Custom headers on every request
  onError: (err, ctx) => {       // Centralized error logging
    Sentry.captureException(err, { extra: ctx });
  },
  fetch: customFetch,            // Replace global fetch
});
```

`onError` is called when a request gets no answer (network failure or timeout) and for an error status on the calls that parse the JSON body directly. It is **not** called for an error status on the calls that unwrap `{ success, data }`, which covers most billing, credits and enterprise calls: catch the thrown error there. The error is still thrown after the callback, and the callback runs at most once per error. A thrown error carries `status`, and `code` / `retryAfterSeconds` when the platform sends them (a 429 without a code gets `code: 'rate_limited'`).

---

## Regions: which `serverUrl`

`serverUrl` decides which cell answers; `region` in the config is a label only. Most apps serve one organization and bake its `serverUrl` into the build (hosted: `https://api.console.buildbase.app`). An app that hosts many organizations resolves each one at runtime, server-side:

```ts
import { resolveServerUrl, clearResolvedServerUrl } from '@buildbase/sdk';

const { serverUrl, region } = await resolveServerUrl({
  orgId,
  centralUrl: 'https://central.console.buildbase.app',
  apiKey: process.env.BUILDBASE_API_TOKEN, // pass it: without it central answers the default cell for every id
});
```

The answer is cached for central's own `max-age` (a shared `cache` store is optional). It throws on failure rather than falling back to the default cell, because that fallback would send an EU organization's request to the US. A cell that receives a request for an organization it does not hold answers **421 `misdirected_request`**: call `clearResolvedServerUrl({ orgId, centralUrl })`, resolve again, retry the request once, and surface a second failure rather than looping.

---

## Webhook Verification

A **webhook** is an HTTP request Buildbase sends *to your server* when something happens (a subscription was created, an invoice paid, etc.) - the reverse of you calling its API. Because anyone could POST to that URL, you must verify each request really came from Buildbase before trusting it.

Both helpers take a **single options object** (not positional args) and require the
`timestamp` header for replay protection (rejecting old, re-sent requests). `parseWebhookEvent` verifies *and* parses in
one step - prefer it over calling `verifyWebhookSignature` separately. The parsed event's
type field is `event.event` (a string), not `event.type`.

```ts
import { parseWebhookEvent, sha256Digest } from '@buildbase/sdk';

export async function POST(request: Request) {
  const rawBody = await request.text();

  // Verifies signature + timestamp age, then parses. Returns null if invalid.
  const parsed = parseWebhookEvent({
    body: rawBody,
    signature: request.headers.get('x-buildbase-signature'),
    timestamp: request.headers.get('x-buildbase-timestamp'),
    secret: process.env.BUILDBASE_WEBHOOK_SECRET!,
  });

  if (!parsed) {
    return Response.json({ error: 'Invalid webhook' }, { status: 401 });
  }

  // A retry resends the same event with the same id: process each one once.
  // `alreadyProcessed` is your own lookup (a unique index on the key). Fall back
  // to a hash of the raw body when an older platform sent no id.
  const dedupeKey = parsed.id ?? sha256Digest(rawBody); // 'sha256:<hex>'
  if (await alreadyProcessed(dedupeKey)) return Response.json({ duplicate: true });

  // Only names from the catalog in knowledge/http-api/webhook-events.json.
  switch (parsed.event) {
    case 'payment.failed':
      await flagWorkspace(parsed.data.workspaceId, parsed.data.nextRetryAt);
      break;
    case 'subscription.created':
      await handleSubscriptionCreated(parsed.data);
      break;
    case 'subscription.canceled':
      await handleSubscriptionCanceled(parsed.data);
      break;
    // ... handle other events
  }

  return Response.json({ received: true });
}
```

**Details confirmed in the official docs ([docs.buildbase.app/webhooks](https://docs.buildbase.app/webhooks/overview)) and the 1.9.0 types:**
- Headers are `x-buildbase-signature` (`sha256=<hex>`) and `x-buildbase-timestamp`, plus `x-buildbase-event` (the event name, so you can route before parsing; verify before trusting it) and `x-buildbase-event-id`.
- Signatures are valid for **5 minutes** (the `timestamp` check rejects older requests to prevent replay attacks). Override with `maxAgeSeconds` if needed.
- Return **401** when verification fails.
- `x-buildbase-timestamp` is Unix **seconds**, and the signed string is `${timestamp}.${rawBody}`. Each attempt is signed fresh with its own header timestamp; the body (whose own `timestamp` is when the event fired) is the same on every attempt.
- **Deliveries carry an event id.** The parsed event is `{ id?, event, timestamp, data }`; `id` is an opaque string starting `evt_`, equal to the `x-buildbase-event-id` header, and the same on every endpoint and every retry, so dedupe on it. It is optional in the type because a delivery from a platform release older than event ids has none (a self-hosted server not yet upgraded, or a worker on the old release mid-deploy); then hash the raw body instead, which a retry repeats exactly. Older notes that told you to dedupe only on a body hash are out of date (the platform added the id around SDK 1.0.0).
- **Standard Webhooks headers** ride beside BuildBase's own on current platforms: `webhook-id` (the event id), `webhook-timestamp` (Unix seconds) and `webhook-signature` (`v1,` and the base64 HMAC-SHA256 of `{id}.{timestamp}.{body}`, same endpoint secret). `verifyStandardWebhook` / `parseStandardWebhookEvent` (`{ body, id, timestamp, signature, secret, maxAgeSeconds? }`) check them; `secret` is the console's secret or its `whsec_<base64>` form, and any `v1` entry in the list may match. When `webhook-signature` is absent (an older platform), use `verifyWebhookSignature`.
- The event names are a fixed catalog: [../http-api/webhooks.md](../http-api/webhooks.md#event-catalog), machine-readable in `webhook-events.json` (and `WEBHOOK_EVENTS` / `isWebhookEvent` in the SDK). `payment.failed` carries `workspaceId, subscriptionId, invoiceId, dunningState, amount, currency, failedAt, nextRetryAt`; the platform already emails the customer about it, so the handler is for your own side effects.
- Verification is runtime-agnostic as of SDK 0.0.50: the HMAC is a dependency-free pure-JS implementation, so it behaves identically on Node (CJS and ESM), bundlers, edge runtimes, Deno, Bun and browsers. Earlier notes calling this "Node.js only" are out of date. Always verify the **raw** body (`await request.text()`), never re-serialized JSON.

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

---

## `@buildbase/sdk/server`: content, email, subscribers, commerce

A separate entry point with its own client, `createServerClient({ serverUrl, apiToken })`, authenticated only by an org API token (`<orgId>:<secret>`, console **Settings > API keys**). It needs no user and runs on a server or at build time, never in a browser: under the `browser` export condition the entry resolves to a module that throws, and the client refuses to run in a browser anyway. Standard `fetch` only, so Node 18+, Bun, Deno, Cloudflare Workers and edge runtimes. Full guide in the package: `docs/SERVER-CONTENT.md`.

An empty `apiToken` (an env var not filled in yet) does not throw at construction; every call that would reach the platform rejects first, naming `BUILDBASE_API_TOKEN`. A malformed token or an empty `serverUrl` throws at once.

```ts
import { createServerClient } from '@buildbase/sdk/server';

export const bb = createServerClient({
  serverUrl: 'https://api.console.buildbase.app',
  apiToken: process.env.BUILDBASE_API_TOKEN!, // <orgId>:<secret>
});

const posts = await bb.blogs.list({ limit: 20, sort: { publishedAt: -1 } });
const { id } = await bb.emails.send({
  to: { email: 'ada@example.com' },
  templateId: process.env.WELCOME_TEMPLATE_ID!, // a template's id from the console
  data: { name: 'Ada' },
});
await bb.subscribers.upsert({ email: 'ada@example.com', tags: ['beta'] });
```

| Area | Calls | Routes | Role grant the key needs |
|---|---|---|---|
| Content (cached, ETag-revalidated) | `blogs`, `docs`, `faqs`, `testimonials`, `richContent`, `collections`, `revalidateAll()`, `cache` | The console's own read routes, `/api/blogs` and the rest | The read-only **content-reader** role |
| Transactional email (1.0.0) | `emails.send(input, { idempotencyKey? })`, `emails.get(id)` | `/api/v1/server/emails` | `emails_api_sends` (create to send) |
| Subscribers (1.0.0) | `subscribers.upsert`, `get`, `unsubscribe`, `resubscribe`, `delete` (by email) | `/api/v1/server/subscribers` | `audience` (create for a new subscriber, update to change one); changing list membership also needs update on `audience_lists` |
| Commerce back office (1.2.0) | `commerce.items`, `orders`, `subscriptions`, `bookings`, `calendars`, `affiliates`, `commissions`, `shipments`, `shippingRates`, `returns`, `shippingSettings`, `grants`, `licenses`, `files`, `releases`, `buyers.state` | `/api/v1/server/commerce/*` | `marketplace_items`, `marketplace_orders`, `marketplace_refunds` (create, for refunds), `marketplace_grants`, `marketplace_affiliate_programs`, `marketplace_sellers`, `marketplace_releases`; a status change needs update |

Grants come from the **API role** the key carries; an integration that only sends email is a role with `emails_api_sends` create and nothing on `audience`. Give every key a role: a key minted without one inherits its creator's role ([../http-api/org-api.md](../http-api/org-api.md#give-it-a-role-or-it-inherits-yours)). The `/api/v1/server` routes take an API key only (never a console session) and are rate limited per key (300 a minute).

Errors and retries for the writes (`emails`, `subscribers`, `commerce`):

- A refusal throws `BuildBaseApiError` with `status`, the platform's `code` (one of `SERVER_API_ERROR_CODE`, typed `ServerApiErrorCode`) and the body (extra fields such as `problems`). A content read throws `BuildBaseContentError` instead (`status`, `url`, `body`).
- 403 `API_KEYS_SUSPENDED` (any request with the org's keys) or `SENDING_SUSPENDED` (a send) means BuildBase suspended the organization's keys or sending. Retrying does not help; the organization contacts support.
- Writes are never cached and never retried by the SDK. Every commerce write sends an `Idempotency-Key` (yours, or a new `crypto.randomUUID()` per call), and every error carries it as `err.idempotencyKey`. To retry after a timeout or network error, send the same request with the same key: the platform answers with the first result for 24 hours. The same key with another body throws `IdempotencyKeyReusedError` (422 `IDEMPOTENCY_KEY_REUSED`); one still running throws `IdempotencyInProgressError` (409 `IDEMPOTENCY_IN_PROGRESS`, retry shortly with the same key). `emails.send` sends a key only when you pass one, and a retried send with that key never sends twice.
- Timeouts: 10 s by default (`timeoutMs`); writes that move money (refunds, part charges, subscription cancel, resume and change, booking cancels, shipments, return approvals and refunds) wait 60 s (`moneyTimeoutMs`). A keyed write that times out throws `BuildBaseTimeoutError`: the outcome is unknown, so retry with the same key or read the order, never refund under a new key.

Every request from this client carries `X-BuildBase-Client: sdk/<version>; runtime=<...>` (version and runtime only, no user data). Content webhooks, cache stores (`memoryCache`, `redisCache`, `kvCache`), `pullContent` / `npx @buildbase/sdk content pull` and the Next.js helpers in `@buildbase/sdk/server/next` are in the package's `agents/server.md`.
