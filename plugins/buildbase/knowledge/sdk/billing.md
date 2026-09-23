# Billing & Subscriptions

This is the part of Buildbase that **charges your users money** — turning a logged-in user into a paying customer. A **plan** is a product tier you sell (e.g. "Pro", "Enterprise"); a **subscription** is one workspace's active enrollment in a plan; a **trial** is a free period before billing starts. Reach for this once sign-in works ([quick-start.md](./quick-start.md)) and you want to gate features behind payment or show a pricing page.

> New to the SDK? Do [quick-start.md](./quick-start.md) first — billing builds on the auth foundation set up there.

## Contents

- [Overview](#overview) — how Buildbase handles Stripe billing
- [Subscription Gate Components](#subscription-gate-components) — show UI by subscription state
- [useSubscriptionContext Hook](#usesubscriptioncontext-hook) — read subscription data in code
- [Trial Gates](#trial-gates) — gate UI on trial status
- [Public Pricing Page](#public-pricing-page) — display plans without login
- [Server-Side Subscription](#server-side-subscription) — manage subscriptions from the backend
- [Multi-Currency Pricing Utilities](#multi-currency-pricing-utilities) — price/format helpers per currency
- [Affiliate / Referral Tracking](#affiliate--referral-tracking) — pass referral data to checkout

## Overview

Buildbase manages Stripe billing entirely. You:
1. Create plans in the Buildbase dashboard (connected to your Stripe account)
2. Use SDK gate components and hooks to control UI based on subscription state
3. The built-in workspace settings dialog handles plan selection, payment, and management

You do NOT need to write Stripe checkout code — the SDK handles it.

> **Four dashboard-first steps — silent failures otherwise.** Miss any one and `PricingPage` renders empty plans and `selectPlan()` fails:
> 1. **Connect Stripe** under **Billing → Credentials**. Use test keys for development. Without it nothing can take payment.
> 2. **Create a plan.**
> 3. **Publish a plan version.** Plans are versioned, and only published versions render.
> 4. **Set up a pricing group.** The `slug` you pass to `PricingPage` is the plan-group slug, and it must exist.
>
> A plan **slug** (the short URL-safe id like `pro`) that does not exist will not error loudly — the gate renders nothing and the picker comes up empty.

---

## Subscription Gate Components

A **gate** is a component that shows its children only when a condition is true (and, like all SDK gates, renders nothing while still loading — see the three-states note in [quick-start.md](./quick-start.md)). These gates check subscription state.

```tsx
import {
  WhenSubscription,
  WhenNoSubscription,
  WhenSubscriptionToPlans,
} from '@buildbase/sdk/react';

function BillingPage() {
  return (
    <div>
      {/* Any active subscription */}
      <WhenSubscription>
        <BillingDashboard />
      </WhenSubscription>

      {/* No subscription */}
      <WhenNoSubscription>
        <UpgradePrompt />
      </WhenNoSubscription>

      {/* Specific plans only (case-insensitive slug match) */}
      <WhenSubscriptionToPlans plans={['pro', 'enterprise']}>
        <AdvancedFeatures />
      </WhenSubscriptionToPlans>

      {/* With loading and fallback */}
      <WhenSubscription
        loadingComponent={<Skeleton />}
        fallbackComponent={<p>No subscription active.</p>}
      >
        <InvoiceList />
      </WhenSubscription>
    </div>
  );
}
```

| Component | Renders when |
|-----------|-------------|
| `WhenSubscription` | Workspace has any active subscription |
| `WhenNoSubscription` | Workspace has no subscription |
| `WhenSubscriptionToPlans` | Subscribed to one of the listed plan slugs |

---

## useSubscriptionContext Hook

```tsx
import { useSubscriptionContext } from '@buildbase/sdk/react';

function SubscriptionStatus() {
  const { response, loading, refetch } = useSubscriptionContext();

  if (loading) return <Spinner />;
  if (!response?.subscription) return <p>No active subscription</p>;

  const plan = response.plan ?? response.subscription?.plan;
  const sub = response.subscription;

  return (
    <div>
      <p>Plan: {plan?.name}</p>
      <p>Status: {sub?.subscriptionStatus}</p>
      <p>Period ends: {new Date(sub?.stripeCurrentPeriodEnd).toLocaleDateString()}</p>
      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

Refetch automatically triggers when:
- Current workspace changes
- Plan is updated, canceled, or resumed via SDK

---

## Trial Gates

A **trial** is a time-limited free period (configured per plan in the dashboard) where the user has access before being charged. These gates react to whether a workspace is currently in that period.

```tsx
import { WhenTrialing, WhenNotTrialing, WhenTrialEnding, useTrialStatus } from '@buildbase/sdk/react';

function TrialBanner() {
  const { isTrialing, daysRemaining, isTrialEnding } = useTrialStatus();

  if (!isTrialing) return null;

  return (
    <div>
      <p>Trial: {daysRemaining} days remaining</p>
      {isTrialEnding && <button>Upgrade Now</button>}
    </div>
  );
}

function Dashboard() {
  return (
    <>
      <WhenTrialing>
        <TrialBanner />
      </WhenTrialing>

      <WhenTrialEnding daysThreshold={7}>
        <UrgentUpgradeBanner />
      </WhenTrialEnding>
    </>
  );
}
```

| Component | Renders when |
|-----------|-------------|
| `WhenTrialing` | Status is `trialing` |
| `WhenNotTrialing` | Status is NOT `trialing` |
| `WhenTrialEnding` | Trialing AND within N days of end. The `daysThreshold` prop wins; otherwise `ui.behavior.trialEndingDays` on the provider; otherwise 3 |

---

## Public Pricing Page

Display plans without requiring login. The `slug` below is the **plan-group slug** (the id of a group of plans you arrange together in the dashboard) — it must already exist there, or the page renders empty.

```tsx
import { PricingPage } from '@buildbase/sdk/react';
import { formatCents, getBasePriceCents } from '@buildbase/sdk';

function PublicPricingPage() {
  return (
    <PricingPage 
      slug="main-pricing"           // Plan group slug from dashboard
      redirectBaseUrl="https://app.com/dashboard"  // For unauthenticated users
    >
      {({ loading, error, items, plans, selectPlan }) => {
        if (loading) return <Skeleton />;
        if (error) return <Error message={error} />;

        return (
          <div className="grid grid-cols-3 gap-6">
            {plans.map(plan => (
              <div key={plan._id} className="border rounded p-6">
                <h2>{plan.name}</h2>
                <p className="text-3xl font-bold">
                  {/* Never divide by 100 yourself: JPY and KRW have no minor
                      unit, KWD and BHD have three. formatCents handles all of
                      them. getBasePriceCents returns number | null. */}
                  {(() => {
                    const cents = getBasePriceCents(plan, 'usd', 'monthly');
                    return cents == null ? 'Contact us' : `${formatCents(cents, 'usd')}/mo`;
                  })()}
                </p>
                <button onClick={() => selectPlan(plan._id, 'monthly', 'usd')}>
                  {plan.trial?.enabled ? `Start ${plan.trial.durationDays}-Day Free Trial` : 'Get Started'}
                </button>
              </div>
            ))}
          </div>
        );
      }}
    </PricingPage>
  );
}
```

`selectPlan(planVersionId, interval, currency)`:
- If authenticated → opens built-in plan picker dialog
- If unauthenticated → **only resumes after login when `redirectBaseUrl` is set on `PricingPage`.** Without it the user is simply sent to sign-in and the plan choice is lost.

---

## Server-Side Subscription

```ts
import { auth, subscription } from '@/lib/buildbase';

export async function GET() {
  const session = await auth();
  if (!session) return Response.json({ error: 'Unauthorized' }, { status: 401 });

  // Get current workspace subscription
  const sub = await subscription.get(workspaceId);
  
  // Cancel at period end
  await subscription.cancel(workspaceId);
  
  // Resume canceled subscription
  await subscription.resume(workspaceId);
  
  // Get billing portal URL (Stripe-hosted portal)
  const { url } = await subscription.getBillingPortalUrl(workspaceId, returnUrl);
}
```

---

## Multi-Currency Pricing Utilities

```tsx
import {
  getPricingVariant,
  getBasePriceCents,
  formatCents,
  getCurrencySymbol,
  getStripePriceIdForInterval,
  isZeroDecimalCurrency,
  getCurrencyDecimals,
  minorAmountToDisplay,
  formatMinorAmountIntl,
} from '@buildbase/sdk';

// Get price for a plan in a specific currency
const variant = getPricingVariant(planVersion, 'eur');
const cents = getBasePriceCents(planVersion, 'eur', 'monthly'); // number | null
const display = cents == null ? null : formatCents(cents, 'eur'); // "€19.99"

// Zero-decimal and three-decimal currencies (SDK 0.0.54 / 0.0.55).
// NEVER divide a minor-unit amount by 100 yourself.
isZeroDecimalCurrency('jpy');            // true - no minor unit
getCurrencyDecimals('kwd');              // 3 - divide by 1000, per Stripe
minorAmountToDisplay(1000, 'jpy');       // 1000, not 10
formatMinorAmountIntl(1000, 'jpy', 'ja'); // locale-aware Intl formatting

// Get Stripe price ID for checkout
const priceId = getStripePriceIdForInterval(planVersion, 'usd', 'yearly');
```

---

## Affiliate / Referral Tracking

Pass referral data to Stripe checkout:

```tsx
<SaaSOSProvider
  getCheckoutStripeParams={async () => ({
    clientReferenceId: await getRewardfulReferralId(),
    subscriptionMetadata: { endorsely_referral: window.endorsely_referral },
    metadata: { campaign: 'summer-launch' },
  })}
>
```

| Field | Stripe mapping | Use case |
|-------|---------------|----------|
| `clientReferenceId` | `client_reference_id` | Rewardful, FirstPromoter |
| `metadata` | checkout session `metadata` | Custom tracking |
| `subscriptionMetadata` | `subscription_data.metadata` | Persists on subscription |
