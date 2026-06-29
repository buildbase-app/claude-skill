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

- An **org** is created once in the Buildbase dashboard. It's your product.
- A **workspace** is created by your users. It's their team/account.
- A **user** belongs to one or more workspaces with a role (owner, admin, member, etc.)
- Subscriptions, quotas, features, and credits belong to **workspaces**, not users.

**Rule**: When you need to check billing, quota, or features — you need `currentWorkspace._id`.

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
| Feature flags | Define features by slug |
| Quota tracking | Define quotas on plans |
| Notifications | Define events, attach email templates |
| Credits | Define credit packages |

**Rule**: If an SDK feature isn't working, check the dashboard first. The SDK only consumes what the dashboard configures.

---

### 4. Gates Return null While Loading

All gate components have three states:
1. **Loading** — returns null (or `loadingComponent` if provided)
2. **Condition met** — renders children
3. **Condition not met** — returns null (or `fallbackComponent` if provided)

This is by design. Gates that look "broken" are almost always in the loading state.

**Debug technique**: Add `loadingComponent={<span>Loading...</span>}` to any gate to distinguish loading from condition-not-met.

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

**The takeaway:** you only ever write **one** provider — `SaaSOSProvider`. Internally it sets up around fourteen sub-providers for you (auth, user, subscription, quota, credits, notifications, and so on), but you never touch those. One provider at the root is all your code has.

> *Curious about the internals?* The nesting order inside `SaaSOSProvider` is, roughly: Translation → SDK context → FullScreenLoader → Auth → Portal → ContextConfig → CheckoutConfig → PermissionConfig → User → Subscription → QuotaUsage → CreditBalance → PushNotification → WorkspaceSettings. You don't need this to build anything — it's here only if you're debugging deep context behavior.
