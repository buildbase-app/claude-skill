# Workspace Management

This is how your app groups users and everything they own — billing, features, quotas, and members all hang off a workspace. You need it as soon as your app has the idea of a "team," an "account," or even just "this user's stuff." If a user can belong to more than one of these (or switch between them), this is the doc. New here? Get logged in first via [quick-start.md](./quick-start.md), then come back.

## Contents

- [What a Workspace Is](#what-a-workspace-is) — the tenant concept
- [useSaaSWorkspaces Hook](#usesaasworkspaces-hook) — primary state and actions
- [Switching Workspaces](#switching-workspaces) — switchTo vs setCurrent
- [WorkspaceSwitcher Component](#workspaceswitcher-component) — built-in render-prop switcher
- [IWorkspace Shape](#iworkspace-shape) — the workspace data type
- [User Attributes](#user-attributes) — arbitrary per-user key-values
- [Workspace Modes](#workspace-modes) — Platform vs Personal
- [Workspace Settings — Platform Mode Overrides](#workspace-settings--platform-mode-overrides) — dashboard config table

## What a Workspace Is

A workspace is the **tenant** — the isolated container that owns one customer's data — in your SaaS application. (Workspace and tenant mean the same thing here.) In B2B apps it's a company/team. In B2C apps (Personal Mode) it's one per user, created automatically.

Workspaces are the unit for:
- Subscriptions and billing
- Feature flags
- Quota usage
- Credits
- Member roles and permissions

---

## useSaaSWorkspaces Hook

The primary hook (a React function you call inside a component to read shared state and get actions) for all workspace operations:

```tsx
import { useSaaSWorkspaces } from '@buildbase/sdk/react';

function WorkspaceManager() {
  const {
    workspaces,          // IWorkspace[] — all workspaces user belongs to
    currentWorkspace,    // IWorkspace | null — currently selected workspace
    loading,             // true during initial fetch
    refreshing,          // true during background refresh
    switching,           // true during workspace switch
    switchingToId,       // string | null — workspace ID being switched to
    error,               // string | null

    // Actions
    fetchWorkspaces,        // () => Promise<void> — explicit fetch
    refreshWorkspaces,      // () => void — background refresh (no loading state)
    setCurrentWorkspace,    // (workspace) => void — direct set (no callback)
    switchToWorkspace,      // (workspace) => Promise<void> — full switch with onWorkspaceChange
    createWorkspace,        // (name, image?) => Promise<void>
    updateWorkspace,        // (workspace, data) => Promise<void>
    deleteWorkspace,        // (id) => Promise<void>
    getUsers,               // (id) => Promise<IWorkspaceUser[]>
    addUser,                // (id, email, role) => Promise<...>  — role = member's permission level (owner/admin/member)
    removeUser,             // (id, userId) => Promise<...>
    updateUser,             // (id, userId, { role }) => Promise<...>
    getFeatures,            // () => Promise<IWorkspaceFeature[]>
    updateFeature,          // (id, key, value) => Promise<IWorkspace>
    getProfile,             // () => Promise<IUser>
    updateUserProfile,      // (data) => Promise<IUser>
    updateWorkspaceSettings,   // (data: { permissions: Record<string, string[]> }) => Promise<...>
    updateWorkspacePermissions, // (id, permissions) => Promise<...>
  } = useSaaSWorkspaces();
}
```

---

## Switching Workspaces

Use `switchToWorkspace` (not `setCurrentWorkspace`) when the user clicks "Switch to workspace". It runs your `onWorkspaceChange` callback — a function the SDK calls *before* the switch completes, handy for prep like minting a new token (see [auth.md](./auth.md)) — before changing the active workspace:

```tsx
// switchToWorkspace: runs onWorkspaceChange callback first, then sets workspace
await switchToWorkspace(workspace);

// setCurrentWorkspace: directly sets without running onWorkspaceChange
// Use only when restoring state from storage, not for user-initiated switches
setCurrentWorkspace(workspace);
```

Show loading state during switch:

```tsx
const { switching, switchingToId } = useSaaSWorkspaces();

return (
  <div>
    {workspaces.map(w => (
      <button 
        key={w._id}
        onClick={() => switchToWorkspace(w)}
        disabled={switching}
      >
        {w.name}
        {switchingToId === w._id && ' (switching...)'}
      </button>
    ))}
  </div>
);
```

---

## WorkspaceSwitcher Component

Built-in workspace switcher with a render-prop (you pass a function that returns your own JSX, so the component handles the logic while you control the look) for custom UI:

```tsx
import { WorkspaceSwitcher } from '@buildbase/sdk/react';

function Header() {
  return (
    <WorkspaceSwitcher
      trigger={(isLoading, currentWorkspace) => {
        if (isLoading) return <div>Loading...</div>;
        if (!currentWorkspace) return <div>Select workspace</div>;
        return (
          <div className="flex items-center gap-2 cursor-pointer border rounded p-2">
            {currentWorkspace.image && (
              <img src={currentWorkspace.image} className="w-6 h-6 rounded" />
            )}
            <span>{currentWorkspace.name}</span>
          </div>
        );
      }}
    />
  );
}
```

---

## IWorkspace Shape

```ts
interface IWorkspace {
  _id: string;
  name: string;
  image?: string;
  workspaceId: string;
  users: IUser[];
  roles: string[];
  createdBy: string | IUser;
  features: Record<string, boolean>;
  quotas?: Record<string, number>;            // usage per quota slug
  limits?: Record<string, number | null>;     // subscription limit snapshot per slug
  subscription?: ISubscription | string | null;
  stripeCustomerId?: string;
  billingCurrency?: string | null;            // locked on first subscription
  permissions?: Record<string, string[]>;     // per-workspace overrides
  trialUsedAt?: string | null;                // set when workspace first uses a trial
}
```

The behaviors `canCreateWorkspace`, `canInviteMembers`, `showWorkspaceSwitcher`, `maxWorkspacesPerUser`, and `autoCreateFirstWorkspace` are **not** fields on the workspace object — they are configured in the Buildbase dashboard (see [Workspace Settings — Platform Mode Overrides](#workspace-settings--platform-mode-overrides)).

---

## User Attributes

Store arbitrary key-value data on a user:

```tsx
import { useUserAttributes } from '@buildbase/sdk/react';

function UserPreferences() {
  const { attributes, isLoading, updateAttribute, updateAttributes } = useUserAttributes();

  return (
    <div>
      <p>Theme: {attributes.theme ?? 'system'}</p>
      <button onClick={() => updateAttribute('theme', 'dark')}>Dark Mode</button>
      <button onClick={() => updateAttributes({ theme: 'light', lang: 'fr' })}>
        Update Multiple
      </button>
    </div>
  );
}
```

---

## Workspace Modes

**Platform Mode** (default): Multi-user, multi-workspace. Full settings UI.

**Personal Mode**: One workspace per user, auto-created. No invites, no switcher. Set in Buildbase dashboard — no code change needed.

---

## Workspace Settings — Platform Mode Overrides

Configured in the Buildbase dashboard (not in code):

| Setting | Options |
|---------|---------|
| Can Create Workspace | Everyone / Owner Only / Disabled |
| Can Invite Members | Everyone / Admin Only / Disabled |
| Show Workspace Switcher | On / Off |
| Max Workspaces Per User | 0 (unlimited) or N |
| Auto-Create First Workspace | On / Off |
