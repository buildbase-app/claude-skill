# Beginner Learning Path

A guided journey from zero to working BuildBase integration. Each milestone has a concrete deliverable, a "what success looks like" check, and checkpoint questions. Don't skip milestones: each one builds on the last.

> **This path is the journey and the checks. The full, commented code lives in one place: [quick-start.md](../sdk/quick-start.md).** That is the canonical golden-path setup guide, and its files are the ones `npx @buildbase/sdk init` writes (checked against `@buildbase/sdk` 1.9.0). When a milestone needs setup code, you'll paste it from there rather than from divergent copies here. This keeps you from accidentally mixing two slightly different versions.

## Contents

- **Milestone 0: Orient** (Explorer): what to read first, what to skip, the one mental model to internalize before code
- **Milestone 1: First Working Auth** (Beginner): set up the project, then let `init` write (or write yourself from quick-start.md) the factory, three auth endpoints and provider; confirm you can sign in
- **Milestone 2: First Gate** (Beginner): protect a page with `WhenAuthenticated`, understand the three gate states and session restore
- **Milestone 3: First Workspace Feature** (Builder): create a feature flag in the console, gate content, learn why console-first matters
- **Milestone 4: First Billing Gate** (Builder): connect Stripe, create and publish a plan and a pricing group, gate by subscription and by plan, test the checkout flow
- **What's Next**: pointers to Advanced and Power User topics

---

## Milestone 0: Orient (Explorer Stage)

**Goal**: Understand what you're building before you touch code.

### What to read first
- The plain-language intro: [explain-buildbase-simply.md](../explain-buildbase-simply.md): what BuildBase is, in jargon-free terms, with analogies
- The quick-start guide: [quick-start.md](../sdk/quick-start.md): the canonical step-by-step setup you'll follow in Milestone 1
- This learning path

### What NOT to read yet
- The SDK's full README (over 6,000 lines: overwhelming)
- Individual hook API references (auth.md, billing.md, etc.)
- The troubleshooting guide
- Webhook documentation

These are reference documents. Read them when you need them, not before you start.

### The one mental model to internalize before touching code

**Console + Code = Features.**

Almost nothing in the SDK works without corresponding configuration in the BuildBase console (console.buildbase.app, sometimes called the dashboard). Feature slugs, plan slugs, quota slugs: the code references them by name, but they must exist in the console first.

A **slug** is a short lowercase id you create in the console, like `pro` or `analytics`. Think of it like environment variables: you define the value in one place (the console), reference it by name in another (your code). The console is not optional for billing or feature flags.

### What success looks like for Milestone 0

You haven't written code yet; success here is *understanding*. You're ready to move on when the "Console + Code = Features" idea feels obvious, and you know where the quick-start guide is.

### Checkpoint questions for Milestone 0

1. In one sentence, what does BuildBase do for your app? (Answer: it handles login, billing, and what users are allowed to do. See explain-buildbase-simply.md.)
2. What must happen in the BuildBase console before a feature flag works in code? (Answer: the feature must exist there first, switched on, with a slug your code references.)

#### Stretch questions (optional)
- Why can't you put `clientSecret` in a `NEXT_PUBLIC_` env var? (Answer: anything prefixed `NEXT_PUBLIC_` is shipped to the browser where anyone can read it; the secret must stay server-side. Covered in quick-start.md Step 2.)
- What is the `orgId` and where do you find it? (Answer: your organization's 24-character hex ID, from **Settings** > **General** in the console, or the dialog shown when you create the auth client. See the credentials table in quick-start.md.)

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

### Step 1: Get the auth files, by command or by hand

**The fast way:** in the project folder,

```bash
npm install @buildbase/sdk
npx buildbase init --org-id <your 24-character org id>
```

`init` writes every file in the table below (and a webhook route), leaves the secrets empty in `.env.local`, and changes nothing if you run it again. Fill in the client id and client secret, allow-list `http://localhost:3000` on your auth client, and jump to "What success looks like". **No account yet?** `npx @buildbase/sdk init --claim --yes` creates a claimable organization and writes its keys for you; you claim it from the link it prints within 72 hours (quick-start.md, "No account yet").

**The learning way:** follow [quick-start.md](../sdk/quick-start.md) Steps 1 to 7 and write the same files yourself. Full, commented code for every file is there: paste from it directly. Either way, here's the map of what you'll have and why:

| File | What it is | quick-start step |
|---|---|---|
| `.env.local` | Your credentials (server URL, orgId, an optional environment key, clientId, redirectUrl) and the **secrets** (client secret, webhook secret) | Step 2 |
| `src/lib/buildbase.ts` | The **factory**: a function you call once that returns your configured BuildBase tools for server code | Step 3 |
| `src/app/api/auth/token/route.ts` | The most important file: trades the one-time login code for a `sessionId` and stores it in an **httpOnly cookie** (a cookie page scripts can't read, so it can't be stolen) | Step 4 |
| `src/app/api/auth/session/route.ts` | Reads back the session on every page load so login survives refresh | Step 4 |
| `src/app/api/auth/signout/route.ts` | Clears the cookie to log out | Step 4 |
| `src/components/saas-provider.tsx` | The React provider that wraps your app. Starts with `'use client'` (tells Next.js this file runs in the browser; the SDK's hooks require it) | Step 5 |
| `src/app/layout.tsx` | Wrap your app in the provider **and** import the SDK CSS (`import '@buildbase/sdk/css'`) | Step 6 |
| `src/app/page.tsx` | A test sign-in page | Step 7 |

Things worth knowing as you go (all confirmed in quick-start.md):
- **You don't write code to read the `?code=` from the URL.** The SDK does it automatically when the provider loads. You just need your `redirectUrl` to be a page the provider wraps; `init` uses the app root, `http://localhost:3000`, so no callback page is needed.
- The token route calls `exchangeCode({ code, clientId, clientSecret })` from the factory, which returns `{ sessionId }`, and `refuseCrossSiteAuthPost` first, so another site cannot sign your visitors in or out.
- `version={ApiVersion.V1}` is required; import `ApiVersion` from `@buildbase/sdk` (the root entry), not from `@buildbase/sdk/react`.

### What success looks like for Milestone 1

Run `npm run dev`, open http://localhost:3000, and:
1. You see a **Sign In** button (after a brief "Checking your session...").
2. Clicking it sends you to the BuildBase sign-in page.
3. After logging in, you're sent back to your app, which now greets you by name.
4. **Refresh the page: you stay logged in.** (That's the session cookie doing its job.)

If all four happen, auth works and you're done with Milestone 1.

### Common blockers at this stage

**"Nothing happens after clicking Sign In" or "Invalid redirect URL"**
→ Confirm your `redirectUrl` is on the auth client's **Redirect URLs** in the console, exactly. Then check that `/api/auth/token` returns a 200 in the Network tab of DevTools.

**"This app has no sign-in methods yet."**
→ Add a method on the **Methods** tab of Authentication and tick it on your auth client.

**"The sign-in code or magic link never arrives"**
→ No email sender is connected in the console (**Messaging** > **Sender accounts**).

**"Signed in but logged out on refresh"**
→ Check that `/api/auth/session` reads the same cookie name the token route sets (both import `SESSION_COOKIE_NAME`), and that the cookie is actually set (DevTools → Application → Cookies, `bb-session-id`).

**"Sign-in failed (401): Invalid client secret" in the browser console**
→ `BUILDBASE_CLIENT_SECRET` in `.env.local` is wrong or empty. Restart `npm run dev` after fixing it.

**"App crashes on load"**
→ Most likely an invalid `orgId` (must be 24 hex chars). An *empty* one does not crash: the provider just renders your app without BuildBase. Remember to restart `npm run dev` after editing `.env.local`.

**"Components are invisible"**
→ Missing `import '@buildbase/sdk/css'` in the root layout.

(The quick-start has a fuller troubleshooting table: see its "If something didn't work" section.)

### Checkpoint questions for Milestone 1

1. Why does the `clientSecret` live in the server route (`/api/auth/token`) and not in the browser provider? (Answer: the secret must never reach the browser; server routes never ship to the browser, so it's safe there.)
2. Where is the session stored so login survives a refresh? (Answer: in the httpOnly cookie set by the token route and read back by the session route.)

#### Stretch questions (optional)
- What does `handleAuthentication` receive, and what must it return? (Answer: it receives the one-time `code` from the login redirect and returns `{ sessionId }`. See the provider in quick-start.md Step 5.)
- Why must the three auth routes and the factory all use the same cookie name? (Answer: they read and write the same cookie; a mismatch means one route can't find what another stored. Hence the shared `SESSION_COOKIE_NAME` constant, which becomes `bb-session-id-<key>` when you set a development environment.)

> **Heads up: you may see `JWT`, workspace tokens, or `onWorkspaceChange` mentioned elsewhere.** Those are an *advanced, optional* topic for multi-workspace apps. You do **not** need a second auth token for this path. The core `sessionId` is all you need to sign in and stay signed in. Skip that material for now.

---

## Milestone 2: First Gate (Beginner Stage)

**Goal**: Protect a page so only authenticated users can see it.

A **gate** is a `When...` component that shows its children only when a condition is true (and shows nothing, or a fallback, otherwise).

### Add WhenAuthenticated to protect a page

Remember the `'use client'` line: it tells Next.js this file runs in the browser, which the SDK hooks require.

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

The auth, subscription and trial gates have three states:

1. **Loading**: data is being fetched from BuildBase. The gate renders `null` (invisible) unless you provide a `loadingComponent`.
2. **Condition met**: renders children.
3. **Condition not met**: renders `null` (invisible) unless you provide a `fallbackComponent`.

States 1 and 3 look identical without `loadingComponent`. This confuses beginners. (The feature-flag gates in Milestone 3 are simpler: they take only `slug` and `children`.)

```tsx
<WhenAuthenticated
  loadingComponent={<p>Loading...</p>}
  fallbackComponent={<button onClick={() => signIn()}>Sign In</button>}
>
  <Dashboard />
</WhenAuthenticated>
```

### Session restore: "loading" is not "signed out"

On every page load the provider renders your app straight away and restores the stored session in the background. While it does, `useSaaSAuth().isLoading` is `true` and `isAuthenticated` is `false`. That does **not** mean the user is signed out: don't redirect them to a login page or call `signIn()` yet. Gate on `isLoading` first.

If the server can't be reached to confirm the session (offline, a timeout, a server error), `isSessionUnverified` is `true` and the SDK keeps retrying: show "can't reach the server", never a sign-in prompt, and never sign the user out yourself. A session only ends when the API refuses it.

### Common confusion: "why does my gate show nothing?"

Check in this order:
1. Is `isLoading` from `useSaaSAuth()` still true? Then it's restoring the session (add a `loadingComponent` to see it).
2. Is `isAuthenticated` true? If not, the user isn't signed in.
3. Is the CSS imported? Without it, components may render invisible.
4. Is the component using `'use client'`? Hooks don't work in server components.

### What success looks like for Milestone 2

Open the protected page while **signed out**: you see the "Please sign in" block. Sign in, then open it again: you see the "Dashboard" block instead. The content swaps based purely on auth state, with no manual checks in your own code.

### Checkpoint questions for Milestone 2

1. What's the difference between `loadingComponent` and `fallbackComponent`? (Answer: `loadingComponent` shows while the SDK is still checking; `fallbackComponent` shows when the condition is *not* met.)
2. If `WhenAuthenticated` shows nothing even though you ARE signed in, what's the first thing to check? (Answer: whether it's still loading: add a `loadingComponent` to tell loading apart from "not authenticated." Then check the CSS import.)

#### Stretch questions (optional)
- When would you read `useSaaSAuth().isAuthenticated` directly instead of using `WhenAuthenticated`? (Answer: when you need the boolean in your own logic, e.g. deciding what to fetch, rather than just showing/hiding JSX. Check `isLoading` first.)
- Can you use `WhenAuthenticated` in a Next.js Server Component? (Answer: yes, as long as you pass it no functions: it is a client component already, like the optional `/callback` page in quick-start.md Step 7. Reading a hook such as `useSaaSAuth()` needs `'use client'`.)

---

## Milestone 3: First Workspace Feature (Builder Stage)

**Goal**: Gate content behind a feature flag that only specific workspaces have.

### Step 1: Create the feature in the console first

In the console's left rail choose **Users**, then **Features** under **Workspaces**, and press **Create feature**.
- Name: "Analytics Dashboard"
- Feature ID: `analytics` (the slug: a short lowercase id, no spaces. This is what your code will reference, and it cannot be changed later.)

Press **Create**. Then press **Edit** on its row, switch **Enabled** on (a new flag is off for everyone) and turn on **Subscription managed**, so your plans decide which workspaces have it. Press **Update**.

### Step 2: Grant the feature on a plan

In your plan's version (**Billing** > **Plans** > **Manage versions**, the draft version), set the feature's value on in **Feature values**, save, and publish the version. (Milestone 4 walks through plans and versions; billing needs Stripe connected first.)

### Step 3: Gate content in code

```tsx
'use client';
import { WhenWorkspaceFeatureDisabled, WhenWorkspaceFeatureEnabled } from '@buildbase/sdk/react';

export default function AnalyticsPage() {
  return (
    <>
      <WhenWorkspaceFeatureEnabled slug="analytics">
        <AnalyticsDashboard />
      </WhenWorkspaceFeatureEnabled>
      <WhenWorkspaceFeatureDisabled slug="analytics">
        <p>Upgrade your plan to access analytics.</p>
      </WhenWorkspaceFeatureDisabled>
    </>
  );
}
```

The feature-flag gates take only `slug` and `children` (no `loadingComponent` or `fallbackComponent`, unlike the auth and subscription gates), so the "otherwise" branch is its own gate, `WhenWorkspaceFeatureDisabled`. It also renders while the workspace is still loading, when every feature reads as off.

### Why console-first matters

If you skip steps 1 and 2, `WhenWorkspaceFeatureEnabled` silently renders nothing for all users (and the "Upgrade" branch shows), even if they're on the paid plan. No error. Just silence. This is the most common "feature flags don't work" issue.

The console is the source of truth for what features exist. The code only references them by slug, and the slug in code must **exactly** match the Feature ID in the console.

### What success looks like for Milestone 3

Sign in as a user whose workspace is on a plan that **grants** the `analytics` feature: the `AnalyticsDashboard` renders. Sign in as a user whose plan does **not** include it: they see the "Upgrade your plan" message (and without the `WhenWorkspaceFeatureDisabled` branch, they'd see nothing at all). Same code, different result based on the workspace's plan.

### Checkpoint questions for Milestone 3

1. What happens if the feature slug in code doesn't exactly match the Feature ID in the console? (Answer: the gate finds no matching feature and silently renders nothing for everyone, while the "Disabled" branch shows, with no error.)
2. Why might a workspace on the "Pro" plan still not see the feature? (Answer: the flag must be switched on, and the feature has to be *granted on the Pro plan's published version* in the console. Being on Pro isn't enough by itself.)

#### Stretch questions (optional)
- How is `WhenWorkspaceFeatureEnabled` different from `WhenUserFeatureEnabled`? (Answer: one checks a feature on the current workspace, the other on the individual user. See feature-flags.md for the distinction.)
- Can you enable a feature for one specific workspace without it being on their plan? (Answer: yes, for a flag that neither plans, workspace admins nor "Allowed to all" decide: open the workspace in the console and use its **Feature flags** card. See feature-flags.md.)
- What does `useEntitlement` / `WhenEntitled` add? (Answer: since SDK 1.0.0 they answer "may this workspace use X" with the plan's answer, follow plan changes and add-ons, and tell a locked feature from one the plan does not mention. See billing.md.)

---

## Milestone 4: First Billing Gate (Builder Stage)

**Goal**: Show different content to paid vs free users. Prompt free users to upgrade.

### Step 0: Connect Stripe first (a real prerequisite, not a one-liner)

BuildBase takes payments through **your own Stripe account**. In the console's left rail press **Billing**: until a Stripe secret key is saved it opens on **Stripe payment setup**. Paste your Stripe **publishable key** and **secret key** (test mode, `pk_test_...` and `sk_test_...`, from Stripe's **Developers > API keys**) and press **Save credentials**. Then, on **Billing** > **Credentials**, press **Check Stripe setup** and let it create the Stripe webhook endpoint (or make it by hand). Until the keys are saved, plans and pricing groups are not even offered, and without the webhook endpoint checkouts never turn into subscriptions.

### Step 1: Create a plan and publish a version

**Billing** > **Plans** > **Create plan**.
- Name: "Pro"
- Slug: `pro`

A plan's price and contents live on its **versions**: open **Manage versions**, create the first version, price it in each billing currency, set what it includes (Milestone 3's feature, limits, quotas), optionally a trial (**Trial configuration**), save, and press **Publish version**. A draft version is invisible to customers.

### Step 2: Put the plan in a published pricing group

**Billing** > **Pricing groups** > **Create group**: Name "Main pricing", Slug `main-pricing` (the slug your pricing page asks for). Add the published Pro version to the group's draft version, save, and **Publish version**.

### Step 3: Gate content by subscription

```tsx
'use client';
import {
  WhenSubscription,
  WhenNoSubscription,
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
      <WhenSubscription>
        <ProContent />
      </WhenSubscription>

      {/* Show upgrade CTA to users with no live subscription */}
      <WhenNoSubscription>
        <UpgradePrompt />
      </WhenNoSubscription>
    </>
  );
}
```

`WhenNoSubscription` is the exact complement of `WhenSubscription`, so exactly one of the two renders once loading is done. (Give `WhenSubscription` a `fallbackComponent` *instead of* using `WhenNoSubscription`, never both, or the prompt shows twice.)

### Step 4: Gate by specific plan

```tsx
<WhenSubscriptionToPlans
  plans={['pro', 'enterprise']}
  fallbackComponent={<p>This feature requires Pro or Enterprise.</p>}
>
  <EnterpriseFeature />
</WhenSubscriptionToPlans>
```

The plan slugs (`'pro'`, `'enterprise'`) must match plans you created in the console.

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
- **`slug="main-pricing"` must match a published pricing group's slug** (Step 2). It's not a magic value. If your `PricingPage` renders empty (no plans), the group or its plan version probably isn't published yet: same console-first rule as feature flags.
- **`plan._id`** is the id of a plan *version* from BuildBase (each entry of `plans` is a published plan version). You pass it to `selectPlan` to say which plan the user chose.

Use Stripe test card `4242 4242 4242 4242` (any future expiry, any CVC) for testing. This only works once your Stripe test keys are saved (Step 0).

### What success looks like for Milestone 4

A user with **no** subscription sees the `UpgradePrompt`; a subscribed or trialing user sees `ProContent`. The `PricingPage` lists your real plans from the console, and clicking Subscribe with the test card completes a checkout and flips that workspace into the subscribed state. If the pricing page is empty, your slug, publish steps or Stripe setup aren't done yet.

### Checkpoint questions for Milestone 4

1. Where does the plan slug `'pro'` come from: the code or the console? (Answer: the console. The code only references it by name.)
2. What must be done before any plan can actually charge a user? (Answer: your Stripe keys saved under Billing, with Stripe's webhook endpoint in place, and a published plan version in a published pricing group.)

#### Stretch questions (optional)
- What's the difference between `WhenSubscription` and `WhenSubscriptionToPlans`? (Answer: the first checks for *any* live subscription; the second checks for a subscription to *specific named plans*.)
- A user on a trial sees content inside `WhenSubscription`: is that correct? (Answer: yes. A live subscription is active, trialing until the trial ends, or past due while Stripe retries; one suspended by dunning does not count. `status="any"` counts every status. See billing.md if you need to treat trials separately.)
- After a user subscribes, how quickly does `WhenSubscription` reflect it? (Answer: once the SDK refreshes subscription state after checkout. See billing.md for the timing details.)

---

## What's Next

After completing all four milestones, you have a working BuildBase integration with:
- Auth (sign in, session persistence, sign out)
- Content gating (auth-based)
- Feature flags (plan-based)
- Billing gates (subscription, trial, specific plans)

**Recommended next steps** (Builder → Advanced):
- Add usage quota tracking: `knowledge/sdk/quota-usage.md`
- Add server-side usage recording in API routes: `knowledge/sdk/server-side.md`
- Workspace switching with JWT generation (the advanced multi-workspace topic flagged earlier): `knowledge/sdk/workspace.md`
- Handle billing webhooks (dedupe on `event.id`): quick-start.md Step 8 and `knowledge/sdk/server-side.md` (webhook section)
- Build against a development or staging environment instead of production: the `environment` setting (`NEXT_PUBLIC_BUILDBASE_ENVIRONMENT`, or `npx @buildbase/sdk init --dev`) in `knowledge/patterns/nextjs-integration.md`
- Complete production wiring, every file: `knowledge/patterns/nextjs-integration.md`
- Let your users' AI agents use your app (its own MCP server): `knowledge/mcp/mcp-and-agent-readiness.md`. Managing your BuildBase organization from an AI tool is a different thing: BuildBase's hosted MCP server, `https://api.console.buildbase.app/mcp`.
