# Credit System

This guide is for **pay-as-you-go capacity that a user buys upfront** — the "buy 1,000 credits, spend them whenever" model. Use it for things like AI tokens or one-off actions where usage shouldn't reset on a schedule. The key distinction: **credits = prepaid units that don't reset; quotas = metered usage that resets each billing period** (for quotas, see [quota-usage.md](./quota-usage.md)).

You sell credits in packages, then spend them from your code as the user takes actions.

## Contents

- [What Credits Are](#what-credits-are) — prepaid units vs quotas
- [Credit Gates](#credit-gates) — show UI by credit balance
- [Consuming Credits](#consuming-credits) — deduct credits in the browser
- [Credit Balance Hook](#credit-balance-hook) — read the current balance
- [Credit Purchase UI](#credit-purchase-ui) — buy-and-consume render-prop
- [Public Credit Packages (Marketing Page)](#public-credit-packages-marketing-page) — show packages without auth
- [Server-Side Credits](#server-side-credits) — balance, consume, transactions on backend
- [Credit vs Quota: When to Use Each](#credit-vs-quota-when-to-use-each) — quick comparison table

## What Credits Are

A **credit** is a prepaid unit that a workspace buys ahead of time and spends later. Credits are sold as a **credit package** — a named bundle priced for sale (e.g., "1,000 credits for $10"). Unlike quotas (included in a subscription plan and reset each billing period), credits are:
- Purchased as packages (e.g., "1,000 credits for $10")
- **Consumed** explicitly by your app code — *consume* means to deduct credits from the balance when the user does something
- Not automatically replenished
- Useful for AI tokens, compute units, one-time actions

**Define your credit packages in the dashboard first.** Packages live at [console.buildbase.app](https://console.buildbase.app); until they exist there, the purchase UI has nothing to show and code that references them won't work.

Credits and subscriptions coexist — a workspace can have both.

---

## Credit Gates

```tsx
import { WhenCreditsAvailable, WhenCreditsExhausted, WhenCreditsLow } from '@buildbase/sdk/react';

function AIFeature() {
  return (
    <div>
      {/* Render when at least 1 credit available */}
      <WhenCreditsAvailable>
        <GenerateButton />
      </WhenCreditsAvailable>

      {/* Render when at least 10 credits available */}
      <WhenCreditsAvailable min={10}>
        <BulkGenerateButton />
      </WhenCreditsAvailable>

      {/* Render when 0 credits */}
      <WhenCreditsExhausted>
        <p>No credits remaining. <a href="/credits">Buy more</a></p>
      </WhenCreditsExhausted>

      {/* Render when below threshold */}
      <WhenCreditsLow threshold={50}>
        <p>Running low on credits!</p>
      </WhenCreditsLow>
    </div>
  );
}
```

| Component | Renders when |
|-----------|-------------|
| `WhenCreditsAvailable` | `balance.available >= min` (default: min=1) |
| `WhenCreditsExhausted` | `balance.available === 0` |
| `WhenCreditsLow` | `balance.available <= threshold` |

---

## Consuming Credits

To **consume** credits is to deduct them from the workspace's balance — you call this when the user performs the paid action. `useConsumeCredits` is the React hook for doing that from the browser.

```tsx
import { useConsumeCredits, useSaaSWorkspaces } from '@buildbase/sdk/react';

function GenerateButton() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { consumeCredits, loading, error } = useConsumeCredits(currentWorkspace?._id);

  const handleGenerate = async () => {
    try {
      const result = await consumeCredits({
        amount: 5,
        metadata: { action: 'image-generation', model: 'dall-e-3' },
        // idempotencyKey: a unique id you supply so a retried call only
        // deducts credits once, even if the request is sent twice.
        idempotencyKey: `gen-${crypto.randomUUID()}`,
      });
      console.log(`Remaining: ${result.balanceAfter}`);
    } catch (err: any) {
      // INSUFFICIENT_CREDITS: the balance is too low for this consume —
      // the workspace needs to buy more before the action can proceed.
      if (err.code === 'INSUFFICIENT_CREDITS') {
        // err.requested and err.available are available
        showPurchaseModal();
      }
    }
  };

  return (
    <button onClick={handleGenerate} disabled={loading}>
      Generate (5 credits)
    </button>
  );
}
```

`consumeCredits` automatically invalidates the `CreditBalanceContext` on success — gates update immediately.

---

## Credit Balance Hook

```tsx
import { useCreditBalance, useSaaSWorkspaces } from '@buildbase/sdk/react';

function CreditBadge() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { balance, loading } = useCreditBalance(currentWorkspace?._id);

  if (loading || !balance) return null;
  return <span>{balance.available} credits</span>;
}
```

---

## Credit Purchase UI

Use the `CreditActionsProvider` render-prop for a complete purchase + consumption UI:

```tsx
import { CreditActionsProvider } from '@buildbase/sdk/react';

function CreditsDashboard() {
  return (
    <CreditActionsProvider>
      {({ balance, packages, consume, consuming, purchase, purchasing, error }) => (
        <div>
          <p className="text-2xl font-bold">{balance?.available ?? 0} credits</p>

          <button 
            onClick={() => consume({ amount: 1 })} 
            disabled={consuming || !balance?.available}
          >
            Use 1 Credit
          </button>

          <h3>Purchase Credits</h3>
          <div className="grid grid-cols-3 gap-4">
            {packages.map(pkg => (
              <button 
                key={pkg._id} 
                onClick={() => purchase(pkg)}
                disabled={purchasing}
              >
                {pkg.name}<br />
                {pkg.creditAmount} credits
              </button>
            ))}
          </div>

          {error && <p className="text-red-500">{error}</p>}
        </div>
      )}
    </CreditActionsProvider>
  );
}
```

---

## Public Credit Packages (Marketing Page)

Show packages without requiring authentication:

```tsx
import { usePublicCreditPackages } from '@buildbase/sdk/react';

function PublicCreditsPage() {
  const { packages, notes, loading } = usePublicCreditPackages();

  if (loading) return <Skeleton />;

  return (
    <div>
      {notes && <p>{notes}</p>}
      {packages.map(pkg => (
        <div key={pkg._id} className="border rounded p-4">
          <h3>{pkg.name}</h3>
          <p>{pkg.creditAmount} credits</p>
          <p>${((pkg.pricingVariants?.[0]?.amount ?? 0) / 100).toFixed(2)}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## Server-Side Credits

```ts
import { credits } from '@/lib/buildbase';

// Get balance
const balance = await credits.getBalance(workspaceId);

// Consume (throws with code 'INSUFFICIENT_CREDITS' on 402)
try {
  const result = await credits.consume(workspaceId, {
    amount: 10,
    metadata: { action: 'generate-report', reportId: 'abc123' },
  });
  console.log(`Remaining: ${result.balanceAfter}`);
} catch (err: any) {
  // The consume error carries err.code === 'INSUFFICIENT_CREDITS'
  // plus err.available and err.requested (it does NOT set err.status).
  if (err.code === 'INSUFFICIENT_CREDITS') {
    throw new Error('Insufficient credits');
  }
}

// Transaction history
const txns = await credits.getTransactions(workspaceId, { page: 1, limit: 20 });

// Credits expiring soon (default: 7 days)
const expiring = await credits.getExpiring(workspaceId, 7);
```

---

## Credit vs Quota: When to Use Each

| Use credits when... | Use quotas when... |
|--------------------|-------------------|
| User pre-purchases capacity | Capacity is included in plan |
| Consumption doesn't reset monthly | Consumption resets each billing period |
| You want marketplace-style billing | You want subscription-style billing |
| AI tokens, compute, one-off actions | API calls, storage, seats, emails |
