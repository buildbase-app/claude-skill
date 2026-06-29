# Quota Usage Tracking

This guide is for **metered features that reset every billing period** — the "you get 1,000 API calls a month" kind of limit. Use it when you need to count how much of an allowance a workspace has used and react when they run out. The key distinction: **quotas = metered usage that resets each billing period; credits = prepaid units that don't reset** (for credits, see [credits.md](./credits.md)).

You record usage as it happens, and Buildbase keeps the running total for you and tells you what's left.

## Contents

- [What Quota Tracking Is](#what-quota-tracking-is) — quotas, slugs, and overage
- [When to Record Client-Side vs Server-Side](#when-to-record-client-side-vs-server-side) — decision table
- [Client-Side: Recording Usage](#client-side-recording-usage) — the `useRecordUsage` hook
- [Client-Side: Checking Quota Status](#client-side-checking-quota-status) — status hooks and dashboards
- [Quota Gate Components](#quota-gate-components) — available/exhausted/overage/threshold gates
- [Server-Side: Recording Usage](#server-side-recording-usage) — `usage.record` in API routes
- [Batch Usage Recording](#batch-usage-recording) — record many items at once
- [Usage Response Shape](#usage-response-shape) — the `IRecordUsageResponse` fields
- [Usage Log History](#usage-log-history) — paginating past usage logs

## What Quota Tracking Is

A **quota** is a usage limit included in a subscription plan — an allowance the workspace gets each billing period. Examples:
- 1,000 API calls per month
- 10 GB storage
- 500 emails per month
- 50 AI generations per month

Each quota is identified by a **slug** — a short text id like `api_calls` or `emails` that you use in code to refer to one specific quota.

**Define your quota slugs on the plan in the dashboard first.** A slug only works in code once it exists on the plan at [console.buildbase.app](https://console.buildbase.app); recording usage against a slug that isn't defined will fail.

When a workspace goes past its included quota, that excess is called **overage** (the units consumed beyond what the plan includes). Buildbase automatically bills overage via Stripe — but only if overage pricing is configured on the plan in the dashboard.

---

## When to Record Client-Side vs Server-Side

| Scenario | Record from | Why |
|----------|------------|-----|
| User clicks a button in the UI | Client (React hook) | Immediate feedback needed |
| API route processes a request | Server (REST API or SDK) | Backend controls the resource |
| Background job | Server | No browser context |
| File upload | Either | Depends on where validation occurs |

**Rule**: Record usage where the resource is consumed.

---

## Client-Side: Recording Usage

To **record usage** means to log a **usage record** — a single entry that says "this workspace consumed N units of this quota." Buildbase adds it to the running total for the current billing period. The `useRecordUsage` hook is the React way to do that from the browser.

```tsx
import { useRecordUsage, useSaaSWorkspaces } from '@buildbase/sdk/react';

function SendEmailButton() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { recordUsage, loading, error } = useRecordUsage(currentWorkspace?._id);

  const handleSend = async () => {
    try {
      const result = await recordUsage({
        quotaSlug: 'emails',       // The quota's slug — must be defined on your plan in the dashboard
        quantity: 1,
        source: 'web-app',         // Optional: a label for analytics
        // idempotencyKey: a unique id you supply so retrying the same call
        // (e.g. after a network blip) only records the usage once, not twice.
        idempotencyKey: `email-${Date.now()}`,  // Optional: prevent duplicates
      });
      
      console.log(`Used: ${result.consumed}/${result.included}`);
      console.log(`Available: ${result.available}`);
      
      if (result.overage > 0) {
        showOverageWarning(result.overage);
      }
    } catch (err) {
      console.error('Usage recording failed:', err);
    }
  };

  return <button onClick={handleSend} disabled={loading}>Send Email</button>;
}
```

After `recordUsage` succeeds, the `QuotaUsageContext` automatically refetches — quota gate components update immediately.

---

## Client-Side: Checking Quota Status

```tsx
import { useQuotaUsageStatus, useAllQuotaUsage, useSaaSWorkspaces } from '@buildbase/sdk/react';

// Single quota
function ApiQuotaBar() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { status, loading } = useQuotaUsageStatus(currentWorkspace?._id, 'api_calls');

  if (loading || !status) return null;

  const percent = Math.round((status.consumed / status.included) * 100);
  return (
    <div>
      <div className="bg-gray-200 rounded-full h-2">
        <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${percent}%` }} />
      </div>
      <p>{status.consumed.toLocaleString()} / {status.included.toLocaleString()} API calls used</p>
      {status.hasOverage && <p className="text-orange-500">Overage: {status.overage} calls</p>}
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
        <p className="text-yellow-600">Warning: 80% of API calls used this month</p>
      </WhenQuotaThreshold>

      {/* Show when in overage billing */}
      <WhenQuotaOverage slug="api_calls">
        <p className="text-orange-600">You are being billed for additional API calls</p>
      </WhenQuotaOverage>

      {/* Show when fully exhausted (no overage) */}
      <WhenQuotaExhausted slug="api_calls">
        <p className="text-red-600">No API calls remaining this month</p>
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
| `WhenQuotaThreshold` | Usage percentage >= threshold |

---

## Server-Side: Recording Usage

```ts
import { usage } from '@/lib/buildbase';

// Record usage in an API route
export async function POST(request: Request) {
  const { workspaceId } = await getAuthContext(request);

  const result = await usage.record(workspaceId, {
    quotaSlug: 'api_calls',
    quantity: 1,
    source: 'api',
    metadata: { endpoint: '/api/generate' },
    idempotencyKey: request.headers.get('x-request-id') ?? undefined,
  });

  if (result.available <= 0 && !result.hasOverage) {
    return Response.json({ error: 'Quota exceeded' }, { status: 429 });
  }

  // ... do the work ...
  return Response.json({ success: true, quotaRemaining: result.available });
}
```

---

## Batch Usage Recording

For bulk operations (cron jobs, exports, webhooks), record all at once:

```ts
import { usage } from '@/lib/buildbase';

await usage.recordBatch(workspaceId, {
  items: [
    { quotaSlug: 'images', quantity: 500, source: 'batch-export' },
    { quotaSlug: 'storage', quantity: 10, source: 'batch-export' },
  ],
});
// Max 100 items per batch
// Each item processed independently (partial success is possible)
```

---

## Usage Response Shape

```ts
interface IRecordUsageResponse {
  used: number;        // Quantity recorded in this request
  consumed: number;    // Total in current billing period
  included: number;    // Included in plan
  available: number;   // Remaining before overage
  overage: number;     // Units beyond included
  billedAsync: boolean; // Whether overage billing was queued to Stripe
}
```

---

## Usage Log History

```tsx
import { useUsageLogs, useSaaSWorkspaces } from '@buildbase/sdk/react';

function UsageHistory() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { logs, totalPages, page, loading } = useUsageLogs(
    currentWorkspace?._id,
    'api_calls',  // optional quota filter
    { limit: 20, page: 1 }
  );

  return (
    <table>
      <tbody>
        {logs.map(log => (
          <tr key={log._id}>
            <td>{log.quotaSlug}</td>
            <td>{log.quantity}</td>
            <td>{log.source}</td>
            <td>{new Date(log.createdAt).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```
