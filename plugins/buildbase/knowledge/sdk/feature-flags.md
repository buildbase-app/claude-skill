# Feature Flags

A **feature flag** (or **feature**) is a simple on/off switch you use to decide whether a given user or workspace can see a piece of your app. Use it when you want to turn a capability on for some customers and off for others - ship a beta to a few users, let a workspace's admins switch something on, or pair a feature with a plan. (A **feature** is a yes/no capability switch; a **quota** - covered in [quota-usage.md](./quota-usage.md) - is a numeric limit like "5,000 API calls/month." Different things.) Verified against `@buildbase/sdk` 1.9.0.

> Feature flags assume sign-in already works - start with [quick-start.md](./quick-start.md) if it doesn't.

## Contents

- [What Feature Flags Are](#what-feature-flags-are) - boolean toggles on users/workspaces, and who decides
- [Feature flag or entitlement?](#feature-flag-or-entitlement) - gating something you sell
- [Workspace Feature Gates](#workspace-feature-gates) - gate UI by workspace feature
- [User Feature Gates](#user-feature-gates) - gate UI by user feature
- [Feature Flags Hook (Programmatic)](#feature-flags-hook-programmatic) - check user features in code
- [Workspace Feature Flags via useSaaSWorkspaces](#workspace-feature-flags-via-usesaasworkspaces) - read and toggle features
- [From your server](#from-your-server) - the server factory and the org API
- [Feature Flag Best Practices](#feature-flag-best-practices) - slugs, plans, and overrides

## What Feature Flags Are

Feature flags in BuildBase are boolean toggles attached to:
- **Workspaces** - "This workspace has the analytics feature enabled"
- **Users** - "This user is in the beta program"

Feature flags are defined in the BuildBase dashboard (Users, then Features under Users or under Workspaces). A new flag is **off for everyone** until you switch it on (**Enable** on a user flag, **Enabled** on a workspace flag). Then one of these decides who has a workspace flag:
- **Subscription managed** - your plans: a plan that grants the flag turns it on for the workspaces on it
- **User managed** - each workspace's admins, on the Features settings screen in your app
- **Allowed to all** - every workspace (not available while Subscription managed is on)
- None of them - you, one workspace at a time, from the workspace's page in the console

A user flag is targeted to individual users, user tags or user lists in the console, to audience lists over the org API, or allowed for all users.

> **Dashboard-first rule - silent failure otherwise:** every feature **slug** (the short, case-sensitive text id like `advanced-analytics` you pass to the SDK, shown as **Feature ID** in the console) must be created in the dashboard BEFORE the code referencing it works. The SDK can only read and toggle features, never create them - reference a slug that doesn't exist and the gate simply renders nothing, with no error to tell you why. The Feature ID cannot be changed after it is created.

---

## Feature flag or entitlement?

To gate a capability you **sell** (on a plan or an add-on), prefer an entitlement check by slug: `useEntitlement(slug)` and `<WhenEntitled slug="...">` (since 1.0.0) answer from the server's composed entitlement (the plan plus anything granted on top), follow plan changes and add-ons, and tell a feature the plan locks from one it does not mention. They are covered in [billing.md](./billing.md). Feature flags remain the tool for rollouts, betas, per-workspace switches and anything a workspace's admins toggle themselves.

---

## Workspace Feature Gates

A **gate** is a component that shows its children only when a condition is true (and renders nothing while the SDK is still loading - see the three-states note in [quick-start.md](./quick-start.md)). These gates check whether a feature is on for the current workspace.

```tsx
import {
  WhenWorkspaceFeatureEnabled,
  WhenWorkspaceFeatureDisabled,
} from '@buildbase/sdk/react';

function Dashboard() {
  return (
    <div>
      {/* Render when feature is ON */}
      <WhenWorkspaceFeatureEnabled slug="advanced-analytics">
        <AdvancedAnalytics />
      </WhenWorkspaceFeatureEnabled>

      {/* Render when feature is OFF */}
      <WhenWorkspaceFeatureDisabled slug="advanced-analytics">
        <UpgradePrompt feature="Advanced Analytics" />
      </WhenWorkspaceFeatureDisabled>
    </div>
  );
}
```

The `slug` must match exactly what was defined in the BuildBase dashboard.

`WhenWorkspaceFeatureEnabled` also takes `whileUnknown` (since 1.0.0), for a slug the workspace has no value for yet, such as a flag created after the workspace loaded: `'allow'` renders the children, and the default, `'deny'`, renders nothing.

```tsx
<WhenWorkspaceFeatureEnabled slug="new-dashboard" whileUnknown="allow">
  <NewDashboard />
</WhenWorkspaceFeatureEnabled>
```

---

## User Feature Gates

```tsx
import {
  WhenUserFeatureEnabled,
  WhenUserFeatureDisabled,
} from '@buildbase/sdk/react';

function App() {
  return (
    <div>
      <WhenUserFeatureEnabled slug="beta-access">
        <BetaFeatures />
      </WhenUserFeatureEnabled>

      <WhenUserFeatureDisabled slug="beta-access">
        <BetaSignupForm />
      </WhenUserFeatureDisabled>
    </div>
  );
}
```

All four feature gates take `slug` and `children`; only `WhenWorkspaceFeatureEnabled` adds `whileUnknown`. They nest with permission, subscription and credit gates.

---

## Feature Flags Hook (Programmatic)

```tsx
import { useUserFeatures } from '@buildbase/sdk/react';

function FeatureCheck() {
  // 0.0.55: `refreshFeatures` and `isLoading` are deprecated aliases for
  // `refetch` and `loading`. Both still work.
  const { features, loading, error, refetch, isFeatureEnabled } = useUserFeatures();

  if (loading) return null;

  return (
    <button onClick={() => {
      if (!isFeatureEnabled('export')) {
        showUpgradeModal();
        return;
      }
      doExport();
    }}>
      Export
    </button>
  );
}
```

`features` is every user flag for the signed-in user as `{ [slug]: boolean }`. Flags are fetched with the session and cached; a change made in the console shows on the next page load, or after `refetch()`.

---

## Workspace Feature Flags via useSaaSWorkspaces

```tsx
import { useSaaSWorkspaces } from '@buildbase/sdk/react';

function FeatureManager() {
  const { currentWorkspace, allFeatures, updateFeature } = useSaaSWorkspaces();

  // allFeatures: IWorkspaceFeature[] ({ slug, name, description, userManaged, defaultValue, category, ... })
  const toggleable = allFeatures.filter(f => f.userManaged);

  const toggleFeature = async (slug: string, enabled: boolean) => {
    if (!currentWorkspace) return;
    try {
      await updateFeature(currentWorkspace._id, slug, enabled);
    } catch (err) {
      // 403 FEATURE_NOT_USER_MANAGED: a plan's feature, or one only your team sets
      console.error(err);
    }
  };

  return (
    <ul>
      {toggleable.map(f => (
        <li key={f.slug}>
          {f.name}{' '}
          <button onClick={() => toggleFeature(f.slug, !currentWorkspace?.features[f.slug])}>
            Toggle
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- A workspace can change only its **user-managed** features. Since 1.0.0 a request that names only features it may not change (a plan's, or one your team sets in the console) is refused with 403 `FEATURE_NOT_USER_MANAGED`, listing them in `features` (`PLATFORM_REFUSAL_CODE.FEATURE_NOT_USER_MANAGED`); before, the platform answered 200 and changed nothing.
- Toggling needs the `workspace:features:edit` permission; `workspace:features:view` reads.
- `getFeatures()` fetches the list again (`IWorkspaceFeature[] | null`; that type is not exported by name); `currentWorkspace.features` holds the workspace's values.
- The built-in screen does all of this: `openWorkspaceSettings('features')`.

---

## From your server

The server factory has `features.list()` (`IWorkspaceFeature[]`) and `features.update(workspaceId, key, value)` (`IWorkspace`), under the same user-managed rule (see [server-side.md](./server-side.md)). Who gets a **user** flag is changed with an org API token, not the session API: `PATCH /api/features/{id}/users/add` with `{ "users": [...] }`, and the matching `user-lists`, `audience-lists`, `tags` and `audience-tags` routes, each with a `/remove`. Adding a target needs a plan that includes advanced flag targeting; removing one never does. See [../http-api/org-api.md](../http-api/org-api.md).

---

## Feature Flag Best Practices

1. **Define slugs in dashboard first** - The SDK can't create feature flags, only read and toggle them. Switch a new flag on, or nobody has it.
2. **Sell with entitlements, roll out with flags** - Gate a plan or add-on capability with `useEntitlement` / `WhenEntitled` ([billing.md](./billing.md)); use flags for betas and switches.
3. **Use user features for individual overrides** - Beta access, staff features, etc.
4. **Slugs are case-sensitive** - `advanced-analytics` and `Advanced-Analytics` are different flags.
5. **Both gate components and hooks work** - Use gates for UI, hooks for logic.
6. **No built-in A/B analytics** - Track conversions yourself (workflows or your own analytics).
