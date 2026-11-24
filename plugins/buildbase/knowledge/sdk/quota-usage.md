# Quota Usage Tracking

This guide is for **metered features that reset on a schedule**: the "you get 1,000 API calls a month" kind of limit. Use it when you need to count how much of an allowance a workspace has used and react when they run out. The key distinction: **quotas = metered usage that resets each period; credits = prepaid units that don't reset** (for credits, see [credits.md](./credits.md)).

You record usage as it happens, and Buildbase keeps the running total for you and tells you what's left.

Verified against `@buildbase/sdk` 1.8.0 (`node_modules/@buildbase/sdk/agents/react.md`, "Quota hooks", and `docs/ERROR_CODES.md`, "Usage codes").

## Contents

- [What Quota Tracking Is](#what-quota-tracking-is) - quotas, slugs, reset periods, overage and hard limits
- [When to Record Client-Side vs Server-Side](#when-to-record-client-side-vs-server-side) - decision table
- [Client-Side: Recording Usage](#client-side-recording-usage) - the `useRecordUsage` hook
- [Client-Side: Checking Quota Status](#client-side-checking-quota-status) - status hooks and dashboards
- [Quota Gate Components](#quota-gate-components) - available/exhausted/overage/threshold gates
- [Server-Side: Recording Usage](#server-side-recording-usage) - `usage.record` in API routes
- [A Person's Own Quotas](#a-persons-own-quotas) - usage against a person's plan
- [Batch Usage Recording](#batch-usage-recording) - record many items at once
- [Usage Response Shape](#usage-response-shape) - the `IRecordUsageResponse` fields
- [Refusals](#refusals) - `QUOTA_EXHAUSTED`, `PLAN_REQUIRED` and the 400s
- [Usage Log History](#usage-log-history) - paginating past usage logs

## What Quota Tracking Is

A **quota** is a usage limit included in a subscription plan: an allowance the workspace gets each period. Examples:
- 1,000 API calls per month
- 10 GB storage
- 500 emails per month
- 50 AI generations per month

Each quota is identified by a **slug**: a short text id like `api_calls` or `emails` that you use in code to refer to one specific quota.

**Define your quota slugs on the plan in the console first.** A slug only works in code once it exists on the plan at [console.buildbase.app](https://console.buildbase.app); recording usage against a slug that isn't defined, or that the workspace's plan does not include, is refused with a 400.

**Reset period.** Each quota on a plan version has its own reset period, apart from the billing interval: `day`, `week`, `month` (the default, on the subscription's own cycle), `billing_period`, `year` or `never` (a lifetime allowance). Day, week and year follow the organization's time zone. The quota standing carries `resetPeriod` and `resetsAt` (absent on a quota that never resets) on 1.8.0 types and a current platform.

**Overage or a hard limit.** When a workspace goes past its included quota, that excess is called **overage** (the units consumed beyond what the plan includes). Buildbase bills overage via Stripe, once per billing period, but only when overage is allowed on the plan with an overage price in every billing currency. Otherwise the quota is a **hard limit**: the unit past the allowance is refused with `402 QUOTA_EXHAUSTED` and nothing is recorded. A free plan's quotas and a trial are always held to the allowance. A customer can also cap their own overage with a spend cap (an HTTP route; see docs.buildbase.app, Credits, Spend caps).

`included === -1` means unlimited: there is no bar to fill.

---

## When to Record Client-Side vs Server-Side

| Scenario | Record from | Why |
|----------|------------|-----|
| User clicks a button in the UI | Client (React hook) | Immediate feedback needed |
| API route processes a request | Server (REST API or SDK) | Backend controls the resource |
| Background job | Server | No browser context |
| File upload | Either | Depends on where validation occurs |

**Rule**: Record usage where the resource is consumed. Anything that bills (overage) is safer recorded on the server, where the user cannot skip the call.

---

## Client-Side: Recording Usage

To **record usage** means to log a **usage record**: a single entry that says "this workspace consumed N units of this quota." Buildbase adds it to the running total for the current period. The `useRecordUsage` hook is the React way to do that from the browser.

```tsx
import { useRecordUsage, useSaaSWorkspaces } from '@buildbase/sdk/react';
import { planRefusalOf } from '@buildbase/sdk';

function SendEmailButton({ messageId }: { messageId: string }) {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { recordUsage, loading } = useRecordUsage(currentWorkspace?._id);

  const handleSend = async () => {
    try {
      const result = await recordUsage({
        quotaSlug: 'emails',       // Must be defined on the plan in the console
        quantity: 1,               // A whole number from 1 to 1,000,000
        source: 'web-app',         // Optional: a label for analytics
        // A key derived from the unit of work, so retrying this send after a
        // network blip records it once. Not Date.now() or a fresh UUID per try.
        idempotencyKey: `email-${messageId}`,
      });

      console.log(`Used: ${result.consumed}/${result.included}, available: ${result.available}`);
      if (result.overage > 0) showOverageWarning(result.overage);
    } catch (err) {
      const refusal = planRefusalOf(err);
      if (refusal?.code === 'QUOTA_EXHAUSTED') {
        // Hard limit reached: nothing was recorded. refusal.resetsAt says when it starts again.
        showUpgradePrompt(refusal.resetsAt);
      }
    }
  };

  return <button onClick={handleSend} disabled={loading}>Send Email</button>;
}
```

The request is `IRecordUsageRequest`: `quotaSlug`, `quantity` (never `amount`; that is credits), `metadata?`, `source?`, `idempotencyKey?`. **Treat `idempotencyKey` as required** in anything that meters: the SDK does not retry a failed `POST` for you, and without a key your retry counts twice. After `recordUsage` succeeds, the `QuotaUsageContext` refetches, so quota gates update immediately. `useRecordUsage` takes a workspace id only; a person's own usage is recorded from the server ([below](#a-persons-own-quotas)).

---

## Client-Side: Checking Quota Status

```tsx
import { useQuotaUsageStatus, useAllQuotaUsage, useSaaSWorkspaces } from '@buildbase/sdk/react';

// Single quota
function ApiQuotaBar() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { status, loading } = useQuotaUsageStatus(currentWorkspace?._id, 'api_calls');

  if (loading || !status) return null;

  // -1 is unlimited: there is no bar to fill. A 0 allowance reads as full.
  if (status.included === -1) return <p>{status.consumed} API calls used (unlimited)</p>;
  const percent = status.included > 0 ? Math.round((status.consumed / status.included) * 100) : 100;

  return (
    <div>
      <div className="bg-muted h-2 rounded-full">
        <div className="bg-primary h-2 rounded-full" style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
      <p>{status.consumed} / {status.included} API calls used</p>
      {status.hasOverage && <p>Overage: {status.overage} calls</p>}
    </div>
  );
}

// All quotas at once
function QuotaDashboard() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { quotas, loading } = useAllQuotaUsage(currentWorkspace?._id);

  if (loading || !quotas) return null;

  return (
    <div>
      {Object.entries(quotas).map(([slug, usage]) => (
        <div key={slug}>
          <strong>{slug}</strong>: {usage.consumed}/{usage.included}
          {usage.hasOverage && ` (+${usage.overage} overage)`}
        </div>
      ))}
    </div>
  );
}
```

The status shape is `IQuotaUsageStatus`: `consumed`, `included`, `available`, `overage`, `hasOverage`, `allowOverage?` (false is a hard limit). Format numbers for the reader with `fmtNum` from `useTranslation()`. The SDK already ships a usage screen: `useSaaSAuth().openWorkspaceSettings('usage')`.

To gate on a quota by slug for a workspace or the person, `useEntitlement('api_calls')` also answers quotas (allowed while units are left, or overage is allowed); see [billing.md](./billing.md#entitlement-checks-by-slug).

---

## Quota Gate Components

```tsx
import {
  WhenQuotaAvailable,
  WhenQuotaExhausted,
  WhenQuotaOverage,
  WhenQuotaThreshold,
} from '@buildbase/sdk/react';

function FeatureWithQuota() {
  return (
    <div>
      {/* Only show action when quota remains */}
      <WhenQuotaAvailable
        slug="api_calls"
        fallbackComponent={<p>API call limit reached. <a href="/upgrade">Upgrade</a></p>}
      >
        <MakeApiCallButton />
      </WhenQuotaAvailable>

      {/* Warn at 80% usage */}
      <WhenQuotaThreshold slug="api_calls" threshold={80}>
        <p>Warning: 80% of API calls used this month</p>
      </WhenQuotaThreshold>

      {/* Show when in overage billing */}
      <WhenQuotaOverage slug="api_calls">
        <p>You are being billed for additional API calls</p>
      </WhenQuotaOverage>

      {/* Show when fully used */}
      <WhenQuotaExhausted slug="api_calls">
        <p>No API calls remaining this month</p>
      </WhenQuotaExhausted>
    </div>
  );
}
```

| Component | Renders when |
|-----------|-------------|
| `WhenQuotaAvailable` | `available > 0` |
| `WhenQuotaExhausted` | `available <= 0` |
| `WhenQuotaOverage` | `hasOverage` is true **and** overage is allowed (`allowOverage !== false`) |
| `WhenQuotaThreshold` | Usage percentage (`consumed / included * 100`) >= threshold; an allowance of 0 with usage reads as 100% |

Each also takes `loadingComponent` and `fallbackComponent`, and reads the current workspace.

---

## Server-Side: Recording Usage

```ts
import { auth, usage } from '@/lib/buildbase';
import { planRefusalOf } from '@buildbase/sdk';

// Record usage in an API route
export async function POST(request: Request) {
  // `auth()` comes from your own src/lib/buildbase.ts factory (see
  // server-side.md). There is no getAuthContext helper in the SDK.
  const session = await auth();
  if (!session) return Response.json({ error: 'Unauthorized' }, { status: 401 });

  // The workspace is your app's to choose - the SDK does not infer one
  // server-side. Take it from the request, or look it up for the user.
  const { workspaceId } = await request.json();
  // Have the client send one id per action and reuse it on its retries.
  const requestId = request.headers.get('x-request-id') ?? crypto.randomUUID();

  try {
    const result = await usage.record(workspaceId, {
      quotaSlug: 'api_calls',
      quantity: 1,
      source: 'api',
      metadata: { endpoint: '/api/generate' },
      idempotencyKey: `generate-${requestId}`,
    });

    // `IRecordUsageResponse` has no `hasOverage` field - that lives on the
    // quota *status* shape. Here, read `overage` directly.
    // ... do the work ...
    return Response.json({ success: true, quotaRemaining: result.available, overage: result.overage });
  } catch (err) {
    // A hard-capped quota refuses the unit: 402 QUOTA_EXHAUSTED, nothing recorded.
    const refusal = planRefusalOf(err);
    if (refusal?.code === 'QUOTA_EXHAUSTED') {
      return Response.json({ error: 'Quota exceeded', resetsAt: refusal.resetsAt ?? null }, { status: 429 });
    }
    throw err;
  }
}
```

Record **before** you do the work when the quota is a hard limit: the refusal is your stop signal, and checking `available` yourself first races with other requests. The `usage` namespace (by workspace id): `record recordBatch getQuota getAll getLogs`. After a server-side change, call `invalidateQuotaUsage()` on the client so its gates refetch.

---

## A Person's Own Quotas

A plan sold to a person (since 1.0.0) has quotas on the person's own counter, never merged with a workspace's:

```ts
import BuildBase from '@buildbase/sdk';

const bb = BuildBase({
  serverUrl: process.env.BUILDBASE_URL!,
  orgId: process.env.BUILDBASE_ORG_ID!,
  apiToken: process.env.BUILDBASE_API_TOKEN, // only for users.*: an org API token, server only
});

export async function recordForPerson(sessionId: string, userId: string, jobId: string) {
  // The session's own person:
  await bb.withSession(sessionId).me.usage.record({ quotaSlug: 'exports', quantity: 1, idempotencyKey: `export-${jobId}` });
  const standing = await bb.withSession(sessionId).me.usage.getQuota('exports'); // IQuotaStanding, with resetsAt

  // A named person, from a backend job, with the org API token:
  await bb.users.usage.record(userId, { quotaSlug: 'exports', quantity: 1, idempotencyKey: `export-${jobId}-owner` });
  return standing;
}
```

`me.usage` has `record`, `recordBatch` and `getQuota`; `users.usage` has `record`. Without `apiToken`, `users.*` calls say so and send nothing.

---

## Batch Usage Recording

For bulk operations (cron jobs, exports, webhooks), record all at once:

```ts
import { usage } from '@/lib/buildbase';

export async function recordExport(workspaceId: string, exportId: string) {
  const res = await usage.recordBatch(workspaceId, {
    items: [
      { quotaSlug: 'images', quantity: 500, source: 'batch-export', idempotencyKey: `${exportId}-images` },
      { quotaSlug: 'storage', quantity: 10, source: 'batch-export', idempotencyKey: `${exportId}-storage` },
    ],
  });
  // Max 100 items per batch. Each item is processed independently.
  if (res.failed > 0) {
    for (const row of res.results.filter(r => !r.success)) {
      console.warn(row.quotaSlug, row.code, row.error, row.resetsAt); // code: 'QUOTA_EXHAUSTED' on a hard cap
    }
  }
  return res;
}
```

The answer is `{ success, total, succeeded, failed, results }`. **A batch does not throw for a refused row**: with any row refused, `success` is false at the top level and each refused row carries `success: false`, `error`, `code` and `resetsAt`. It throws only when the request itself fails (a non-2xx answer, a timeout). Each item takes its own `idempotencyKey`.

---

## Usage Response Shape

```ts
interface IRecordUsageResponse {
  used: number;        // Quantity recorded by this request (0 on an idempotent replay)
  consumed: number;    // Total in the current period
  included: number;    // Included in plan (-1 is unlimited)
  available: number;   // Remaining before overage
  overage: number;     // Units beyond included
  billedAsync: boolean; // Whether overage billing was queued to Stripe
}
```

When the same `idempotencyKey` is sent again, the platform answers 200 without recording twice, and `used` is 0 on that replay: do not assert `used` equals what you asked for.

---

## Refusals

What `recordUsage`, the server client's `usage.record` and their twins answer when they refuse. Nothing is recorded on any of them. Match the `code`, not the status.

| Code | Status | When |
|---|---|---|
| `QUOTA_EXHAUSTED` | 402 | The unit would go past a hard allowance (overage off, a free plan, a trial) or past a spend cap. Carries `quotaSlug` and `resetsAt`. Older servers sent it with 400. `planRefusalOf(err)` reads it typed |
| `PLAN_REQUIRED` | 402 | The org requires a plan before a workspace is used (since 1.1.0) and this one has none. `isPlanRequiredError(err)` from `/react` |
| none | 400 | Malformed: `quantity` not a whole number from 1 to 1,000,000, a `null` `idempotencyKey`, an unknown field; or an unknown `quotaSlug`, a plan that does not include it, no subscription |
| none | 403 | The signed-in person may not record usage in this workspace |

The SDK keeps the body's `code` on the error since 1.0.0 (0.0.90 dropped it, so there the two 402s looked alike). An app that does not require a plan can read every 402 here as `QUOTA_EXHAUSTED`.

---

## Usage Log History

```tsx
import { useUsageLogs, useSaaSWorkspaces, useTranslation } from '@buildbase/sdk/react';

function UsageHistory() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { formattingLocale } = useTranslation();
  const { logs, totalPages, page, loading } = useUsageLogs(
    currentWorkspace?._id,
    'api_calls',  // optional quota filter
    { limit: 20, page: 1 }  // also from, to, source
  );

  if (loading) return null;
  const when = new Intl.DateTimeFormat(formattingLocale, { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <>
      <table>
        <tbody>
          {logs.map(log => (
            <tr key={log._id}>
              <td>{log.quotaSlug}</td>
              <td>{log.quantity}</td>
              <td>{log.source}</td>
              <td>{when.format(new Date(log.createdAt))}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Page {page} of {totalPages}</p>
    </>
  );
}
```

The hook returns `{ logs, totalDocs, totalPages, page, hasNextPage, hasPrevPage, loading, error, refetch }`. Server: `usage.getLogs(workspaceId, { quotaSlug?, from?, to?, source?, page?, limit? })` returns the paginated `{ docs, totalDocs, ... }`.
