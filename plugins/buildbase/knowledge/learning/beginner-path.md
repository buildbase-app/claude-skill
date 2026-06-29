# Beginner Learning Path

A guided journey from zero to working Buildbase integration. Each milestone has a concrete deliverable, a "what success looks like" check, and checkpoint questions. Don't skip milestones — each one builds on the last.

> **This path is the journey and the checks. The full, commented code lives in one place: [quick-start.md](../sdk/quick-start.md).** That is the canonical golden-path setup guide. When a milestone needs setup code, you'll paste it from there rather than from divergent copies here. This keeps you from accidentally mixing two slightly different versions.

## Contents

- **Milestone 0: Orient** (Explorer) — what to read first, what to skip, the one mental model to internalize before code
- **Milestone 1: First Working Auth** (Beginner) — set up the project, then create the factory, three auth endpoints, and provider (all from quick-start.md); confirm you can sign in
- **Milestone 2: First Gate** (Beginner) — protect a page with `WhenAuthenticated`, understand the three gate states
- **Milestone 3: First Workspace Feature** (Builder) — create a feature flag in the dashboard, gate content, learn why dashboard-first matters
- **Milestone 4: First Billing Gate** (Builder) — connect Stripe, create a plan, gate by subscription and by plan, test the checkout flow
- **What's Next** — pointers to Advanced and Power User topics

---

## Milestone 0: Orient (Explorer Stage)

**Goal**: Understand what you're building before you touch code.

### What to read first
- The plain-language intro: [explain-buildbase-simply.md](../explain-buildbase-simply.md) — what Buildbase is, in jargon-free terms, with analogies
- The quick-start guide: [quick-start.md](../sdk/quick-start.md) — the canonical step-by-step setup you'll follow in Milestone 1
- This learning path

### What NOT to read yet
- The full README (2900 lines — overwhelming)
- Individual hook API references (auth.md, billing.md, etc.)
- The troubleshooting guide
- Webhook documentation

These are reference documents. Read them when you need them, not before you start.

### The one mental model to internalize before touching code

**Dashboard + Code = Features.**

Almost nothing in the SDK works without corresponding configuration in the Buildbase dashboard. Feature slugs, plan slugs, quota slugs — the code references them by name, but they must exist in the dashboard first.

A **slug** is a short lowercase id you create in the dashboard, like `pro` or `analytics`. Think of it like environment variables: you define the value in one place (the dashboard), reference it by name in another (your code). The dashboard is not optional for billing or feature flags.

### What success looks like for Milestone 0

You haven't written code yet — success here is *understanding*. You're ready to move on when the "Dashboard + Code = Features" idea feels obvious, and you know where the quick-start guide is.

### Checkpoint questions for Milestone 0

1. In one sentence, what does Buildbase do for your app? (Answer: it handles login, billing, and what users are allowed to do — see product-model.md.)
2. What must happen in the Buildbase dashboard before a feature flag works in code? (Answer: the feature must exist there first, with a slug your code references.)

#### Stretch questions (optional)
- Why can't you put `clientSecret` in a `NEXT_PUBLIC_` env var? (Answer: anything prefixed `NEXT_PUBLIC_` is shipped to the browser where anyone can read it; the secret must stay server-side. Covered in quick-start.md Step 2.)
- What is the `orgId` and where do you find it? (Answer: your organization's 24-character hex ID, from Dashboard → Settings → General. See the credentials table in quick-start.md.)

---

## Milestone 1: First Working Auth (Beginner Stage)

**Goal**: A user can sign in, and their session persists on page refresh.

### Step 0: Make sure you have the right kind of project

This path assumes a **Next.js (App Router) + TypeScript** app. If you don't already have one, create it:

```bash
npx create-next-app@latest my-app --typescript --app --src-dir --import-alias "@/*"
cd my-app
```

This sets up everything the code assumes: TypeScript, the App Router, a `src/` folder, and the `@/` import alias (which maps `@/` to `./src/*`, so `import { x } from '@/lib/buildbase'` finds `src/lib/buildbase.ts`). When prompted, the defaults are fine.

### Step 1: Follow the quick-start to wire up auth

Rather than re-paste setup code here (and risk it drifting out of sync), **follow [quick-start.md](../sdk/quick-start.md) Steps 1–7.** Full, commented code for every file is there — paste from it directly. Here's the map of what you'll create and why, so you understand the journey:

| File | What it is | quick-start step |
|---|---|---|
| `.env.local` | Your five credentials (server URL, orgId, clientId, redirectUrl, and the **secret** clientSecret) | Step 2 |
| `src/lib/buildbase.ts` | The **factory** — a function you call once that returns your configured Buildbase tools for server code | Step 3 |
| `src/app/api/auth/token/route.ts` | The most important file: trades the one-time login code for a `sessionId` and stores it in an **httpOnly cookie** (a cookie page scripts can't read, so it can't be stolen) | Step 4 |
| `src/app/api/auth/session/route.ts` | Read back the session on every page load so login survives refresh | Step 4 |
| `src/app/api/auth/signout/route.ts` | Clears the cookie to log out | Step 4 |
| `src/components/saas-provider.tsx` | The React provider that wraps your app. Starts with `'use client'` (tells Next.js this file runs in the browser; the SDK's hooks require it) | Step 5 |
| `src/app/layout.tsx` | Wrap your app in the provider **and** import the SDK CSS (`import '@buildbase/sdk/css'`) | Step 6 |
| `src/app/page.tsx` | A test sign-in page | Step 7 |

Two things worth knowing as you go (both confirmed in quick-start.md):
- **You don't write code to read the `?code=` from the URL** — the SDK does it automatically when the provider loads. You just need a page at your `redirectUrl` (the docs use `/callback`) that the provider wraps; quick-start Step 7 includes a tiny callback page.
- The token endpoint returns the shape `{ data: { sessionId, user } }` — that's why the token route reads `data.sessionId`.

### What success looks like for Milestone 1

Run `npm run dev`, open http://localhost:3000, and:
1. You see a **Sign In** button.
2. Clicking it sends you to the Buildbase login page.
3. After logging in, you're sent back to your app, which now greets you by name.
4. **Refresh the page — you stay logged in.** (That's the session cookie doing its job.)

If all four happen, auth works and you're done with Milestone 1.

### Common blockers at this stage

**"Nothing happens after clicking Sign In"**
→ Check that `/api/auth/token` exists and returns a 200. Open the Network tab in DevTools. Also confirm your `redirectUrl` is in the OAuth App's allowed redirect URLs in the dashboard.

**"Signed in but logged out on refresh"**
→ Check that `/api/auth/session` is reading the correct cookie name, and that the cookie is actually set (DevTools → Application → Cookies).

**"App crashes on load"**
→ Most likely an invalid `orgId` (must be 24 hex chars) or a missing env var. Remember to restart `npm run dev` after editing `.env.local`.

**"Auth modal doesn't look right / components are invisible"**
→ Missing `import '@buildbase/sdk/css'` in the root layout.

(The quick-start has a fuller troubleshooting table — see its "If something didn't work" section.)

### Checkpoint questions for Milestone 1

1. Why does the `clientSecret` live in the server route (`/api/auth/token`) and not in the browser provider? (Answer: the secret must never reach the browser; server routes never ship to the browser, so it's safe there.)
2. Where is the session stored so login survives a refresh? (Answer: in the httpOnly cookie set by the token route and read back by the session route.)

#### Stretch questions (optional)
- What does `handleAuthentication` receive, and what must it return? (Answer: it receives the one-time `code` from the login redirect and returns `{ sessionId }`. See the provider in quick-start.md Step 5.)
- Why must the three auth routes and the factory all use the same cookie name? (Answer: they read and write the same cookie; a mismatch means one route can't find what another stored — hence the shared `SESSION_COOKIE_NAME` constant.)

> **Heads up — you may see `JWT`, workspace tokens, or `onWorkspaceChange` mentioned elsewhere.** Those are an *advanced, optional* topic for multi-workspace apps. You do **not** need a second auth token for this path. The core `sessionId` is all you need to sign in and stay signed in. Skip that material for now.

---

## Milestone 2: First Gate (Beginner Stage)

**Goal**: Protect a page so only authenticated users can see it.

A **gate** is a `When…` component that shows its children only when a condition is true (and shows nothing, or a fallback, otherwise).

### Add WhenAuthenticated to protect a page

Remember the `'use client'` line — it tells Next.js this file runs in the browser, which the SDK hooks require.

```tsx
'use client';
import { WhenAuthenticated, WhenUnauthenticated, useSaaSAuth } from '@buildbase/sdk/react';

export default function DashboardPage() {
  const { signIn } = useSaaSAuth();
  return (
    <>
      <WhenUnauthenticated>
        <div>
          <h1>Please sign in</h1>
          <button onClick={() => signIn()}>Sign In</button>
        </div>
      </WhenUnauthenticated>
      <WhenAuthenticated>
        <div>
          <h1>Dashboard</h1>
          <p>You are authenticated.</p>
        </div>
      </WhenAuthenticated>
    </>
  );
}
```

### Understanding the three states

Every gate component has three states:

1. **Loading** — data is being fetched from Buildbase. The gate renders `null` (invisible) unless you provide a `loadingComponent`.
2. **Condition met** — renders children.
3. **Condition not met** — renders `null` (invisible) unless you provide a `fallbackComponent`.

States 1 and 3 look identical without `loadingComponent`. This confuses beginners.

```tsx
<WhenAuthenticated
  loadingComponent={<p>Loading...</p>}
  fallbackComponent={<button onClick={signIn}>Sign In</button>}
>
  <Dashboard />
</WhenAuthenticated>
```

### Common confusion: "why does my gate show nothing?"

Check in this order:
1. Is `isAuthenticated` from `useSaaSAuth()` true? If no, the user isn't signed in.
2. Is there a `loadingComponent`? Without it, loading looks like "not authenticated."
3. Is the CSS imported? Without it, components may render invisible.
4. Is the component using `'use client'`? Hooks don't work in server components.

### What success looks like for Milestone 2

Open the protected page while **signed out**: you see the "Please sign in" block. Sign in, then open it again: you see the "Dashboard" block instead. The content swaps based purely on auth state — no manual checks in your own code.

### Checkpoint questions for Milestone 2

1. What's the difference between `loadingComponent` and `fallbackComponent`? (Answer: `loadingComponent` shows while the SDK is still checking; `fallbackComponent` shows when the condition is *not* met.)
2. If `WhenAuthenticated` shows nothing even though you ARE signed in, what's the first thing to check? (Answer: whether it's stuck in the loading state — add a `loadingComponent` to tell loading apart from "not authenticated." Then check the CSS import.)

#### Stretch questions (optional)
- When would you read `useSaaSAuth().isAuthenticated` directly instead of using `WhenAuthenticated`? (Answer: when you need the boolean in your own logic — e.g. deciding what to fetch — rather than just showing/hiding JSX.)
- Can you use `WhenAuthenticated` in a Next.js Server Component? (Answer: no — it relies on SDK hooks, which need `'use client'`.)

---

## Milestone 3: First Workspace Feature (Builder Stage)

**Goal**: Gate content behind a feature flag that only specific workspaces have.

### Step 1: Create the feature in the dashboard first

Open Buildbase dashboard → Features → New Feature.
- Name: "Analytics Dashboard"
- Slug: `analytics` (a short lowercase id, no spaces — this is what your code will reference)

Save it.

### Step 2: Add the feature to a plan

Go to Plans → [Your Plan] → Features → Add Feature → select "Analytics Dashboard".

Save.

### Step 3: Gate content in code

```tsx
'use client';
import { WhenWorkspaceFeatureEnabled } from '@buildbase/sdk/react';

export default function AnalyticsPage() {
  return (
    <WhenWorkspaceFeatureEnabled
      slug="analytics"
      fallbackComponent={<p>Upgrade your plan to access analytics.</p>}
    >
      <AnalyticsDashboard />
    </WhenWorkspaceFeatureEnabled>
  );
}
```

### Why dashboard-first matters

If you skip steps 1 and 2, the gate will silently show the fallback for all users — even if they're on the paid plan. No error. Just silence. This is the most common "feature flags don't work" issue.

The dashboard is the source of truth for what features exist. The code only references them by slug, and the slug in code must **exactly** match the slug in the dashboard.

### What success looks like for Milestone 3

Sign in as a user whose workspace is on a plan that **includes** the `analytics` feature: the `AnalyticsDashboard` renders. Sign in as a user whose plan does **not** include it: they see the "Upgrade your plan" fallback (and if you removed the fallback, they'd see nothing at all). Same code, different result based on the workspace's plan.

### Checkpoint questions for Milestone 3

1. What happens if the feature slug in code doesn't exactly match the slug in the dashboard? (Answer: the gate finds no matching feature and silently shows the fallback for everyone — no error.)
2. Why might a workspace on the "Pro" plan still not see the feature? (Answer: because the feature has to be *added to the Pro plan* in the dashboard — being on Pro isn't enough by itself.)

#### Stretch questions (optional)
- How is `WhenWorkspaceFeatureEnabled` different from `WhenUserFeatureEnabled`? (Answer: one checks a feature on the current workspace, the other on the individual user. See feature-flags.md for the distinction.)
- Can you enable a feature for one specific workspace without it being on their plan? (Answer: this is an override-style case — check feature-flags.md before relying on it.)

---

## Milestone 4: First Billing Gate (Builder Stage)

**Goal**: Show different content to paid vs free users. Prompt free users to upgrade.

### Step 0: Connect Stripe first (a real prerequisite, not a one-liner)

Billing requires connecting Stripe **before** any plan can charge money. This is a separate onboarding step inside the dashboard (**Billing → Stripe Connect**) that takes roughly 10 minutes and needs a Stripe account. Until you finish it, plans you create won't be able to charge — checkout will not work. Treat this as a genuine prerequisite for the rest of this milestone, not a setting you flip in passing.

### Step 1: Create a plan in the dashboard

Buildbase dashboard → Plans → New Plan.
- Name: "Pro"
- Slug: `pro`
- Price: you can only set a real charging price once Stripe Connect (Step 0) is done.
- Trial: optional 14-day trial

### Step 2: Gate content by subscription

```tsx
'use client';
import {
  WhenSubscription,
  WhenNoSubscription,
  WhenTrialing,
  WhenTrialEnding,
} from '@buildbase/sdk/react';

export default function ProFeaturePage() {
  return (
    <>
      {/* Show trial warning */}
      <WhenTrialEnding daysThreshold={3}>
        <TrialEndingBanner />
      </WhenTrialEnding>

      {/* Show content to subscribed or trialing users */}
      <WhenSubscription fallbackComponent={<UpgradePrompt />}>
        <ProContent />
      </WhenSubscription>

      {/* Show upgrade CTA to users with no subscription */}
      <WhenNoSubscription>
        <UpgradePrompt />
      </WhenNoSubscription>
    </>
  );
}
```

### Step 3: Gate by specific plan

```tsx
<WhenSubscriptionToPlans
  plans={['pro', 'enterprise']}
  fallbackComponent={<p>This feature requires Pro or Enterprise.</p>}
>
  <EnterpriseFeature />
</WhenSubscriptionToPlans>
```

The plan slugs (`'pro'`, `'enterprise'`) must match plans you created in the dashboard.

### Test the checkout flow

Use the `PricingPage` component for a full self-serve checkout:

```tsx
import { PricingPage } from '@buildbase/sdk/react';

<PricingPage slug="main-pricing" redirectBaseUrl="http://localhost:3000/dashboard">
  {({ plans, selectPlan, loading }) => (
    <div>
      {plans.map(plan => (
        <div key={plan._id}>
          <h3>{plan.name}</h3>
          <button onClick={() => selectPlan(plan._id, 'monthly', 'usd')}>
            Subscribe
          </button>
        </div>
      ))}
    </div>
  )}
</PricingPage>
```

Two silent traps here:
- **`slug="main-pricing"` must match a pricing-page slug you created in the dashboard.** It's not a magic value. If your `PricingPage` renders empty (no plans), the slug probably doesn't exist yet — same dashboard-first rule as feature flags. Create the pricing page in the dashboard and use its exact slug.
- **`plan._id`** is the plan's unique ID from Buildbase (it comes from the `plans` array the component gives you). You pass it to `selectPlan` to say which plan the user chose.

Use Stripe test card `4242 4242 4242 4242` (any future expiry, any CVC) for testing — this only works after Stripe Connect (Step 0) is done.

### What success looks like for Milestone 4

A user with **no** subscription sees the `UpgradePrompt`; a subscribed or trialing user sees `ProContent`. The `PricingPage` lists your real plans from the dashboard, and clicking Subscribe with the test card completes a checkout and flips that user into the subscribed state. If the pricing page is empty, your slug or Stripe setup isn't done yet.

### Checkpoint questions for Milestone 4

1. Where does the plan slug `'pro'` come from — the code or the dashboard? (Answer: the dashboard. The code only references it by name.)
2. What must be done before any plan can actually charge a user? (Answer: Stripe Connect onboarding in the dashboard, Step 0.)

#### Stretch questions (optional)
- What's the difference between `WhenSubscription` and `WhenSubscriptionToPlans`? (Answer: the first checks for *any* active subscription; the second checks for a subscription to *specific named plans*.)
- A user on a trial sees content inside `WhenSubscription` — is that correct? (Answer: yes, trialing users count as having an active subscription for this gate. See billing.md if you need to treat trials separately.)
- After a user subscribes, how quickly does `WhenSubscription` reflect it? (Answer: once the SDK refreshes subscription state after checkout — see billing.md for the timing details.)

---

## What's Next

After completing all four milestones, you have a working Buildbase integration with:
- Auth (sign in, session persistence, sign out)
- Content gating (auth-based)
- Feature flags (plan-based)
- Billing gates (subscription, trial, specific plans)

**Recommended next steps** (Builder → Advanced):
- Add usage quota tracking: `knowledge/sdk/quota-usage.md`
- Add server-side usage recording in API routes: `knowledge/sdk/server-side.md`
- Workspace switching with JWT generation (the advanced multi-workspace topic flagged earlier): `knowledge/sdk/workspace.md`
- Handle billing webhooks: `knowledge/sdk/server-side.md` (webhook section)
- Complete production wiring, every file: `knowledge/patterns/nextjs-integration.md`
