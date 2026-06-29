# Authentication

This is everything about logging users in and knowing who they are: starting sign-in, reading the logged-in user, protecting pages, and reacting to auth events. You'll reach for this the moment your app needs a "Sign In" button or needs to show different things to logged-in vs. logged-out users. If you just want the shortest working setup, do [quick-start.md](./quick-start.md) first — this doc is the deeper reference for what the SDK gives you afterward.

## Contents

- [How Buildbase Auth Works](#how-buildbase-auth-works) — the OAuth2 flow explained
- [The useSaaSAuth Hook](#the-usesaasauth-hook) — main hook for auth state
- [Conditional Auth Components](#conditional-auth-components) — gates for signed-in/out UI
- [Redirect Preservation](#redirect-preservation) — return to URL after login
- [Custom loading screen during auth](#custom-loading-screen-during-auth-loadingcomponent) — branded full-screen loader
- [Workspace Settings Sections](#workspace-settings-sections) — open built-in settings dialog
- [Auth Callbacks Reference](#auth-callbacks-reference) — provider callback functions
- [onWorkspaceChange vs handleEvent](#onworkspacechange-vs-handleevent) — before vs after switch
- [Available Event Types](#available-event-types) — SDK event names
- [User Object Shape](#user-object-shape) — AuthUser fields
- [Security Notes](#security-notes) — cookie, secret, storage safety

## How Buildbase Auth Works

Buildbase uses OAuth2 — an industry-standard login handshake where your app never sees the user's password; it gets a one-time **code** it trades for proof of login. When a user clicks "Sign In":

1. The SDK redirects to the Buildbase-hosted login page
2. The user authenticates (Google, magic link, etc. — configured in the dashboard)
3. Buildbase redirects back to your `redirectUrl` with `?code=...` in the URL — a one-time code proving the user just logged in
4. The SDK reads that `?code=` from the URL **automatically** when the provider mounts, then calls your `handleAuthentication(code)` callback (a function you supply that the SDK calls at the right moment). Because of this, your `redirectUrl` must point at a page the provider wraps; the docs use `/callback`.
5. Your callback POSTs the code to your `/api/auth/token` endpoint
6. Your endpoint exchanges the code with Buildbase for a **`sessionId`** — Buildbase's token that says "this user is logged in"
7. Your endpoint stores `sessionId` in an httpOnly cookie (a cookie your browser JavaScript can't read, so injected scripts can't steal it)
8. Your callback returns `{ sessionId }` to the SDK
9. The SDK uses `sessionId` for all subsequent API calls

On page refresh:
1. The SDK calls your `getSession()` callback
2. Your callback hits `/api/auth/session` which reads the httpOnly cookie
3. Returns `sessionId` or `null`

> Full file-by-file wiring of the `/api/auth/*` routes and the provider lives in [quick-start.md](./quick-start.md).

---

## The useSaaSAuth Hook

A hook is a React function you call inside a component to tap into shared state — here, the current auth state. `useSaaSAuth` is the main one for everything login-related.

```tsx
import { useSaaSAuth } from '@buildbase/sdk/react';
import { AuthStatus } from '@buildbase/sdk';

function AuthExample() {
  const {
    user,              // Current user object (undefined if not authenticated)
    session,           // Full session with sessionId
    isAuthenticated,   // true if authenticated
    isLoading,         // true during session restore on mount
    isRedirecting,     // true during OAuth redirect
    status,            // AuthStatus enum: 'loading' | 'redirecting' | 'authenticating' | 'authenticated' | 'unauthenticated'
    signIn,            // () => void — starts OAuth flow. Optionally pass returnUrl
    signOut,           // () => void — calls onSignOut callback
    openWorkspaceSettings,  // (section) => void — opens settings dialog
  } = useSaaSAuth();

  // Type-safe status checks (preferred over boolean flags for complex logic)
  if (status === AuthStatus.loading) return <Spinner />;
  if (status === AuthStatus.unauthenticated) return <LoginButton onClick={signIn} />;

  return <Dashboard user={user} />;
}
```

---

## Conditional Auth Components

These are **gates** — components that render their children only when a condition is true (and render nothing, or a fallback, otherwise). Note they have a third, easy-to-miss "still loading" state; see the gates section in [quick-start.md](./quick-start.md).

```tsx
import { WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';

// Declarative — preferred for route-level protection
function App() {
  return (
    <>
      <WhenUnauthenticated>
        <LoginPage />
      </WhenUnauthenticated>
      <WhenAuthenticated>
        <Dashboard />
      </WhenAuthenticated>
    </>
  );
}
```

---

## Redirect Preservation

When `signIn()` is called, the SDK saves the current URL to localStorage (10-minute TTL). After login, the user is redirected back to that URL.

```tsx
// Custom redirect after login
signIn('https://app.com/dashboard?action=selectPlan');
```

---

## Custom loading screen during auth (`loadingComponent`)

While the SDK is initializing auth (and exchanging the login `?code=`), `SaaSOSProvider` shows a full-screen loader. Replace it with your own branding via the provider's `loadingComponent` prop. It accepts **either** a static `ReactNode` **or** a render function that receives `{ message: string }` — a human-readable, locale-aware status string the SDK updates as it works (e.g. "Signing you in…").

```tsx
// Static — simplest
<SaaSOSProvider loadingComponent={<MyBrandedSpinner />} ...>

// Render function — show the SDK's live status message
<SaaSOSProvider
  loadingComponent={({ message }) => (
    <div className="splash">
      <Logo />
      <p>{message}</p>
    </div>
  )}
  ...
>
```

> This provider-level `loadingComponent` is the full-screen auth overlay. It's separate from the subscription gates' `loadingComponent`, which only covers that one gate's loading state and takes a `ReactNode`. (Note: the `WhenAuthenticated` / `WhenUnauthenticated` auth gates do **not** accept a `loadingComponent` — they take only `children` and render nothing while loading.)

---

## Workspace Settings Sections

Open specific sections of the built-in workspace settings dialog:

```tsx
const { openWorkspaceSettings } = useSaaSAuth();

openWorkspaceSettings('profile');       // Account profile
openWorkspaceSettings('general');       // Workspace name, icon
openWorkspaceSettings('users');         // Workspace members
openWorkspaceSettings('subscription');  // Plan & Billing
openWorkspaceSettings('usage');         // Quota usage dashboard
openWorkspaceSettings('features');      // Feature toggles
openWorkspaceSettings('danger');        // Delete workspace (owner only)
```

---

## Auth Callbacks Reference

Callbacks are functions you pass to the provider that the SDK calls at specific moments (restoring a session, exchanging a code, signing out). You write what happens; the SDK decides when.

```ts
callbacks: {
  // Required: restore session on page refresh
  getSession: () => Promise<string | null>;
  
  // Required: exchange OAuth code for sessionId
  handleAuthentication: (code: string) => Promise<{ sessionId: string }>;
  
  // Required: clear session on sign out
  onSignOut: () => Promise<void>;
  
  // Optional: handle expired/invalid sessions
  onSessionExpired?: (reason: 'missing' | 'expired' | 'invalid') => void;
  
  // Optional: listen to SDK events (workspace:changed, user:created, etc.)
  handleEvent?: (eventType: EventType, data: EventData) => void | Promise<void>;
  
  // Optional: prep before workspace switch (generate tokens, etc.)
  onWorkspaceChange?: (params: { workspace, user, role }) => Promise<void>;
}
```

---

## onWorkspaceChange vs handleEvent

A **workspace** is one tenant (a team/company, or a single user in Personal Mode) — see [workspace.md](./workspace.md). A **role** is that user's permission level *within* a workspace (owner, admin, member). These two callbacks fire around a workspace switch but serve different purposes:

| Callback | When called | Use for |
|----------|------------|---------|
| `onWorkspaceChange` | BEFORE workspace switch completes | Token generation, data prep that must happen before new workspace loads |
| `handleEvent('workspace:changed')` | AFTER workspace switch completes | Notifications, analytics, updating app state |

```tsx
// onWorkspaceChange: generate a workspace-scoped JWT before the switch
onWorkspaceChange: async ({ workspace, user, role }) => {
  const token = await generateWorkspaceToken(user.id, workspace._id, role);
  localStorage.setItem('auth_token', token);
},

// handleEvent: update analytics after switch
handleEvent: async (type, data) => {
  if (type === 'workspace:changed') {
    analytics.track('workspace_switched', { workspaceId: data.workspace._id });
  }
}
```

---

## Available Event Types

```ts
'user:created'
'user:updated'
'workspace:changed'         // After switch completes
'workspace:created'
'workspace:updated'
'workspace:deleted'
'workspace:user-added'
'workspace:user-removed'
'workspace:user-role-changed'
```

---

## User Object Shape

```ts
interface AuthUser {
  id: string;
  name: string;
  org: string;
  email: string;
  emailVerified: boolean;
  clientId: string;
  role: string;      // Global role (not workspace role)
  image?: string;
}
```

---

## Security Notes

- `sessionId` is stored in an httpOnly cookie — not accessible to JavaScript (XSS-safe)
- `clientSecret` is used only server-side — never expose in client code or `NEXT_PUBLIC_` vars
- The SDK stores no auth data in localStorage — only the redirect URL preservation
- Session lifetime is controlled by your server's cookie `maxAge`
