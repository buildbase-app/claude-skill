# Billing & Subscriptions

This is the part of Buildbase that **charges your users money**: it turns a logged-in user into a paying customer. A **plan** is a product tier you sell (e.g. "Pro", "Enterprise"); a **subscription** is one workspace's (or one person's) enrollment in a plan; a **trial** is a free period before billing starts; an **add-on** is something bought on top of a plan. Reach for this once sign-in works ([quick-start.md](./quick-start.md)) and you want to gate features behind payment or show a pricing page.

> New to the SDK? Do [quick-start.md](./quick-start.md) first. Billing builds on the auth foundation set up there.

This file is about charging for **your** app. When the people in your app sell things to each other (a marketplace, a storefront, bookings, downloads), that is commerce: [commerce.md](./commerce.md). Prepaid credits are [credits.md](./credits.md); metered quotas are [quota-usage.md](./quota-usage.md).

Verified against `@buildbase/sdk` 1.8.0. The SDK's own reference for every name below is `node_modules/@buildbase/sdk/agents/react.md` (hooks, gates, components) and `agents/core.md` (API classes, codes, money helpers).

## Contents

- [Overview](#overview) - how Buildbase handles Stripe billing, and the console steps first
- [A workspace or a person](#a-workspace-or-a-person) - who the plan is sold to
- [Entitlement Checks by Slug](#entitlement-checks-by-slug) - gate a capability, not a plan name
- [Subscription Gate Components](#subscription-gate-components) - show UI by subscription state
- [useSubscriptionContext Hook](#usesubscriptioncontext-hook) - read subscription data in code
- [Trial Gates](#trial-gates) - gate UI on trial status
- [Seats](#seats) - per-seat pricing and the invite ceiling
- [Public Pricing Page](#public-pricing-page) - display plans without login, with prices in the server HTML (`initialData`)
- [Checkout: hosted, embedded, in the app](#checkout-hosted-embedded-in-the-app) - where the buyer pays
- [Add-ons](#add-ons) - buying on top of a plan
- [Server-Side Subscription](#server-side-subscription) - manage subscriptions from the backend
- [Retries and the Idempotency-Key](#retries-and-the-idempotency-key) - never charge twice
- [Refusals and Their Codes](#refusals-and-their-codes) - 402, 400, 409 and what each means
- [Money and Multi-Currency Utilities](#money-and-multi-currency-utilities) - format minor units, never `/ 100`
- [Renewal Terms](#renewal-terms) - what the SDK shows beside paid buttons, and `PricingPlanTerms` for yours
- [Affiliate / Referral Tracking](#affiliate--referral-tracking) - pass referral data to checkout

## Overview

Buildbase manages Stripe billing entirely. You:
1. Set billing up in the Buildbase console (connected to your own Stripe account; the platform fee is 0%)
2. Use SDK gate components and hooks to control UI based on subscription state and entitlements
3. Let the built-in settings dialog handle plan selection, payment, and management

You do NOT need to write Stripe checkout code. The SDK handles it.

> **Console first, in this order, or nothing renders.** Miss a step and `PricingPage` renders empty plans and `selectPlan()` fails:
> 1. **Connect Stripe** under **Billing > Credentials** (test keys in development or a Staging environment). The rest of the **Billing** menu appears only once the keys are saved.
> 2. **Currencies, product categories and products.** No plan version can be created until the organization has a billing currency.
> 3. **Create a plan and publish a version.** Plans are versioned, and only published versions render.
> 4. **Set up a pricing group.** The `slug` you pass to `PricingPage` is the plan-group slug, and it must exist.
> 5. **Run a test subscription** with a Stripe test card.
>
> A plan **slug** (the short URL-safe id like `pro`) that does not exist will not error loudly: the gate renders nothing and the picker comes up empty.

---

## A workspace or a person

Since 1.0.0 a plan can be sold to a **workspace** (the default) or to a **person** (their own plan, apart from any workspace). The subscription, checkout, cancel, portal, invoice, entitlement, add-on and credit hooks take `{ user: true }` in place of the workspace id for the signed-in person (`agents/react.md` lists which); the two are never merged. `useTrialEligibility`, `useConvertToPaid` and the quota hooks take a workspace id only.

| You want | Workspace | The signed-in person |
|---|---|---|
| Read the subscription | `useSubscription(workspaceId)` | `useSubscription({ user: true })` |
| Their billing screen | Plan & Billing in the settings dialog | `<AccountBilling />` on a page, or `useSaaSAuth().openAccountBilling()` |
| A pricing page | `<PricingPage slug="...">` | `<PricingPage slug="..." for="user">` |
| Gate a capability | `<WhenEntitled slug="...">` | `<WhenUserEntitled slug="...">` |
| Checkout, cancel, portal | `useCreateCheckoutSession(workspaceId)` and friends | the same hooks with `{ user: true }` |
| Server | `subscription.*` (by workspace id) | `bb.me.subscription.*` (the session's person) |

A named person's billing from your backend (not the session's person) needs an org API token: `BuildBase({ apiToken })`, then `bb.users.subscription.get(userId)`, `bb.users.usage.record(userId, ...)`, `bb.users.limits.*` and `bb.entitlements.check({ slug, user: '<userId>' })`. The token acts for the whole org, so keep it on the server. See [Server-Side Subscription](#server-side-subscription).

---

## Entitlement Checks by Slug

Gate a **capability** by its slug, not a plan by its name. `useEntitlement` answers from the server's composed entitlement (the plan plus add-ons, grants and overrides), so it keeps working when you rename a plan or sell the feature as an add-on. Prefer it to `WhenSubscriptionToPlans` (since 1.0.0).

```tsx
import { useEntitlement, useLimit, WhenEntitled, WhenWithinLimit } from '@buildbase/sdk/react';

function Projects({ projects }: { projects: { id: string }[] }) {
  const analytics = useEntitlement('advanced-analytics');                      // a feature
  const { reached, remaining } = useLimit('max-projects', { current: projects.length }); // a limit

  return (
    <>
      <WhenEntitled slug="advanced-analytics" fallbackComponent={<UpgradeCard />}>
        <Analytics />
      </WhenEntitled>

      <WhenWithinLimit slug="max-projects" current={projects.length} fallbackComponent={<UpgradeCard />}>
        <NewProjectButton />
      </WhenWithinLimit>

      {analytics.loading ? null : <p>{reached ? 'Project limit reached' : remaining != null ? `${remaining} left` : null}</p>}
    </>
  );
}
```

- **Fail open.** `allowed` is false only on an explicit no. Nothing locks while loading, a failed read is `unknown`, and a slug the plan does not mention is `unknown` (which allows) unless you pass `strictAbsent` (or `<SaaSOSProvider entitlement={{ strictAbsent: true }}>`).
- **Whose answer.** Omitted, `subject` is the selected workspace, never the person. Pass `subject: { user: true }` for the person's own plan, or `subjects: [{ user: true }, { workspaceId }]` to answer each from its own entitlement (`resolve: 'any'` by default; `useLimit` takes the highest ceiling).
- Gates: `WhenEntitled`, `WhenNotEntitled`, `WhenUserEntitled`, `WhenLimitReached`, `WhenWithinLimit`. There is no `useUserEntitlement`.
- After a change made elsewhere, `invalidateEntitlement()` refreshes `useEntitlement` and `useLimit`.
- Server: `bb.entitlements.check({ slug, workspaceId })` gives the same answer without React (see [server-side](#server-side-subscription)). Enforce on the server too: the gates only hide UI.

The slug must exist on the plan in the console first, like every slug.

---

## Subscription Gate Components

A **gate** is a component that shows its children only when a condition is true (and, like all SDK gates, renders nothing while still loading; see the three-states note in [quick-start.md](./quick-start.md)). These gates check subscription state.

```tsx
import {
  WhenSubscription,
  WhenNoSubscription,
  WhenSubscriptionToPlans,
} from '@buildbase/sdk/react';

function BillingPage() {
  return (
    <div>
      {/* A live subscription, any plan */}
      <WhenSubscription>
        <BillingDashboard />
      </WhenSubscription>

      {/* No live subscription */}
      <WhenNoSubscription>
        <UpgradePrompt />
      </WhenNoSubscription>

      {/* Specific plans only (case-insensitive slug match) */}
      <WhenSubscriptionToPlans plans={['pro', 'enterprise']}>
        <AdvancedFeatures />
      </WhenSubscriptionToPlans>

      {/* Any status, for a screen a lapsed customer still needs (fixing the card) */}
      <WhenSubscription
        status="any"
        loadingComponent={<Skeleton />}
        fallbackComponent={<p>No subscription.</p>}
      >
        <InvoiceList />
      </WhenSubscription>
    </div>
  );
}
```

| Component | Renders when |
|-----------|-------------|
| `WhenSubscription` | The current workspace has a **live** subscription |
| `WhenNoSubscription` | It has none (the exact complement, with the same `status`) |
| `WhenSubscriptionToPlans` | It holds a live subscription to one of the listed plan slugs |

**Live** (the default since 1.0.0, `status="live"`) means `active`, `trialing` until `trialEnd`, or `past_due` while Stripe retries, and not suspended by the platform's dunning ladder nor past a pause's paid period (`pause.accessUntil`). `canceled`, `unpaid`, `paused` and `incomplete` do not count. Before 1.0.0 these gates counted any subscription record; `status="any"` keeps that. Gating a capability? Use [entitlements](#entitlement-checks-by-slug) instead of a plan list.

---

## useSubscriptionContext Hook

```tsx
import { useSubscriptionContext, useTranslation } from '@buildbase/sdk/react';

function SubscriptionStatus() {
  const { response, loading, refetch } = useSubscriptionContext();
  const { formattingLocale } = useTranslation();

  if (loading) return <Spinner />;
  if (!response?.subscription) return <p>No active subscription</p>;

  const sub = response.subscription;
  const plan = response.plan ?? sub.plan;
  const periodEnd = sub.stripeCurrentPeriodEnd
    ? new Intl.DateTimeFormat(formattingLocale, { dateStyle: 'medium' }).format(new Date(sub.stripeCurrentPeriodEnd))
    : null;

  return (
    <div>
      <p>Plan: {plan?.name}</p>
      <p>Status: {sub.subscriptionStatus}</p>
      {periodEnd && <p>Period ends: {periodEnd}</p>}
      <button onClick={() => refetch()}>Refresh</button>
    </div>
  );
}
```

`response` is `ISubscriptionResponse`: `subscription`, `planVersion`, `plan`, `group`, and on current servers `entitlement`, `grants`, `capabilities` (whether the org lets customers pause, cancel now, or switch interval) and `planRequired`. `stripeCurrentPeriodEnd` is optional, so guard it before `new Date(...)`.

Refetch automatically triggers when:
- Current workspace changes
- Plan is updated, canceled, or resumed via SDK
- `invalidateSubscription()` is called (do that after a server-side change)

`useSubscription(workspaceId)` (or `{ user: true }`) is the same read outside the context: `{ subscription, loading, error, refetch }`.

---

## Trial Gates

A **trial** is a time-limited free period (configured per plan in the console) where the user has access before being charged. These gates react to whether the current workspace is in that period.

```tsx
import { WhenTrialing, WhenTrialEnding, useTrialStatus } from '@buildbase/sdk/react';

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

`useTrialStatus()` returns `{ isTrialing, daysRemaining, trialEndsAt, trialStartedAt, isTrialEnding }`. A trial is offered once per person: `useTrialEligibility(workspaceId)` says whether this user would get one, and on which plans. `useConvertToPaid(workspaceId)` ends a trial now and pays (`usePreviewTrialEnd` shows what it charges first). A plan's trial config is `trial { enabled, durationDays, requireCard }` on the plan version.

---

## Seats

When a plan prices per seat, `useSeatStatus(workspace, { pendingInvitations })` says where the workspace stands. Pass the pending invitations: each holds a seat, and the server counts them, so leaving them out offers an invite the server answers with 402.

```tsx
import { useSeatStatus, useSaaSWorkspaces, useTranslation, type TranslationKey } from '@buildbase/sdk/react';

function InviteGate({ pending }: { pending: number }) {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { t, fmtCents } = useTranslation();
  const seats = useSeatStatus(currentWorkspace, { pendingInvitations: pending });

  if (!seats.canInvite && seats.inviteBlockMessageKey) {
    return <p>{t(seats.inviteBlockMessageKey as TranslationKey, seats.inviteBlockMessageValues ?? undefined)}</p>;
  }
  return seats.nextSeatCostCents != null
    ? <p>Next member adds {fmtCents(seats.nextSeatCostCents, seats.currency)}</p>
    : null;
}
```

Fields include `hasSeatPricing`, `memberCount`, `includedSeats`, `maxUsers` (0 is unlimited), `billableSeats`, `availableSeats`, `isAtMax`, `isNearMax`, `perSeatPriceCents`, `seatPriceTiers`, `nextSeatCostCents`, `currency`, `canInvite`, `inviteBlockReason`. Pure helpers in the core: `calculateBillableSeats`, `getSeatPricing`, `getSeatPriceTiers`, `resolveMaxUsers`, `validateInvite`. An invitation past the plan's seats is refused with `SEAT_LIMIT_REACHED`.

---

## Public Pricing Page

Display plans without requiring login. The `slug` below is the **plan-group slug** (the id of a group of plans you arrange together in the console). It must already exist there, or the page renders empty.

```tsx
import { PricingPage, useTranslation } from '@buildbase/sdk/react';
import { getBasePriceCents } from '@buildbase/sdk';

function PublicPricingPage() {
  const { fmtCents } = useTranslation();
  return (
    <PricingPage
      slug="main-pricing"                          // Plan group slug from the console
      redirectBaseUrl="https://app.com/dashboard"  // Needed for signed-out visitors
    >
      {({ loading, error, plans, selectPlan, purchaseGuard }) => {
        if (loading) return <Skeleton />;
        if (error) return <p>{error}</p>;
        if (purchaseGuard) return <p>A purchase is being confirmed.</p>;

        return (
          <div className="grid grid-cols-3 gap-6">
            {plans.map(plan => {
              // Never divide by 100 yourself: JPY and KRW have no minor unit,
              // KWD and BHD have three. getBasePriceCents returns number | null.
              const cents = getBasePriceCents(plan, 'usd', 'monthly');
              return (
                <div key={plan._id} className="border rounded p-6">
                  <h2>{plan.name}</h2>
                  <p className="text-3xl font-bold">
                    {cents == null ? 'Contact us' : `${fmtCents(cents, 'usd')}/mo`}
                  </p>
                  <button onClick={() => selectPlan(plan._id, 'monthly', 'usd')}>
                    {plan.trial?.enabled ? `Start ${plan.trial.durationDays}-Day Free Trial` : 'Get Started'}
                  </button>
                </div>
              );
            })}
          </div>
        );
      }}
    </PricingPage>
  );
}
```

`selectPlan(planVersionId, interval, currency)`:
- Signed in: opens the built-in plan picker dialog (with `for="user"`, the person's own Billing on this group), which shows each paid plan's renewal terms and takes payment.
- Signed out (`AuthStatus.unauthenticated`): **only resumes after login when `redirectBaseUrl` is set on `PricingPage`.** Without it the user is simply sent to sign-in and the plan choice is lost.
- While the session is still being read, the press waits for the answer; it never sends a signed-in person to sign in.

### Prices in the server HTML (`initialData`, 1.9.0)

Without help, `PricingPage` fetches the plans in the browser, so the server HTML has a skeleton and the layout shifts when the prices arrive (the starter measured CLS 0.16). Since 1.9.0, fetch the plans on the server and pass them in: they render from the first render, server and client alike, and the hook still refreshes them in the background (a failed refresh keeps them on screen, with `error` null, and reports to `handleError`).

```tsx
// app/pricing/page.tsx - a server component. plans.getPublic needs no session.
import { plans } from '@/lib/buildbase';
import { PricingClient } from './pricing-client';

export default async function Page() {
  const initialData = await plans.getPublic('main-pricing').catch(() => null);
  return <PricingClient initialData={initialData} />;
}
```

```tsx
// app/pricing/pricing-client.tsx
'use client';
import type { IPublicPlansResponse } from '@buildbase/sdk';
import { PricingPage } from '@buildbase/sdk/react';

export function PricingClient({ initialData }: { initialData: IPublicPlansResponse | null }) {
  return (
    <PricingPage slug="main-pricing" initialData={initialData} redirectBaseUrl="https://app.com/dashboard">
      {({ plans }) => /* the same markup as above */ null}
    </PricingPage>
  );
}
```

`usePublicPlans(slug, { initialData })` takes the same option (type `UsePublicPlansOptions`). `initialData` is used only for the `slug` it was given with on the first render.

The render prop also carries `items`, `notes`, `refetch`, `promotion` (the `promotionCode` prop or `?promo=` in the URL, with `check`), `addOns` (`{ list, loading, error }`, the org's add-ons) with `selectAddOn(slug, currency?)`, and `purchaseGuard` (`'confirming'`, `'clearing'` or null: show it in place of the buy buttons while a buyer back from Stripe is being confirmed). For an interval toggle, `getAvailableBillingIntervals(plans, currency)` offers an interval only when some plan prices it (monthly is always in the list).

---

## Checkout: hosted, embedded, in the app

The plan picker, `useCreateCheckoutSession`, `usePurchaseAddOn` and the credit purchase all start a Stripe Checkout session. Where it opens is yours to choose:

| Mode | Set up | What the buyer sees |
|---|---|---|
| Hosted (default) | nothing | redirected to Stripe's page, then back |
| Embedded (since 1.0.0) | `loadStripe` from `@stripe/stripe-js` on the provider, plus `ui={{ behavior: { checkoutMode: 'embedded' } }}` | Stripe Checkout in a dialog on your page |
| In-app card and 3-D Secure (since 1.0.0) | `loadStripe` on the provider | a card added in the SDK's own dialog; a held plan change or recurring add-on finishes 3-D Secure in the page (`useInAppPayment`) |

```tsx
'use client';

import { ApiVersion } from '@buildbase/sdk';
import { SaaSOSProvider } from '@buildbase/sdk/react';
import { loadStripe } from '@stripe/stripe-js';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SaaSOSProvider
      serverUrl={process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!}
      version={ApiVersion.V1}
      orgId={process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!}
      loadStripe={loadStripe}
      ui={{ behavior: { checkoutMode: 'embedded' } }}
    >
      {children}
    </SaaSOSProvider>
  );
}
```

- The SDK never imports Stripe.js itself; the app installs `@stripe/stripe-js` and picks the version. Without `loadStripe`, or against an older platform, every checkout redirects to Stripe's page as before.
- This is the only way the org's Stripe **publishable key** reaches the browser: on an embedded checkout's answer and the in-app card answers. You never configure a publishable key yourself.
- Embedded needs the org's publishable key saved with its secret key, in the same Stripe mode: otherwise `STRIPE_PUBLISHABLE_KEY_MISSING` or `STRIPE_KEY_MODE_MISMATCH` (400), and the SDK opens the hosted page instead.
- `useInAppPayment(subject)` returns `{ available, addCard, authenticate, payWithNewCard, element }`; render `element` once. `available` is false without `loadStripe`, and the billing portal stays the way to change a card.
- **Back from Stripe** (since 1.2.0) the provider confirms the purchase in a dialog (`ui.behavior.checkoutReturn`: `'dialog'` default, `'screen'`, `'off'`). On your own route use `<CheckoutStatus />` or `useCheckoutStatus()`.
- Checkouts carry the app's language as `locale` (the provider's `locale`), so the renewal terms Stripe Checkout shows above Subscribe are in it.

---

## Add-ons

An add-on is bought on top of a plan: one-time, lifetime, consumable or recurring (since 1.0.0). Show and sell them with the hooks; **gate on entitlements** (`useEntitlement`), never on these lists.

```tsx
import { usePurchaseAddOn, useSaaSWorkspaces } from '@buildbase/sdk/react';
import { createAddOnPurchaseRedirectUrls } from '@buildbase/sdk';

function BuyExtraSeats() {
  const { currentWorkspace } = useSaaSWorkspaces();
  const { purchaseAddOn, loading, error } = usePurchaseAddOn(currentWorkspace?._id);

  const buy = async (retryKey?: string) => {
    if (!currentWorkspace) return;
    try {
      await purchaseAddOn(
        { offerSlug: 'extra-seats', quantity: 2, ...createAddOnPurchaseRedirectUrls(currentWorkspace._id) },
        retryKey ? { idempotencyKey: retryKey } : undefined,
      );
    } catch (err) {
      const e = err as { status?: number; idempotencyKey?: string };
      // No status = a timeout or network error: the purchase may have been made.
      // Retry THAT purchase once, under the key it was sent with, never a new one.
      if (!retryKey && e.status === undefined && e.idempotencyKey) await buy(e.idempotencyKey);
    }
  };

  return (
    <>
      <button onClick={() => buy()} disabled={loading}>Add 2 seats</button>
      {error && <p role="alert">{error}</p>}
    </>
  );
}
```

- `useAddOns({ currency? })` is the org's public catalog; `useWorkspaceAddOns(subject)` is what is on sale to the workspace or person (`purchasable`, `reason`) and what it holds; `useGrants(subject)` is what it holds beyond its plan, for display.
- `usePurchaseAddOn(subject)` redirects to Stripe for `checkout` (unless embedded), refreshes on `added`, and opens the invoice on `payment_required`; pass `redirect: false` to follow it yourself. It sends **one `Idempotency-Key` per call**, and every error it throws carries that key as `err.idempotencyKey`, the one the SDK made up included. Never derive a key from the add-on and quantity, or two purchases of the same add-on read as one.
- A recurring add-on bought while another purchase of it is in flight is refused 409 with nothing charged: `PURCHASE_SETTLING` (the hook sends it again once after `retryAfterSeconds`), `SUBSCRIPTION_PENDING_UPDATE` or `SUBSCRIPTION_BUSY` (`ADD_ON_PURCHASE_CODE`, `isPurchaseSettling`).
- Also: `useCancelAddOn`, `useDecreaseAddOn` (pass `expectedQuantity`; 409 `QUANTITY_CHANGED` when another tab moved it first), `usePreviewAddOnChange`, `useUpgradeAddOn`, `useAddOnFutureVersions`. Server: `bb.addOns.list`, `purchase`, `cancel`, `grants`.

---

## Server-Side Subscription

Add the names you need (`me`, `users`, `entitlements`, `addOns`) to what your `src/lib/buildbase.ts` exports from `BuildBase(...)` ([server-side.md](./server-side.md)).

```ts
import { auth, subscription, entitlements } from '@/lib/buildbase';

export async function POST(request: Request) {
  const session = await auth();
  if (!session) return Response.json({ error: 'Unauthorized' }, { status: 401 });

  // The workspace is your app's to choose; the SDK does not infer one server-side.
  const { workspaceId, returnUrl } = await request.json();

  const sub = await subscription.get(workspaceId);                 // ISubscriptionResponse
  const sso = await entitlements.check({ slug: 'sso', workspaceId }); // one slug, fails open

  // Stripe-hosted portal: minted per call and short-lived, so redirect now, never email it.
  const { url } = await subscription.getBillingPortalUrl(workspaceId, returnUrl);

  return Response.json({ plan: sub.plan?.name ?? null, sso: sso.allowed, portal: url });
}
```

The `subscription` namespace (by workspace id): `get checkout update preview getUpcomingInvoice getTrialEligibility selectFreePlan cancel cancelNow resume getRetentionOffer acceptRetentionOffer pause convertToPaid getBillingPortalUrl checkPromotionCode`. `cancel` is at the period end; `cancelNow` only when the org allows it (`capabilities.cancelNow`, else 403 `CANCEL_NOW_OFF`).

**The person's own plan** is `bb.me.subscription.*` (the same calls without the workspace id) on the session. **A named person's** needs the org API token:

```ts
import BuildBase from '@buildbase/sdk';

const bb = BuildBase({
  serverUrl: process.env.BUILDBASE_URL!,
  orgId: process.env.BUILDBASE_ORG_ID!,
  apiToken: process.env.BUILDBASE_API_TOKEN, // org API token: server only, acts for the whole org
});

export async function personPlan(userId: string) {
  const { subscription, standing } = await bb.users.subscription.get(userId);
  const keys = await bb.entitlements.check({ slug: 'api-keys', user: userId });
  return { status: subscription?.subscriptionStatus ?? null, standing, apiKeys: keys.allowed };
}
```

Without `apiToken` those `users.*` calls say so and send nothing. After any server-side change to a subscription, call `invalidateSubscription()` on the client so its contexts refetch.

---

## Retries and the Idempotency-Key

Since 1.0.0 every billing write sends an `Idempotency-Key`: `createCheckoutSession`, `updateSubscription`, `cancelSubscriptionAtPeriodEnd`, `pauseSubscription`, `resumeSubscription`, `convertToPaid`, `purchaseAddOn`, `purchaseCredits` and the other `WorkspaceApi` calls that change a Stripe subscription. Each sends a new UUID per call and takes your own as its last optional argument (`createBillingPortalSession` as `options.idempotencyKey`).

- When your code retries **the same action**, pass the same key: the platform answers with the first try's checkout or plan change, never a second.
- The same key with a **different request** is refused with **409 `IDEMPOTENCY_KEY_REUSED`**. A new action takes a new key.
- The SDK never retries a `POST` or `PATCH` that failed mid-flight for you, and the hooks send a new key per call. Retrying is the caller's job.

Commerce writes use the same header but answer a reused key with 422; see [commerce.md](./commerce.md).

---

## Refusals and Their Codes

Match on `err.code`, never the message. The full table is `node_modules/@buildbase/sdk/docs/ERROR_CODES.md`.

| Code | Status | Meaning |
|---|---|---|
| `PLAN_LIMIT_REACHED`, `QUOTA_EXHAUSTED`, `FEATURE_NOT_IN_PLAN` | 402 | A plan refused it (`PLAN_REFUSAL_CODE`). `FEATURE_NOT_IN_PLAN` is about the app's own BuildBase plan, never the end user's: show a neutral message |
| `PLAN_REQUIRED` | 402 | The org requires a plan before a workspace is used (since 1.1.0); usage and credit writes are refused until one is chosen. `isPlanRequiredError(err)` from `/react` |
| `NO_SUBSCRIPTION`, `SUBSCRIPTION_PAUSED`, `SUBSCRIPTION_PAST_DUE`, ... | 400 | The subscription's state refuses the operation (`SUBSCRIPTION_STATE_CODE`, eight codes) |
| `STRIPE_NOT_CONNECTED`, `STRIPE_CATALOG_SYNCING`, `LAPSE_HELD` | 409 | Platform refusals no plan moves (`PLATFORM_REFUSAL_CODE`) |
| `CANCEL_NOW_OFF`, `INTERVAL_SWITCH_OFF` | 403 | The org's customer billing settings (`CUSTOMER_BILLING_CODE`) |
| `IDEMPOTENCY_KEY_REUSED` | 409 | Same key, different request |
| `PROMOTION_CODE_INVALID` | 400 | `reason`: `not_found`, `currency_mismatch`, `not_applicable`, `refused_by_stripe` |
| `SUBSCRIPTION_CURRENCY_MISMATCH`, `PLAN_CURRENCY_UNAVAILABLE` | 400 | A currency the server will not bill in |

`planRefusalOf(err)` (since 1.6.0) reads a 402's numbers typed, so you can say "3 of 3 projects used" without casts:

```ts
import { planRefusalOf } from '@buildbase/sdk';

export function describeRefusal(err: unknown): string | null {
  const refusal = planRefusalOf(err);
  if (refusal?.code === 'PLAN_LIMIT_REACHED') return `${refusal.current} of ${refusal.limit} used`;
  if (refusal?.code === 'QUOTA_EXHAUSTED') return `Allowance used up; resets ${refusal.resetsAt ?? 'next period'}`;
  if (refusal?.code === 'FEATURE_NOT_IN_PLAN') return 'This feature is not available right now.';
  return null;
}
```

`upgradeTarget` on the refusal (`org`, `user` or `workspace`) says whose plan lifts it. The SDK's own hooks and screens word every code above in the reader's language; you only need this for your own UI.

---

## Money and Multi-Currency Utilities

Amounts are **minor units** of their currency. **Never divide by 100 yourself**: JPY and KRW have no minor unit, KWD and BHD have three. In React use `fmtCents` from `useTranslation()` (the active locale); elsewhere `formatCents` or `formatMinorAmountIntl`.

```tsx
import {
  getPricingVariant,
  getBasePriceCents,
  formatCents,
  getStripePriceIdForInterval,
  isZeroDecimalCurrency,
  getCurrencyDecimals,
  minorAmountToDisplay,
  formatMinorAmountIntl,
  minorAmountFromInput,
  type IPlanVersion,
} from '@buildbase/sdk';

export function priceTour(planVersion: IPlanVersion) {
  const variant = getPricingVariant(planVersion, 'eur');              // IPricingVariant | null
  const cents = getBasePriceCents(planVersion, 'eur', 'monthly');      // number | null
  const display = cents == null ? null : formatCents(cents, 'eur');    // "€19.99"

  isZeroDecimalCurrency('jpy');              // true: no minor unit
  getCurrencyDecimals('kwd');                // 3: divided by 1000, per Stripe
  minorAmountToDisplay(1000, 'jpy');         // "1,000" (a string), never "10"
  formatMinorAmountIntl(1000, 'jpy', 'ja');  // locale-aware Intl formatting
  minorAmountFromInput('19,99', 'eur');      // 1999: what someone typed, in minor units

  const priceId = getStripePriceIdForInterval(planVersion, 'usd', 'yearly');
  return { variant, display, priceId };
}
```

Also: `getCurrencySymbol`, `getAvailableCurrenciesFromPlans`, `getAvailableBillingIntervals`, `getQuotaOverageCents`, and for tiered prices `tierQuote`, `formatPriceTiers`, `priceTierRows`. A pay-what-you-want price (`customAmount`) takes its amount through `<CustomAmountInput>`, which answers minor units.

---

## Renewal Terms

Since 1.0.0 the SDK's own screens put auto-renewal terms beside every button that starts or changes a paid subscription or a recurring add-on (the plan picker, the change summary, End Trial, a recurring add-on's Buy): how often it renews, that it renews until cancelled, and at what charge, in the reader's language. Stripe Checkout shows its own terms above Subscribe, in the app's `locale`. So a pricing page whose button calls `selectPlan` reaches payment through the terms. If you build a paid button of your own on a `PricingPage` card, put `<PricingPlanTerms plan={plan} currency="usd" interval="monthly" id={termsId} />` (1.9.0) beside it and `aria-describedby={termsId}` on the button: it says every interval the plan sells with its price (`showIntervals={false}` hides that list), the one-time setup fee sentence, and the auto-renewal terms of the interval the button buys, in the reader's language. Renewal terms beside every paid button are a legal requirement (California's Automatic Renewal Law). Before 1.9.0 there was no public component, and you wrote them yourself.

---

## Affiliate / Referral Tracking

Pass referral data to Stripe checkout:

```tsx
<SaaSOSProvider
  serverUrl={process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!}
  version={ApiVersion.V1}
  orgId={process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!}
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
| `promotionCode` | applied to the session | A code the customer typed; an unusable one is refused before any session (`PROMOTION_CODE_INVALID`) |

Metadata values are strings (`Record<string, string>`). For affiliates of things your users sell (commerce), see [commerce.md](./commerce.md#affiliates).
