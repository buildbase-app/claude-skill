# Credit System

This guide is for **pay-as-you-go capacity that a user buys upfront**: the "buy 1,000 credits, spend them whenever" model. Use it for things like AI tokens or one-off actions where usage shouldn't reset on a schedule. The key distinction: **credits = prepaid units that don't reset; quotas = metered usage that resets each period** (for quotas, see [quota-usage.md](./quota-usage.md)).

You sell credits in packages, then spend them from your code as the user takes actions.

Verified against `@buildbase/sdk` 1.8.0 (`node_modules/@buildbase/sdk/agents/react.md`, "Credit hooks", and `agents/server-toolkits.md`, `credits.withHold`).

## Contents

- [What Credits Are](#what-credits-are) - prepaid units vs quotas, a workspace's wallet or a person's
- [Credit Gates](#credit-gates) - show UI by credit balance
- [Consuming Credits](#consuming-credits) - deduct credits in the browser
- [Holds: Reserve, then Settle](#holds-reserve-then-settle) - for work whose cost is not known yet
- [Credit Balance Hook](#credit-balance-hook) - read the current balance
- [Credit Purchase UI](#credit-purchase-ui) - buy-and-consume render-prop and the credit store
- [Public Credit Packages (Marketing Page)](#public-credit-packages-marketing-page) - show packages without auth
- [Auto Top-Up](#auto-top-up) - buy a pack on the saved card under a threshold
- [Server-Side Credits](#server-side-credits) - balance, consume, holds, transactions on the backend
- [Error Codes](#error-codes) - which codes 1.8.0 documents
- [Credit vs Quota: When to Use Each](#credit-vs-quota-when-to-use-each) - quick comparison table

## What Credits Are

A **credit** is a prepaid unit that a workspace (or a person) buys ahead of time and spends later. Credits are sold as a **credit package**: a named bundle priced for sale (e.g., "1,000 credits for $10"). Unlike quotas (included in a subscription plan and reset each period), credits are:
- Purchased as packages (e.g., "1,000 credits for $10"), or granted by a plan
- **Consumed** explicitly by your app code (*consume* means to deduct credits from the balance when the user does something)
- Not automatically replenished, unless the buyer turns on [auto top-up](#auto-top-up)
- Useful for AI tokens, compute units, one-time actions

**Define your credit packages in the console first.** Packages live at [console.buildbase.app](https://console.buildbase.app) (**Credit packages**, under **Credits** in the **Billing** menu, once Stripe is connected); until they exist there, the purchase UI has nothing to show and code that references them won't work.

Credits and subscriptions coexist: a workspace can have both.

**A workspace's wallet or a person's own** (since 1.0.0). Every credit hook takes `{ user: true }` in place of the workspace id for the signed-in person's own wallet (`/me/credits`): `useCreditBalance`, `useConsumeCredits`, `useReserveCredits`, `usePurchaseCredits`, `useCreditPackages`, `useCreditTransactions`, `useExpiringCredits`, `useCreditAutoTopUp`. The person's balance is never a workspace's, and no hook falls back from one to the other. Server: `bb.me.credits.*`.

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

      {/* Render when at or below a threshold */}
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
| `WhenCreditsExhausted` | `balance.available <= 0` |
| `WhenCreditsLow` | `balance.available <= threshold` |

Each also takes `loadingComponent` and `fallbackComponent`. The gates read the current workspace's balance; credits on open holds are already out of `available`.

---

## Consuming Credits

To **consume** credits is to deduct them from the balance: you call this when the user performs the paid action. `useConsumeCredits` is the React hook for doing that from the browser.

```tsx
import { useConsumeCredits, useSaaSWorkspaces } from '@buildbase/sdk/react';

function GenerateImage({ requestId }: { requestId: string }) {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { consumeCredits, loading } = useConsumeCredits(currentWorkspace?._id);

  const handleGenerate = async () => {
    try {
      const result = await consumeCredits({
        amount: 5,
        description: 'Image generation',
        metadata: { action: 'image-generation', model: 'dall-e-3' },
        // Derive the key from the unit of work, so a retry of this request
        // deducts once. A fresh UUID per attempt would bill the retry again.
        idempotencyKey: `gen-${requestId}`,
      });
      console.log(`Remaining: ${result.balanceAfter}`);
    } catch (err) {
      const e = err as { code?: string; available?: number; requested?: number };
      if (e.code === 'INSUFFICIENT_CREDITS') {
        // The balance is too low: e.available and e.requested say by how much.
        showPurchaseModal();
      } else if (e.code === 'PLAN_REQUIRED') {
        // The org requires a plan before a workspace is used (402). Not a short balance.
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

- The request is `IConsumeCreditsRequest`: `amount` (never `quantity`; that is usage recording), `description?`, `metadata?`, `idempotencyKey?`.
- It resolves `IConsumeCreditsResponse`: `{ success, consumed, balanceAfter }`. There is no `remaining` field.
- **Treat `idempotencyKey` as required** in anything that spends. The SDK does not retry a failed `POST` for you; your code retries, and without a key the second attempt spends twice.
- On success `consumeCredits` calls `invalidateCreditBalance()`, so the gates and balance hooks update immediately.
- `CreditActionsProvider`'s `consume` is the same call.

---

## Holds: Reserve, then Settle

For work whose cost is only known afterwards (an agent run, a long generation), hold an estimate, run the work, then close the hold at the real cost (since 1.0.0). Credits leave `available` at reserve, so nobody can spend them twice meanwhile.

```tsx
import { useReserveCredits, useSaaSWorkspaces } from '@buildbase/sdk/react';

function useRunAgent(runAgent: () => Promise<number>) {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { reserve, settle, release } = useReserveCredits(currentWorkspace?._id);

  return async (jobId: string) => {
    const hold = await reserve({ amount: 40, ttlSeconds: 900, idempotencyKey: `job-${jobId}` });
    try {
      const used = await runAgent();                    // what the work really cost
      await settle(hold.holdId, { amount: used });      // less returns the rest, more takes the extra
    } catch (err) {
      await release(hold.holdId);                       // give the whole hold back
      throw err;
    }
  };
}
```

- `reserve` takes `amount` (at least 1), `ttlSeconds` (60 to 86400, 900 by default), `idempotencyKey`, `description`, `metadata`, and resolves `{ holdId, amount, status, expiresAt, available, held, replayed? }`. An unsettled hold is released back at `expiresAt`.
- `settle(holdId, { amount })`: less than held returns the rest, more takes the extra, 0 releases.
- Errors: `INSUFFICIENT_CREDITS` (402, with `available` and `requested`), `HOLD_NOT_FOUND` (404), `HOLD_NOT_OPEN` (409, with the hold's `status`, e.g. `expired`).
- `balance.held` is what open holds take. On the server, [`credits.withHold`](#server-side-credits) does all three steps for you.

---

## Credit Balance Hook

```tsx
import { useCreditBalance, useSaaSWorkspaces } from '@buildbase/sdk/react';

function CreditBadge() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { balance, loading } = useCreditBalance(currentWorkspace?._id); // or { user: true }

  if (loading || !balance) return null;
  return <span>{balance.available} credits{balance.held ? ` (${balance.held} on hold)` : ''}</span>;
}
```

`ICreditBalance` is `{ available, held?, totalGranted, totalConsumed, totalExpired, totalRefunded, autoTopUp? }`. Also: `useCreditTransactions(subject, { type?, page?, limit? })`, `useExpiringCredits(subject, days)` (1 to 90, default 7), `useCreditPackages(subject)`.

---

## Credit Purchase UI

The fastest route is the SDK's own: `useSaaSAuth().openCreditStore()` opens the SDK's credit purchase UI from anywhere (a "Buy credits" button, an `INSUFFICIENT_CREDITS` handler). For your own layout, use the `CreditActionsProvider` render-prop:

```tsx
import { CreditActionsProvider, useTranslation } from '@buildbase/sdk/react';

function CreditsDashboard({ requestId }: { requestId: string }) {
  const { fmtCents } = useTranslation();
  return (
    <CreditActionsProvider>
      {({ balance, packages, consume, consuming, purchase, purchasing, purchaseGuard, error }) => (
        <div>
          <p className="text-2xl font-bold">{balance?.available ?? 0} credits</p>

          <button
            onClick={() => consume({ amount: 1, idempotencyKey: `use-${requestId}` })}
            disabled={consuming || !balance?.available}
          >
            Use 1 Credit
          </button>

          <h3>Purchase Credits</h3>
          {purchaseGuard ? (
            <p>A purchase is being confirmed.</p>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {packages.map(pkg => {
                const price = pkg.pricingVariants.find(v => v.currency === 'usd');
                return (
                  <button key={pkg._id} onClick={() => purchase(pkg, 'usd')} disabled={purchasing}>
                    {pkg.name}<br />
                    {pkg.creditAmount} credits
                    {price ? ` for ${fmtCents(price.amount, price.currency)}` : ''}
                  </button>
                );
              })}
            </div>
          )}

          {error && <p role="alert">{error}</p>}
        </div>
      )}
    </CreditActionsProvider>
  );
}
```

- `purchase(pkg, currency?)` redirects to Stripe Checkout, or opens it in a dialog when `ui.behavior.checkoutMode` is `'embedded'` (with `loadStripe` on the provider; see [billing.md](./billing.md#checkout-hosted-embedded-in-the-app)). Pass the currency you showed the price in.
- While `purchaseGuard` is set (`'confirming'` or `'clearing'`: a purchase being confirmed, or a bank payment clearing), `purchase` asks nothing and rejects with `PURCHASE_BEING_CONFIRMED`. Show the notice in place of the buy buttons.
- `<CreditStorePage>` is the headless public store: a render prop with `packages`, `selectPackage(packageId)` (signs a visitor in first, with `redirectBaseUrl`) and `purchaseGuard`; `subject={{ user: true }}` buys for the person's own wallet.
- `usePurchaseCredits(subject).purchaseCredits({ creditPackageId, currency?, successUrl?, cancelUrl?, promotionCode?, amount? })` is the raw call. `amount` is for a pack with a chosen price (`customAmount` on its variant): what the buyer pays, in minor units, typed through `<CustomAmountInput>`.

---

## Public Credit Packages (Marketing Page)

Show packages without requiring authentication:

```tsx
import { usePublicCreditPackages, useTranslation } from '@buildbase/sdk/react';

function PublicCreditsPage() {
  const { packages, notes, loading } = usePublicCreditPackages();
  const { fmtCents } = useTranslation();

  if (loading) return <Skeleton />;

  return (
    <div>
      {notes && <p>{notes}</p>}
      {packages.map(pkg => {
        const price = pkg.pricingVariants[0];
        return (
          <div key={pkg._id} className="border rounded p-4">
            <h3>{pkg.name}</h3>
            <p>{pkg.creditAmount} credits</p>
            {/* Minor units: never divide by 100 (JPY has none, KWD has three). */}
            {price && <p>{fmtCents(price.amount, price.currency)}</p>}
          </div>
        );
      })}
    </div>
  );
}
```

Each package carries `pricingVariants` (`{ currency, amount, stripePriceId?, customAmount? }`), `validityDays` (null for credits that never expire) and `sortOrder`. On the server, `credits.getPublicPackages()` is the same read.

---

## Auto Top-Up

`useCreditAutoTopUp(subject)` buys a pack on the saved card when the balance falls under a threshold (since 1.0.0): `settings` (null on an older server), `update({ enabled, threshold, creditPackageId, monthlyCap })`, `resume()` after a pause (`settings.pausedReason` says why), and `addPaymentMethod()`. The credits screen has the same card. Refusals: `AUTO_TOP_UP_OFF` (403, the app does not offer it; switching off always works), `MONTHLY_CAP_ABOVE_LIMIT` (400), `AUTO_TOP_UP_INCOMPLETE`, `CREDIT_PACKAGE_NOT_FOUND`, `PACKAGE_CURRENCY_UNAVAILABLE` (400), `TAX_REQUIRES_HOSTED_CHECKOUT` and `PACKAGE_VERSION_CHANGED` (409; read the setting again) (`CREDIT_AUTO_TOP_UP_CODE`).

---

## Server-Side Credits

```ts
import { credits } from '@/lib/buildbase';

export async function generateReport(workspaceId: string, reportId: string) {
  // Get balance
  const balance = await credits.getBalance(workspaceId);

  try {
    const result = await credits.consume(workspaceId, {
      amount: 10,
      metadata: { action: 'generate-report', reportId },
      idempotencyKey: `report-${reportId}`, // treat as required: the SDK never retries a POST
    });
    console.log(`Remaining: ${result.balanceAfter} (was ${balance.available})`);
  } catch (err) {
    // A short balance carries err.code === 'INSUFFICIENT_CREDITS' plus err.available
    // and err.requested; it does NOT set err.status. Any other 402 (PLAN_REQUIRED
    // since 1.5.0) keeps its own code and sets status: 402.
    const e = err as { code?: string; available?: number; requested?: number };
    if (e.code === 'INSUFFICIENT_CREDITS') throw new Error('Insufficient credits');
    throw err;
  }

  // Transaction history
  const txns = await credits.getTransactions(workspaceId, { page: 1, limit: 20 });

  // Credits expiring soon (default: 7 days)
  const expiring = await credits.getExpiring(workspaceId, 7);
  return { txns, expiring };
}
```

**`credits.withHold`** reserves, runs your function, and settles at what it returns (a number, or `{ cost }`):

```ts
import { credits } from '@/lib/buildbase';

export async function runAgentJob(workspaceId: string, jobId: string, runAgent: () => Promise<number>) {
  const { result, settlement, consumed } = await credits.withHold(
    workspaceId,
    { amount: 40, ttlSeconds: 600, idempotencyKey: `job-${jobId}`, onExpired: 'throw' },
    async () => runAgent(), // resolves the credits the work really cost
  );
  return { cost: result, settledBy: settlement ? 'hold' : 'consume', consumed };
}
```

A throw from your function releases the hold and rethrows. When the hold expired before the settle (work that outran `ttlSeconds`), the default `onExpired: 'consume'` charges with a plain consume, which may answer 402 after the work is done if the balance dropped meanwhile; pass `onExpired: 'throw'` for work that must not be charged unheld. On a server without holds, your function runs and its result is consumed.

The whole `credits` namespace (by workspace id): `getBalance consume purchase getPackages getTransactions getExpiring getBuckets getPublicPackages reserve settle release getHolds getAutoTopUp updateAutoTopUp withHold`. `bb.me.credits.*` is the same on the session person's own wallet, without the workspace id. `bb.users.credits.getBalance(userId)`, `getHolds(userId)` and `release(userId, holdId)` read a named person's wallet with the org API token (`BuildBase({ apiToken })`), for example to release a hold a crashed job never settled.

After a server-side change to a balance, call `invalidateCreditBalance()` on the client so its contexts refetch.

---

## Error Codes

Older versions of this skill said only `INSUFFICIENT_CREDITS` was a guaranteed code. 1.8.0's `docs/ERROR_CODES.md` documents these on credit calls:

| Code | Status | From |
|---|---|---|
| `INSUFFICIENT_CREDITS` | 402 | consume, reserve, settle: the spend exceeds the balance. Carries `available` and `requested`, no `status` |
| `PLAN_REQUIRED` | 402 | consume and reserve on a workspace with no plan while the org requires one. Thrown with that code and `status: 402` since 1.5.0 (before, every credit 402 read as `INSUFFICIENT_CREDITS`). `isPlanRequiredError(err)` from `/react` |
| `HOLD_NOT_FOUND` | 404 | settle or release of a hold this wallet does not have |
| `HOLD_NOT_OPEN` | 409 | settle of a hold already settled, released or expired; carries `status` |
| `PURCHASE_BEING_CONFIRMED` | none | `CreditActionsProvider`'s `purchase` while `purchaseGuard` is set; nothing was sent |
| `SUBSCRIPTION_CURRENCY_MISMATCH`, `PLAN_CURRENCY_UNAVAILABLE` | 400 | a purchase in a currency the pack or the wallet cannot be billed in |
| `CUSTOM_AMOUNT_INVALID`, `CUSTOM_AMOUNT_NOT_ALLOWED` | 400 | a purchase `amount` outside a chosen-price pack's range, or sent for a set price (`isCustomAmountRefusal`) |
| `STRIPE_NOT_CONNECTED` | 409 | a purchase before the app has connected Stripe |
| Auto top-up codes | 400 / 403 / 409 | see [Auto Top-Up](#auto-top-up) |

Plus the client-wide `rate_limited` (429) and `not_configured`. A failed purchase or consume also leaves the hook's `error` set, already translated.

---

## Credit vs Quota: When to Use Each

| Use credits when... | Use quotas when... |
|--------------------|-------------------|
| User pre-purchases capacity | Capacity is included in plan |
| Consumption doesn't reset each period | Consumption resets each period |
| You want marketplace-style billing | You want subscription-style billing |
| AI tokens, compute, one-off actions | API calls, storage, seats, emails |
