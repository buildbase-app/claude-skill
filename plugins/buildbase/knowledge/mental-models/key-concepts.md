# Key Mental Models for Buildbase

## The Five Core Concepts

Understanding these five concepts is sufficient to integrate 90% of Buildbase features.

---

### 1. Org → Workspace → User

```
Org (your product/company)
  └── Workspace (a team/account — the thing that gets billed)
        └── User (a person with a role in this workspace)
```

A **workspace** is one customer account or team — the unit that holds a subscription and usage limits. (You'll also hear it called a "tenant," which is just SaaS jargon for the same idea.)

- An **org** is created once in the Buildbase dashboard (or, with no account yet, by `npx @buildbase/sdk init --claim --yes`, for a person to claim). It's your product. It can have development and staging **environments**, each with its own users and data; the `environment` prop picks one, and unset is production.
- A **workspace** is created by your users. It's their team/account.
- A **user** belongs to one or more workspaces with a role (`admin`, `editor`, `viewer`, or one the org defines).
- Subscriptions, quotas, features, and credits belong to **workspaces** by default. Since 1.0.0 a plan, a credit wallet and add-ons can also belong to one **user** (the `{ user: true }` subject), never merged with a workspace's.

**Rule**: When you need to check billing, quota, or features, name whose: `currentWorkspace._id` (or omit the subject, which means the selected workspace) for the team's plan, `{ user: true }` for the person's own.

---

### 2. The session is your login — that's all you need to start

When a user logs in, Buildbase gives you a **`sessionId`** (think of it as a coat-check ticket proving they're logged in). You store it in a secure cookie, and the SDK reads it back via your `getSession` callback. **For the whole beginner path, this one token is all you need.**

> **Advanced — you can ignore this until later.** Some apps *also* issue their own separate token (a **JWT**) so their *own* backend API can identify the user independently of Buildbase. That's a second, optional system. You do **not** need it to integrate Buildbase, and you should not build it on day one. If you ever see `onWorkspaceChange` generating a "workspace token," that's this advanced pattern — skip it for now.

| Token | What it's for | Needed to start? |
|-------|---------------|------------------|
| **sessionId** | Proves the user is logged in to Buildbase | ✅ Yes — this is the core |
| **Your own JWT** | Lets *your* backend identify the user separately | ❌ No — advanced, optional |

---

### 3. Dashboard Config + SDK Code = Features

Most SDK features require configuration in the Buildbase dashboard first:

| Feature | Dashboard setup required |
|---------|------------------------|
| Auth | Configure OAuth method, get clientId |
| Plans/Billing | Create pricing plans, connect Stripe |
| Entitlements and add-ons | Put the feature, limit or quota on the plan, or sell an add-on that grants it |
| Feature flags | Define features by slug |
| Quota tracking | Define quotas on plans |
| Notifications | Define events, attach email templates |
| Credits | Define credit packages |

**Rule**: If an SDK feature isn't working, check the dashboard first. The SDK only consumes what the dashboard configures. The configuration can also be one reviewed file (a blueprint, `npx @buildbase/sdk blueprint plan` then `apply`, by an owner or admin), and an agent can do the dashboard steps as the person through BuildBase's hosted MCP server (`https://api.console.buildbase.app/mcp`).

---

### 4. Gates Return null While Loading

The auth, subscription, trial, quota and credit gates have three states:
1. **Loading** - returns null (or `loadingComponent` if provided)
2. **Condition met** - renders children
3. **Condition not met** - returns null (or `fallbackComponent` if provided)

This is by design. Gates that look "broken" are almost always in the loading state.

Not every gate takes both props. The role and permission gates (`WhenRoles`, `WhenWorkspaceRoles`, `WhenPermission`) take `fallback`; the feature gates (`WhenWorkspaceFeatureEnabled` and the rest) take neither. The entitlement gates (`WhenEntitled`, `WhenUserEntitled`, `WhenLimitReached`, `WhenWithinLimit`) take both, but lock nothing while loading, and a slug the plan does not mention reads as `unknown`, which `WhenEntitled` renders as entitled unless `whileUnknown="deny"` or `strictAbsent`.

**Debug technique**: Add `loadingComponent={<span>Loading...</span>}` to a gate that takes it to distinguish loading from condition-not-met.

---

### 5. Provider Order Matters

The `SaaSOSProvider` wraps everything. All other SDK providers are nested inside it automatically. You don't add them manually.

```tsx
// Correct: one provider at root
<SaaSOSProvider ...>
  <App />  {/* WhenSubscription, useSaaSWorkspaces, etc. all work here */}
</SaaSOSProvider>

// Wrong: nested providers
<SaaSOSProvider>
  <SaaSOSProvider>  {/* Don't do this */}
    <App />
  </SaaSOSProvider>
</SaaSOSProvider>
```

**The takeaway:** you only ever write **one** provider - `SaaSOSProvider` (or `BuildBaseProvider`, the same component under its brand name). Internally it sets up close to twenty sub-providers for you (auth, workspaces, user, subscription, quota, credits, notifications, and so on), but you never touch those. One provider at the root is all your code has.

> *Curious about the internals?* In 1.8.0 the nesting order inside `SaaSOSProvider` is, roughly: Translation → SDK context → FullScreenLoader → Auth → Portal → ContextConfig → UIConfig → CheckoutConfig → EntitlementConfig → PermissionConfig → Workspace → McpConfig → User → Subscription → QuotaUsage → CreditBalance → PushNotification → (BuildBaseTracking, when `tracking` is set) → WorkspaceSettings. It changes between releases. You don't need this to build anything - it's here only if you're debugging deep context behavior.
