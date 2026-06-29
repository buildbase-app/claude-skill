# Feature Flags

A **feature flag** (or **feature**) is a simple on/off switch you use to decide whether a given user or workspace can see a piece of your app. Use it when you want to turn a capability on for some customers and off for others — ship a beta to a few users, unlock an add-on for a workspace, or pair a feature with a plan. (A **feature** is a yes/no capability switch; a **quota** — covered in [quota-usage.md](./quota-usage.md) — is a numeric limit like "5,000 API calls/month." Different things.)

> Feature flags assume sign-in already works — start with [quick-start.md](./quick-start.md) if it doesn't.

## Contents

- [What Feature Flags Are](#what-feature-flags-are) — boolean toggles on users/workspaces
- [Workspace Feature Gates](#workspace-feature-gates) — gate UI by workspace feature
- [User Feature Gates](#user-feature-gates) — gate UI by user feature
- [Feature Flags Hook (Programmatic)](#feature-flags-hook-programmatic) — check features in code
- [Workspace Feature Flags via useSaaSWorkspaces](#workspace-feature-flags-via-usesaasworkspaces) — read and toggle features
- [Feature Flag Best Practices](#feature-flag-best-practices) — slugs, plans, and overrides

## What Feature Flags Are

Feature flags in Buildbase are boolean toggles attached to:
- **Workspaces** — "This workspace has the analytics feature enabled"
- **Users** — "This user is in the beta program"

Feature flags are defined in the Buildbase dashboard. They can be:
- Included automatically with certain plans
- Manually toggled per workspace from the admin dashboard or by workspace admins

> **Dashboard-first rule — silent failure otherwise:** every feature **slug** (the short, case-sensitive text id like `advanced-analytics` you pass to the SDK) must be created in the dashboard BEFORE the code referencing it works. The SDK can only read and toggle features, never create them — reference a slug that doesn't exist and the gate simply renders nothing, with no error to tell you why.

---

## Workspace Feature Gates

A **gate** is a component that shows its children only when a condition is true (and renders nothing while the SDK is still loading — see the three-states note in [quick-start.md](./quick-start.md)). These gates check whether a feature is on for the current workspace.

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

The `slug` must match exactly what was defined in the Buildbase dashboard.

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

---

## Feature Flags Hook (Programmatic)

```tsx
import { useUserFeatures } from '@buildbase/sdk/react';

function FeatureCheck() {
  const { features, isFeatureEnabled, refreshFeatures } = useUserFeatures();

  // Programmatic check
  const hasPremium = isFeatureEnabled('premium-features');

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

---

## Workspace Feature Flags via useSaaSWorkspaces

```tsx
import { useSaaSWorkspaces } from '@buildbase/sdk/react';

function FeatureManager() {
  const { currentWorkspace, getFeatures, updateFeature } = useSaaSWorkspaces();

  const toggleFeature = async (slug: string, enabled: boolean) => {
    await updateFeature(currentWorkspace._id, slug, enabled);
  };

  return (
    <button onClick={() => toggleFeature('dark-mode', true)}>
      Enable Dark Mode
    </button>
  );
}
```

---

## Feature Flag Best Practices

1. **Define slugs in dashboard first** — The SDK can't create feature flags, only read and toggle them.
2. **Use workspace features for plan-gated features** — Associate features with plans in the dashboard.
3. **Use user features for individual overrides** — Beta access, staff features, etc.
4. **Slugs are case-sensitive** — `advanced-analytics` ≠ `Advanced-Analytics`.
5. **Both gate components and hooks work** — Use gates for UI, hooks for logic.
