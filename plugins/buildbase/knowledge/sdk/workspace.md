# Workspace Management

This is how your app groups users and everything they own - billing, features, quotas, and members all hang off a workspace. You need it as soon as your app has the idea of a "team," an "account," or even just "this user's stuff." If a user can belong to more than one of these (or switch between them), this is the doc. New here? Get logged in first via [quick-start.md](./quick-start.md), then come back. Verified against `@buildbase/sdk` 1.8.0.

## Contents

- [What a Workspace Is](#what-a-workspace-is) - the tenant concept
- [useSaaSWorkspaces Hook](#usesaasworkspaces-hook) - primary state and actions
- [Loading and "no workspace"](#loading-and-no-workspace) - `loading` vs `loaded`
- [Switching Workspaces](#switching-workspaces) - switchTo vs setCurrent
- [WorkspaceSwitcher Component](#workspaceswitcher-component) - built-in render-prop switcher
- [Members, invitations and leaving](#members-invitations-and-leaving) - addUser vs inviteMember, pending invitations
- [Roles and permissions](#roles-and-permissions) - built-in roles, `usePermissions`, `WhenPermission`
- [IWorkspace Shape](#iworkspace-shape) - the workspace data type
- [User Attributes](#user-attributes) - arbitrary per-user key-values
- [Workspace Modes](#workspace-modes) - Personal vs Platform
- [Workspace Settings: Advanced Overrides](#workspace-settings-advanced-overrides) - dashboard config table

## What a Workspace Is

A workspace is the **tenant** - the isolated container that owns one customer's data - in your SaaS application. (Workspace and tenant mean the same thing here.) In B2B apps it's a company/team. In B2C apps (Personal Mode) it's one per user, created automatically.

Workspaces are the unit for:
- Subscriptions and billing (a person can also hold a plan of their own; see [billing.md](./billing.md))
- Feature flags
- Quota usage
- Credits
- Member roles and permissions

The types `IWorkspace`, `IUser`, `IUserProfile` and `ISettings` are exported from both `@buildbase/sdk` and `@buildbase/sdk/react`.

---

## useSaaSWorkspaces Hook

The primary hook (a React function you call inside a component to read shared state and get actions) for all workspace operations:

```tsx
import { useSaaSWorkspaces } from '@buildbase/sdk/react';

function WorkspaceManager() {
  const {
    workspaces,          // IWorkspace[] - all workspaces user belongs to
    currentWorkspace,    // IWorkspace | null - currently selected workspace
    loading,             // true until the first list is in for anyone not signed out
    loaded,              // true once the list has been answered since sign-in (fetched or failed)
    refreshing,          // true during background refresh
    switching,           // true during workspace switch
    switchingToId,       // string | null - workspace ID being switched to
    error,               // string | null
    allFeatures,         // IWorkspaceFeature[] - the org's workspace features

    // Workspaces
    fetchWorkspaces,        // () => Promise<void> - explicit fetch
    refreshWorkspaces,      // () => Promise<void> - background refresh (no loading state)
    getWorkspace,           // (id) => Promise<IWorkspace>
    setCurrentWorkspace,    // (workspace, { forceEmit? }?) => void - direct set (no callback)
    switchToWorkspace,      // (workspace, { forceEmit? }?) => Promise<void> - full switch with onWorkspaceChange
    resetCurrentWorkspace,  // () => void - clear the current workspace
    createWorkspace,        // (name, image?) => Promise<void>
    updateWorkspace,        // (workspace, data: Partial<IWorkspace>) => Promise<void>
    deleteWorkspace,        // (id) => Promise<unknown> - the workspace's creator only
    leaveWorkspace,         // (id) => Promise<IWorkspaceLeaveResponse> - leave as the signed-in member

    // Members
    getUsers,               // (id) => Promise<IWorkspaceUser[]>
    addUser,                // (id, email, role) => Promise<{ userId }> - an EXISTING account only
    removeUser,             // (id, userId) => Promise<{ userId }>
    updateUser,             // (id, userId, { role }) => Promise<{ userId, workspace, message }>

    // Invitations (an address that may have no account yet)
    inviteMember,           // (id, email, role, { landingUrl? }?) => Promise<IWorkspaceInvitation>
    listInvitations,        // (id) => Promise<IWorkspaceInvitation[]>
    resendInvitation,       // (id, invitationId) => Promise<IWorkspaceInvitation>
    revokeInvitation,       // (id, invitationId) => Promise<void>
    myInvitations,          // () => Promise<IWorkspaceInvitation[]> - the signed-in user's own
    acceptInvitation,       // (invitationId, { token? }?) => Promise<{ invitation, workspace }>
    declineInvitation,      // (invitationId) => Promise<IWorkspaceInvitation>
    previewInvitation,      // (token) => Promise<IWorkspaceInvitationPreview>

    // Features, profile, permissions
    getFeatures,            // () => Promise<IWorkspaceFeature[] | null>
    updateFeature,          // (id, key, value) => Promise<IWorkspace> - user-managed features only
    getProfile,             // () => Promise<IUserProfile>
    updateUserProfile,      // (data: Partial<IUser>) => Promise<IUserProfile>
    updateWorkspacePermissions, // (id, permissions: Record<string, string[]>) => Promise<unknown>
    updateWorkspaceSettings,    // deprecated: refused with 403 WORKSPACE_SETTINGS_ORG_WIDE
  } = useSaaSWorkspaces();
}
```

Platform limits on the writes: a workspace name is at most 200 characters and not blank; `updateWorkspacePermissions` takes at most 100 roles, 300 permissions per role and 128 characters per key. `createWorkspace` follows `ui.behavior.autoOpenPlanDialog` (set it to `false` to keep the plan picker from opening after a create). `getProfile()` resolves to `IUserProfile`: read `profile.id`, since `_id` is deprecated there and undefined at runtime.

---

## Loading and "no workspace"

`loading` is true until the first workspace list is in for anyone who is signed in or may be: while the session is still being read, and while it is kept but unverified during an outage (see [auth.md](./auth.md)). Only a signed-out visitor reads `loading: false` with no list. `loaded` (1.0.0) turns true once the list has been answered since sign-in, fetched (even empty) or failed with `error`. So:

```tsx
const { loading, loaded, currentWorkspace } = useSaaSWorkspaces();

if (loading) return <Skeleton />;
if (loaded && !currentWorkspace) return <NoWorkspaceScreen />; // really none
```

Two behaviours behind it, both since 1.0.0:
- When the organization makes a person's first workspace (`autoCreateFirst`, on unless turned off), an empty first list is asked for once more after 1.5 s, because the platform creates that workspace on the first read and a racing read can answer `[]`.
- A list that failed (timeout, server down) is asked for again with backoff (up to one ask every 30 s) and when the browser comes back online, until it is in.

---

## Switching Workspaces

Use `switchToWorkspace` (not `setCurrentWorkspace`) when the user clicks "Switch to workspace". It runs your `onWorkspaceChange` callback - a function the SDK calls *before* the switch completes, handy for prep like minting a new token (see [auth.md](./auth.md)) - before changing the active workspace. If that callback rejects, the switch is aborted:

```tsx
// switchToWorkspace: runs onWorkspaceChange callback first, then sets workspace
await switchToWorkspace(workspace);

// setCurrentWorkspace: directly sets without running onWorkspaceChange
// Use only when restoring state from storage, not for user-initiated switches
setCurrentWorkspace(workspace);
```

Show loading state during switch:

```tsx
const { workspaces, switching, switchingToId, switchToWorkspace } = useSaaSWorkspaces();

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

The lifecycle lives in the one `WorkspaceProvider` that `SaaSOSProvider` mounts, so `onWorkspaceChange` and `workspace:changed` fire exactly once per switch however many components use the hook.

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
              <img src={currentWorkspace.image} alt="" className="w-6 h-6 rounded" />
            )}
            <span>{currentWorkspace.name}</span>
          </div>
        );
      }}
    />
  );
}
```

`trigger` is its only prop, and the argument order is `(isLoading, currentWorkspace)`. The switcher lists workspaces, creates one where the org allows it, and in an invite-only app (`autoCreateFirst: false`) shows the user's pending invitations in its empty state. Hide parts with `ui.workspaceSwitcher` (`show`, `createButton`, `planBadge`, `memberCount`).

---

## Members, invitations and leaving

The `users` settings screen (`openWorkspaceSettings('users')`) already does all of this: invite by email, pending invitations with Resend and Revoke, roles, seat usage, and Remove behind a confirmation. Use the calls below only for a screen of your own.

- **`addUser(id, email, role)`** adds an **existing** account; it answers 404 when the address has none.
- **`inviteMember(id, email, role, { landingUrl? })`** reaches an address that may have no account yet. The person gets an email, follows the link into your app (your auth client's redirect URL, or `landingUrl`, which must be one of them), signs in or registers, and accepts. The SDK handles the invitee's side: it reads the link, offers sign-in, and accepts. An invitation lasts 14 days, a resend waits out a cooldown (`resendAvailableAt` on the row), and a pending invitation holds a seat until it is accepted, declined, revoked or expired.

```tsx
const { currentWorkspace, inviteMember } = useSaaSWorkspaces();
await inviteMember(currentWorkspace!._id, 'teammate@example.com', 'editor');
```

For the invitee's own list, use the components and hooks rather than raw calls:

```tsx
import { PendingInvitations, WhenPendingInvitations } from '@buildbase/sdk/react';

function NoWorkspaceScreen() {
  return (
    <WhenPendingInvitations fallbackComponent={<p>Ask your team for an invitation.</p>}>
      <PendingInvitations onAccepted={ws => console.log('joined', ws.name)} />
    </WhenPendingInvitations>
  );
}
```

`useMyInvitations()` is `{ invitations, loading, error, busy, refresh, accept, decline }` for the invitee, and `useWorkspaceInvitations(workspaceId)` is the admin's list with `resend` and `revoke`. Invitation errors carry `status` and a `code` (`INVITATION_ERROR_CODE`: `SEAT_LIMIT_REACHED` with `currentUserCount` and `limit`, `INVITATION_RATE_LIMITED` with `retryAfterSeconds`, `INVITATION_EMAIL_MISMATCH`, `EMAIL_NOT_VERIFIED`, `INVITATION_EXPIRED`, `INVITATION_ALREADY_HANDLED`). With `canInviteMembers` off, every invite surface hides and the server refuses with 403 `WORKSPACE_INVITES_DISABLED`. Invitations need SDK 0.0.71 or later and a server from release 22.

**Leaving.** `leaveWorkspace(id)` (since 1.0.0) removes the signed-in member. The creator cannot leave (409 `WORKSPACE_OWNER_CANNOT_LEAVE`; they delete instead), and a member who pays for the workspace's subscription is refused with 409 `PAYER_STILL_PAYS` until its billing moves or it is cancelled (`WORKSPACE_MEMBERSHIP_CODE`). The `danger` settings screen offers Leave to every member who did not create the workspace; `ui.settings.danger.leave: false` hides Leave alone.

---

## Roles and permissions

Every organization starts with three workspace roles, `admin`, `editor` and `viewer`, and you can add your own in the console (Users, then Settings under Workspaces). No member row is ever `owner`: the workspace's **owner** is the person who created it, told apart with `isOwner`, and only they may delete it. The creator's row starts as `admin`. Someone joining without a role gets the org's default role (`viewer` unless you pick another).

| Role | Default permissions |
|---|---|
| owner (the creator, not an assignable role) | Everything, including `workspace:delete` |
| `admin` | Every workspace permission except deleting the workspace |
| `editor` | View settings, members, features, billing and usage, and record usage |
| `viewer` | View settings and members |

Check permissions, not role names:

```tsx
import { Permission, usePermissions, WhenPermission, WhenWorkspaceRoles } from '@buildbase/sdk/react';

function Team() {
  const { can, isOwner } = usePermissions(); // the current workspace by default
  return (
    <>
      <WhenPermission permission={Permission.WORKSPACE_MEMBERS_INVITE}>
        <InviteForm />
      </WhenPermission>
      {can('app:reports:export') && <ExportButton />}
      {isOwner && <DeleteWorkspaceButton />}
      <WhenWorkspaceRoles roles={['admin']}>
        <AdminTools />
      </WhenWorkspaceRoles>
    </>
  );
}
```

- `usePermissions(workspace?)` returns `{ can, permissions, isOwner, role, appPermissionDefinitions }`; `can` takes one permission or an array (all must hold).
- `Permission` holds the platform's keys (`workspace:settings:view`, `workspace:members:invite`, `workspace:billing:manage`, `workspace:usage:record`, ...). Your own permissions are keys you define in the console (suggested form `app:<area>:<action>`) or pass through `defaultPermissions` on the provider; the `permissions` settings screen lets the workspace's creator override them per workspace.
- `WhenRoles` checks the user's **global** role; `WhenWorkspaceRoles` checks the role in the current workspace.
- Your backend asks the server instead of trusting the browser: `GET /api/v1/public/workspaces/{workspaceId}/permissions/me` answers `{ role, isOwner, permissions }`, and the server factory has `workspace.permissions(workspaceId)` and `workspace.can(workspaceId, key)` (see [server-side.md](./server-side.md)).

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
  entitlement?: IPlanEntitlement;             // what the workspace may do, composed by the server
}
```

`entitlement` is what `useEntitlement` and `useLimit` answer from (absent on older servers); see [billing.md](./billing.md). The behaviors `canCreateWorkspace`, `canInviteMembers`, `showSwitcher`, `maxWorkspacesPerUser` and `autoCreateFirst` are **not** fields on the workspace object - they are organization settings (`ISettings['workspace']`, read with `useSaaSSettings()`), configured in the BuildBase dashboard (see [Advanced Overrides](#workspace-settings-advanced-overrides)).

---

## User Attributes

Store arbitrary key-value data on a user:

```tsx
import { useUserAttributes } from '@buildbase/sdk/react';

function UserPreferences() {
  // 0.0.55 moved these to the { data, loading, error, refetch } convention.
  // `isLoading` still works but is deprecated, and it combines both pipelines.
  const { attributes, loading, error, refetch, updateAttribute, updateAttributes } =
    useUserAttributes();

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

Values are `string | number | boolean`; both updates resolve to the updated `IUser`.

---

## Workspace Modes

The mode is a preset chosen in the dashboard (Users, then Settings under Workspaces); no code change is needed.

**Personal Mode** (where a new organization starts): one workspace per user, created on first sign-in. No team invites, no switcher. In a consumer app you usually sell the plan to the person instead of the workspace.

**Platform Mode**: multi-user, multi-workspace, with the full settings UI. It needs a BuildBase plan that includes it. Switching to Personal is refused while anyone owns more than one workspace.

The SDK never reads the mode itself: it follows the settings the preset fills in, so changing one of them underneath the mode is what every surface follows.

---

## Workspace Settings: Advanced Overrides

Configured in the BuildBase dashboard (not in code), with **Advanced overrides** turned on:

| Setting | Options |
|---------|---------|
| Can Create Workspace | Everyone / Disabled (the first workspace made on sign-in is not affected) |
| Can Invite Members | Everyone / Admin Only / Disabled |
| Show Workspace Switcher | On / Off |
| Max Workspaces Per User | 0 (unlimited) to 100 |
| Auto-Create First Workspace | On / Off (off for an invite-only app) |

`ISettings['workspace']['canCreateWorkspace']` is a `boolean` since 0.0.85; the "Owner only" choice was removed. `canInviteMembers` is `boolean | 'admin-only'`. Roles, the default role, and the limits (max workspaces per person, max members per workspace) sit on the same page. In Personal mode the preset holds except for invitations for admins only.
