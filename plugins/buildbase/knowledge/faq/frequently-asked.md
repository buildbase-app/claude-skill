# Frequently Asked Questions

## Contents

- [Installation & Setup](#installation--setup) - Next.js, React, Express, Stripe, no account yet, environments
- [Authentication](#authentication) - OAuth, sessions, staying logged in, enterprise SSO, importing users
- [Workspaces](#workspaces) - multi-workspace and creation rules
- [Billing](#billing) - pricing pages, upgrades, free plans, personal plans, add-ons
- [Feature Flags](#feature-flags) - creating and plan-linking flags
- [Quota & Credits](#quota--credits) - resets, overage, expiration
- [i18n](#i18n) - adding languages and RTL support
- [Notifications](#notifications) - email senders, transactional email, unsubscribe, push
- [Agents and the Console](#agents-and-the-console) - BuildBase's hosted MCP server, blueprints

## Installation & Setup

**Q: Can I use this with Next.js?**
Yes. Use `'use client'` in components using SDK hooks. The server-side `BuildBase()` factory works in API routes and Server Components. `npx @buildbase/sdk init` wires a Next.js, TanStack Start, Vite or Express app in one run. See [nextjs-integration.md](../patterns/nextjs-integration.md) for the complete pattern.

**Q: Can I use this with React 18 instead of 19?**
Yes. The peer dependency is `react@^18.0.0 || ^19.0.0`.

**Q: Can I use the server-side SDK with Express?**
Yes. Don't set `getSessionId` in the config. Use `withSession(req.headers['x-session-id'])` per request to get scoped action modules.

**Q: Do I need to install Stripe separately?**
No. Stripe is handled by Buildbase. You connect your own Stripe account in the Buildbase dashboard (Billing, Stripe payment setup). No Stripe server SDK in your app. The one optional exception: embedded checkout (`ui.behavior.checkoutMode: 'embedded'`) and taking a card inside the app (`useInAppPayment`) need `loadStripe` from `@stripe/stripe-js` passed to the provider.

**Q: Can I start before I have a Buildbase account?**
Yes. `npx @buildbase/sdk init --claim --yes` creates a claimable organization, writes its keys to `.env.local` and prints a claim URL and code. It is deleted after 72 hours unless a person claims it.

**Q: How do I keep test data out of production?**
Use a development or staging environment: same `orgId`, plus the environment's key as `environment` on the provider and on `BuildBase()`. Unset is production. `npx @buildbase/sdk init --dev` wires an app to one.

**Q: Is the SDK API stable?**
It follows semver since 1.0.0. A minor release adds; a change in behaviour is flagged in the changelog with a compatibility note.

---

## Authentication

**Q: How do I handle OAuth with multiple providers (Google + GitHub)?**
Auth method configuration is done in the Buildbase dashboard. Your code doesn't change - the SDK redirects to the Buildbase login page which handles multiple providers.

**Q: Can my customers sign in with their company's identity provider (SAML, OIDC) or sync their directory (SCIM)?**
Yes: enterprise SSO and Directory Sync, through the app owner's own WorkOS account. The SDK's `EnterpriseAccess` screen (the `enterprise` settings section) and the `useEnterprise*` hooks let a customer's admin set it up.

**Q: Can I move my existing users in from another auth provider?**
Yes, from Clerk, Auth0, Firebase or Supabase: `npx @buildbase/sdk import --from <source> <file>`, with `BUILDBASE_API_TOKEN` and `BUILDBASE_SERVER_URL` set (`--dry-run` first). If the app already has auth, ask the person before migrating.

**Q: Can I use the Buildbase SDK alongside next-auth?**
Yes. They use different cookie names and manage different sessions. Buildbase handles the SaaS platform layer; next-auth can handle your own user auth if needed.

**Q: How do I stay logged in after page refresh?**
This is handled by `getSession` callback. The SDK calls it on mount and restores the session from your httpOnly cookie. The cookie lasts as long as its `maxAge` (recommend 7 days); the session itself ends only when the platform refuses it (a 401, 403 or 404 on the page-load check). If the server can't be reached, the SDK keeps the session, sets `isSessionUnverified`, and retries: don't sign the user out on that.

**Q: The user gets logged out after they close the browser. Why?**
Check your cookie's `maxAge`. If you set it to a session cookie (no `maxAge`), it expires when the browser closes. Set `maxAge: 60 * 60 * 24 * 7` for 7 days.

---

## Workspaces

**Q: Can a user be in multiple workspaces simultaneously?**
A user can belong to many, but the SDK manages one `currentWorkspace` at a time. Use `switchToWorkspace(workspace)` - pass the workspace object (not an id) - to change.

**Q: How do I auto-select the first workspace on login?**
The SDK does this automatically. A new user gets a workspace of their own on first sign-in while "Auto-create first workspace" is on in the dashboard (`settings.workspace.autoCreateFirst`, on by default in both modes), and the SDK selects it and restores the last one on later visits. You can react to it with `handleEvent`:

```tsx
handleEvent: async (type, data) => {
  if (type === 'user:created' || type === 'workspace:created') {
    // First workspace was created - no action needed, SDK auto-selects
  }
}
```

**Q: Can I restrict workspace creation?**
Yes - in Platform mode, turn on Advanced overrides under Workspaces, Settings and set "Can create workspace" to Disabled (the choices are Everyone or Disabled). The first workspace made on first sign-in is not affected. In Personal mode users never create workspaces. No code change needed.

---

## Billing

**Q: How do I show a pricing page to unauthenticated users?**
Use the `PricingPage` component with a `redirectBaseUrl`:

```tsx
<PricingPage slug="main-pricing" redirectBaseUrl="https://app.com/dashboard">
  {({ plans, selectPlan, loading }) => { ... }}
</PricingPage>
```

`selectPlan()` handles the "redirect to sign in and come back" flow automatically. `<PricingPage for="user">` sells the person's own plan instead of the workspace's.

**Q: How do I know when a user upgrades their plan?**
In the browser, the SDK confirms the return from Stripe itself (a dialog by default; `useCheckoutStatus()` and `<CheckoutStatus />` on your own page; `ui.behavior.onCheckoutComplete` runs once on completion). On your server, listen for subscription webhook events from Buildbase, or poll `subscription.get(workspaceId)`.

**Q: How do I implement a free plan?**
Create a free plan in the dashboard with price $0. `useSelectFreePlan(workspaceId).selectFreePlan(planVersionId)` puts a workspace on it with no checkout. The org's onboarding mode (none, freemium, trial or require a plan) decides what a new workspace starts on. Or use `WhenNoSubscription` to show free-tier content.

**Q: How do I gate a paid feature?**
By its slug, with `useEntitlement(slug)` or `<WhenEntitled slug="...">`: they answer from the plan plus add-ons and overrides, so pricing changes need no code change. They fail open on an unknown slug; enforce on the server too.

**Q: Can I bill a person instead of a workspace?**
Yes, since 1.0.0. Put the plans in a pricing group whose payer is a person, and pass `{ user: true }` to the hooks (`useEntitlement(slug, { subject: { user: true } })`, `useSubscription({ user: true })`, the credit hooks). A person's plan and a workspace's are never merged.

**Q: Can I sell add-ons?**
Yes: one-time, lifetime, consumable or recurring add-ons on top of a plan. `useAddOns()` lists the catalog, `usePurchaseAddOn(subject)` buys one, and what it grants shows up in `useEntitlement`. Selling items, bookings and other commerce through the app is a separate surface: [../sdk/commerce.md](../sdk/commerce.md).

---

## Feature Flags

**Q: How do I create a feature flag?**
In the Buildbase dashboard → Features → New Feature. Define a name and slug. Then use the slug in your code.

**Q: Can feature flags be set per-workspace automatically based on plan?**
Yes. In the dashboard, associate features with plans. When a workspace upgrades, features are automatically enabled. For a feature you sell, `WhenEntitled` reads the same answer with the plan's provenance.

---

## Quota & Credits

**Q: Can quotas reset on a custom date instead of billing cycle?**
No - quotas reset at the start of each billing period (as defined by Stripe).

**Q: What happens when a workspace runs out of quota?**
- If overage is configured on the plan: usage continues, billed per-unit
- If no overage: `available` returns 0 and `allowOverage` is false. Gate actions with `WhenQuotaAvailable`, or check `available > 0` before proceeding.
- Note which shape you are holding. `hasOverage` and `allowOverage` are fields on the quota **status** (`useQuotaUsageStatus`, `useAllQuotaUsage`, `usage.getQuota`). The response from recording usage has no `hasOverage` - it returns `used`, `consumed`, `included`, `available`, `overage` and `billedAsync`.

**Q: Can credits expire?**
Yes - credit buckets can have expiration dates. Use `credits.getExpiring(workspaceId, 7)` to check credits expiring in the next 7 days.

---

## i18n

**Q: How do I add the SDK language support?**
Set the `locale` prop on `SaaSOSProvider`:

```tsx
<SaaSOSProvider locale="fr">{/* SDK UI renders in French */}</SaaSOSProvider>
```

Supported: `en`, `es`, `fr`, `de`, `ja`, `zh`, `hi`, `ar`

**Q: Does RTL (Arabic) work automatically?**
Yes. The `dir` attribute is set correctly on all SDK dialogs and components when `locale="ar"`.

---

## Notifications

**Q: Do I need to set up an email sender?**
Yes - connect one in the Buildbase dashboard (Messaging, Sender accounts): SMTP, Google, Mailgun or Amazon SES. Until one works, sign-in links, password resets and invitations cannot be delivered. The SDK's `notification.send()` and the server client's `emails.send()` go out through it; your app needs no email SDK.

**Q: Can I send a transactional email (a receipt, an order confirmation) from my server?**
Yes, since 1.0.0: `createServerClient({ serverUrl, apiToken }).emails.send({ to: { email }, templateId, data }, { idempotencyKey })` from `@buildbase/sdk/server`, with a template from the console. `subscribers.upsert` and the rest manage the audience. Server only, with an org API token whose role grants `emails_api_sends` (and `audience` for subscribers).

**Q: Can users unsubscribe from email notifications?**
Yes - automatically. The workspace settings dialog includes unsubscribe options for events with `userManaged: true`. Buildbase handles the unsubscribe tracking.

**Q: Is push notification support required?**
No - it's optional. If you don't serve the service worker at `/push-sw.js` (the SDK ships it as `PUSH_SERVICE_WORKER_SCRIPT`), push simply won't work but won't break anything.

---

## Agents and the Console

**Q: Can an AI agent set up my Buildbase organization for me?**
Yes. BuildBase hosts an MCP server at `https://api.console.buildbase.app/mcp` ("BuildBase Console"). Connect it in your AI client (listed in Claude's connectors directory; `npx @buildbase/sdk agent setup --console` for local clients) and sign in as yourself. The agent then works with your role in your organizations, and asks you to approve deletes and other destructive changes.

**Q: Is that the same as making my app agent-ready?**
No. That server manages Buildbase itself. Your app's own MCP server, which your users' agents connect to, is built with `@buildbase/sdk/mcp` (`createAgentStack`; `npx @buildbase/sdk init --agent` scaffolds it). See [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md).

**Q: Can I keep my console configuration in git?**
Yes: a blueprint, `buildbase.blueprint.json`, holds settings, sign-in, email, billing, roles, webhooks and workflows. `npx @buildbase/sdk blueprint validate`, then `plan`, then `apply` by an owner or admin with an admin key. Secrets are only ever written as `${env:NAME}`.
