# Frequently Asked Questions

## Contents

- [Installation & Setup](#installation--setup) — Next.js, React, Express, Stripe
- [Authentication](#authentication) — OAuth, sessions, staying logged in
- [Workspaces](#workspaces) — multi-workspace and creation rules
- [Billing](#billing) — pricing pages, upgrades, free plans
- [Feature Flags](#feature-flags) — creating and plan-linking flags
- [Quota & Credits](#quota--credits) — resets, overage, expiration
- [i18n](#i18n) — adding languages and RTL support
- [Notifications](#notifications) — email providers, unsubscribe, push

## Installation & Setup

**Q: Can I use this with Next.js?**
Yes. The SDK is designed for Next.js. Use `'use client'` in components using SDK hooks. The server-side `BuildBase()` factory works in API routes and Server Components. See [nextjs-integration.md](../patterns/nextjs-integration.md) for the complete pattern.

**Q: Can I use this with React 18 instead of 19?**
Yes. The peer dependency is `react@^18.0.0 || ^19.0.0`.

**Q: Can I use the server-side SDK with Express?**
Yes. Don't set `getSessionId` in the config. Use `withSession(req.headers['x-session-id'])` per request to get scoped action modules.

**Q: Do I need to install Stripe separately?**
No. Stripe is handled by Buildbase. You connect your Stripe account in the Buildbase dashboard. No Stripe SDK in your app.

---

## Authentication

**Q: How do I handle OAuth with multiple providers (Google + GitHub)?**
Auth method configuration is done in the Buildbase dashboard. Your code doesn't change — the SDK redirects to the Buildbase login page which handles multiple providers.

**Q: Can I use the Buildbase SDK alongside next-auth?**
Yes. They use different cookie names and manage different sessions. Buildbase handles the SaaS platform layer; next-auth can handle your own user auth if needed.

**Q: How do I stay logged in after page refresh?**
This is handled by `getSession` callback. The SDK calls it on mount and restores the session from your httpOnly cookie. The session is valid for as long as your cookie's `maxAge` (recommend 7 days).

**Q: The user gets logged out after they close the browser. Why?**
Check your cookie's `maxAge`. If you set it to a session cookie (no `maxAge`), it expires when the browser closes. Set `maxAge: 60 * 60 * 24 * 7` for 7 days.

---

## Workspaces

**Q: Can a user be in multiple workspaces simultaneously?**
No. The SDK manages one `currentWorkspace` at a time. Use `switchToWorkspace(workspace)` — pass the workspace object (not an id) — to change.

**Q: How do I auto-select the first workspace on login?**
The SDK does this automatically when `autoCreateFirstWorkspace` is enabled in dashboard settings. You can also implement it using `handleEvent`:

```tsx
handleEvent: async (type, data) => {
  if (type === 'user:created' || type === 'workspace:created') {
    // First workspace was created — no action needed, SDK auto-selects
  }
}
```

**Q: Can I restrict workspace creation to admins only?**
Yes — configure "Can Create Workspace" to "Owner Only" or "Disabled" in the Buildbase dashboard. No code change needed.

---

## Billing

**Q: How do I show a pricing page to unauthenticated users?**
Use the `PricingPage` component with a `redirectBaseUrl`:

```tsx
<PricingPage slug="main-pricing" redirectBaseUrl="https://app.com/dashboard">
  {({ plans, selectPlan, loading }) => { ... }}
</PricingPage>
```

`selectPlan()` handles the "redirect to sign in and come back" flow automatically.

**Q: How do I know when a user upgrades their plan?**
Listen for subscription webhook events from Buildbase, or poll `subscription.get(workspaceId)` after the user returns from checkout.

**Q: How do I implement a free plan?**
Create a free plan in the dashboard with price $0. Workspaces can subscribe to it. Or use `WhenNoSubscription` to show free-tier content.

---

## Feature Flags

**Q: How do I create a feature flag?**
In the Buildbase dashboard → Features → New Feature. Define a name and slug. Then use the slug in your code.

**Q: Can feature flags be set per-workspace automatically based on plan?**
Yes. In the dashboard, associate features with plans. When a workspace upgrades, features are automatically enabled.

---

## Quota & Credits

**Q: Can quotas reset on a custom date instead of billing cycle?**
No — quotas reset at the start of each billing period (as defined by Stripe).

**Q: What happens when a workspace runs out of quota?**
- If overage is configured on the plan: usage continues, billed per-unit
- If no overage: `available` returns 0, `hasOverage` is false. Your code should gate actions using `WhenQuotaAvailable` or check `available > 0` before proceeding.

**Q: Can credits expire?**
Yes — credit buckets can have expiration dates. Use `credits.getExpiring(workspaceId, 7)` to check credits expiring in the next 7 days.

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

**Q: Do I need to set up an email provider?**
Yes — configure your email provider (Resend, SendGrid, etc.) in the Buildbase dashboard. The SDK `notification.send()` calls Buildbase which routes through your configured provider.

**Q: Can users unsubscribe from email notifications?**
Yes — automatically. The workspace settings dialog includes unsubscribe options for events with `userManaged: true`. Buildbase handles the unsubscribe tracking.

**Q: Is push notification support required?**
No — it's optional. If you don't create `public/push-sw.js`, push simply won't work but won't break anything.
