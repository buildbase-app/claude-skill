# Authentication

This is everything about logging users in and knowing who they are: starting sign-in, reading the logged-in user, protecting pages, keeping a session through an outage, and reacting to auth events. You'll reach for this the moment your app needs a "Sign In" button or needs to show different things to logged-in vs. logged-out users. If you just want the shortest working setup, do [quick-start.md](./quick-start.md) first - this doc is the deeper reference for what the SDK gives you afterward. Verified against `@buildbase/sdk` 1.8.0.

## Contents

- [How BuildBase Auth Works](#how-buildbase-auth-works) - the OAuth2 flow explained
- [The useSaaSAuth Hook](#the-usesaasauth-hook) - main hook for auth state
- [Restoring a session, outages and expiry](#restoring-a-session-outages-and-expiry) - `isSessionUnverified`, `onSessionExpired`
- [Conditional Auth Components](#conditional-auth-components) - gates for signed-in/out UI
- [Redirect Preservation](#redirect-preservation) - return to URL after login
- [The full-screen loader](#the-full-screen-loader-loadingcomponent-and-fullscreenloader) - `loadingComponent`, `fullScreenLoader`
- [Confirming it's you](#confirming-its-you) - `reauth_required` and `requireReverification`
- [Access refusals and ended sessions](#access-refusals-and-ended-sessions) - a company's rules, kept sessions
- [Workspace Settings Sections](#workspace-settings-sections) - open built-in settings dialog
- [Auth Callbacks Reference](#auth-callbacks-reference) - provider callback functions
- [onWorkspaceChange vs handleEvent](#onworkspacechange-vs-handleevent) - before vs after switch
- [Available Event Types](#available-event-types) - SDK event names
- [User and Session Shape](#user-and-session-shape) - `user` and `session` fields
- [Account security screens](#account-security-screens) - passkeys, two-step, phone, connected accounts, guests
- [Devices, sessions and connected agents](#devices-sessions-and-connected-agents) - self-service screens and hooks
- [Enterprise single sign-on](#enterprise-single-sign-on) - SAML, OIDC and SCIM through your own WorkOS account
- [Development and staging environments](#development-and-staging-environments) - the `environment` prop
- [Security Notes](#security-notes) - cookie, secret, storage safety

## How BuildBase Auth Works

BuildBase uses OAuth2 - an industry-standard login handshake where your app never sees the user's password; it gets a one-time **code** it trades for proof of login. When a user clicks "Sign In":

1. The SDK redirects to the BuildBase-hosted login page (in the provider's `locale`, or the `locale` you set in `auth`)
2. The user authenticates (Google, magic link, passkey, enterprise SSO, etc. - configured in the dashboard)
3. BuildBase redirects back to your `redirectUrl` with `?code=...` in the URL - a one-time code proving the user just logged in
4. The SDK reads that `?code=` from the URL **automatically** when the provider mounts, then calls your `handleAuthentication(code)` callback (a function you supply that the SDK calls at the right moment). Because of this, your `redirectUrl` must point at a page the provider wraps; the docs use `/callback`.
5. Your callback POSTs the code to your `/api/auth/token` endpoint
6. Your endpoint exchanges the code with BuildBase for a **`sessionId`** - BuildBase's token that says "this user is logged in"
7. Your endpoint stores `sessionId` in an httpOnly cookie (a cookie your browser JavaScript can't read)
8. Your callback returns `{ sessionId }` to the SDK
9. The SDK uses `sessionId` for all subsequent API calls

On page refresh:
1. The SDK calls your `getSession()` callback
2. Your callback hits `/api/auth/session` which reads the httpOnly cookie
3. Returns `sessionId` or `null`
4. The SDK checks the session against the profile (`GET /api/v1/public/profile`). Your app renders meanwhile, with `isLoading` true

> Full file-by-file wiring of the `/api/auth/*` routes and the provider lives in [quick-start.md](./quick-start.md). Outside Next.js (TanStack Start, Workers, Hono, a Vite app's serverless functions), `createAuthHandler(options)` from `@buildbase/sdk` is the three routes (`POST /api/auth/token`, `GET /api/auth/session`, `POST /api/auth/signout`) as one `Request -> Response` handler with the `bb-session-id` cookie, and `exchangeAuthCode({ code, orgId, clientId, clientSecret, environment?, serverUrl? })` is the code exchange on its own. Both are server-side only. The token and sign-out POSTs must send `Content-Type: application/json`; a hand-written route calls `refuseCrossSiteAuthPost(request)` first (login CSRF).

---

## The useSaaSAuth Hook

A hook is a React function you call inside a component to tap into shared state - here, the current auth state. `useSaaSAuth` is the main one for everything login-related.

```tsx
import { AuthStatus, useSaaSAuth } from '@buildbase/sdk/react';

function AuthExample() {
  const {
    user,                  // Current user (undefined if not authenticated)
    session,               // Full session with sessionId, or null
    isAuthenticated,       // true if authenticated
    isLoading,             // true while the session is restored or checked on page load
    isRedirecting,         // true during OAuth redirect
    isSessionUnverified,   // true while a stored session is kept but the server could not confirm it
    status,                // AuthStatus: 'loading' | 'redirecting' | 'authenticating' | 'authenticated' | 'unauthenticated'
    signIn,                // (returnUrl?, { notice? }?) => Promise<void> - starts the OAuth flow
    signOut,               // (options?) => Promise<void> - ends the session, then onSignOut
    requireReverification, // (options?) => Promise<'recent' | 'redirecting'> - "confirm it's you" after reauth_required
    openWorkspaceSettings, // (section?) => void - opens the settings dialog
    openPlanPicker,        // () => void - opens plan selection
    openCreditStore,       // () => void - opens credit purchase
    openAccountBilling,    // (params?) => void - the person's own Billing screen
  } = useSaaSAuth();

  // Type-safe status checks (preferred over boolean flags for complex logic)
  if (isSessionUnverified) return <p>Can't reach the server. Retrying...</p>;
  if (status === AuthStatus.loading) return <Spinner />;
  if (status === AuthStatus.unauthenticated) return <button onClick={() => signIn()}>Sign in</button>;

  return <Dashboard user={user} />;
}
```

Call `signIn()` from an arrow function: its first argument is a return URL string, so `onClick={signIn}` would hand it the click event. `onClick={signOut}` is fine; `signOut` ignores an event.

`AuthStatus` and the other core enums are exported from both `@buildbase/sdk` and `@buildbase/sdk/react`. In a server layout (a file without `'use client'`), import enums from `@buildbase/sdk`, because `/react` is a `"use client"` boundary.

---

### Signing out actually ends the session (SDK 0.0.70)

Before 0.0.70, `signOut()` cleared the session id locally and reset client state, and stopped there - the session stayed valid on the server until it expired. It now revokes the session server-side as well.

```tsx
const { signOut } = useSaaSAuth();

await signOut();                      // ends this session
await signOut({ everywhere: true });  // ends every session, on every device
```

`signOut()` alone still ends only the current session. Signing out one *other* session is `SessionsApi.revoke`, covered in the devices and sessions section below. If the developer is on an older SDK, say so rather than promising server-side revocation.

---

## Restoring a session, outages and expiry

Since 1.0.0 a platform outage no longer signs your users out. On page load the provider checks the stored session against the profile, and only the server refusing it ends it:

| What the profile check gets | What happens |
|---|---|
| 200 | Signed in: `status` becomes `authenticated` |
| 401, 403, or 404 (a user that no longer exists) | The session ends and `onSessionExpired('expired')` is called |
| A company's access refusal (403 `ip_not_allowed` or `tenant_restricted`, 400 `tenant_header_invalid`) | The session is **kept**; see [Access refusals](#access-refusals-and-ended-sessions) |
| No answer, a timeout (8 s on the first try), a 5xx, a 429 | The session is **kept**: `status` stays `loading`, `isSessionUnverified` is `true`, `onSessionExpired` is not called, and the SDK retries with backoff (about 2 s doubling to 30 s) and when the browser fires `online`. When the server answers, the user is signed in without a reload |

Rules that follow from this:

- Do not treat `!isAuthenticated` while `isLoading` as signed out, and do not sign users out yourself on `isSessionUnverified`. Show a "can't reach the server" state instead of a sign-in prompt.
- `onSessionExpired` fires with `'missing'` when `getSession()` returns null, and with `'expired'` when the server refuses the session, on page load or on a 401 from any later call.
- A 401 sign-out (an expired session, or a company ending it) resets the current workspace and the workspace list and closes the settings dialog, as `signOut()` does (1.8.0). The same person signing in again lands on their first workspace.
- `useSaaSWorkspaces().loading` stays true while the session is still being read or is unverified, so "no `currentWorkspace`" is not "no workspace" yet. See [workspace.md](./workspace.md).

---

## Conditional Auth Components

These are **gates** - components that render their children only when a condition is true (and render nothing, or a fallback, otherwise). Note they have a third, easy-to-miss "still loading" state; see the gates section in [quick-start.md](./quick-start.md).

```tsx
import { WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';

// Declarative - preferred for route-level protection
function App() {
  return (
    <>
      <WhenUnauthenticated>
        <LoginPage />
      </WhenUnauthenticated>
      <WhenAuthenticated loadingComponent={<Skeleton />}>
        <Dashboard />
      </WhenAuthenticated>
    </>
  );
}
```

Both take `loadingComponent` and `fallbackComponent` (each defaults to `null`), matching the subscription, quota and credit gates. Without a `loadingComponent`, nothing renders during the loading, redirecting and authenticating states, which now includes the whole page-load session check, since the provider no longer covers the page while it runs.

---

## Redirect Preservation

When `signIn()` is called, the SDK saves the current URL to localStorage (10-minute TTL, checked with `validateRedirectUrl()`). After login, the user is redirected back to that URL.

```tsx
// Custom redirect after login
signIn('https://app.com/dashboard?bb=action:selectPlan,plan:abc');

// Tell the hosted sign-in page why the person signs in again (SignInOptions)
signIn(undefined, { notice: { reason: 'enterprise_workspace' } });
```

`notice` defaults to the last `session_ended` reason the page heard, so after a company ends a session the hosted page says why. A server that does not take it signs in without it.

---

## The full-screen loader (`loadingComponent` and `fullScreenLoader`)

Since 1.0.0 the provider renders your app straight away while it restores a session on page load; gate on `useSaaSAuth().isLoading` (or `WhenAuthenticated` / `WhenUnauthenticated`). Its full-screen overlay is shown only while the page is mid sign-in (`?code=` in the URL, back from the hosted page) and while the SDK sends the user to the hosted sign-in or re-confirmation page.

Replace the overlay's content with your own branding via the provider's `loadingComponent` prop. It accepts **either** a static `ReactNode` **or** a render function that receives `{ message: string }` - a human-readable, locale-aware status string the SDK updates as it works (e.g. "Signing you in...").

```tsx
// Static - simplest
<SaaSOSProvider loadingComponent={<MyBrandedSpinner />} ...>

// Render function - show the SDK's live status message
<SaaSOSProvider
  loadingComponent={({ message }) => (
    <div className="splash">
      <Logo />
      <p>{message}</p>
    </div>
  )}
  ...
>

// Never cover the app; it gates on isLoading itself
<SaaSOSProvider fullScreenLoader={false} ...>
```

`useFullScreenLoader()` returns `{ show(message), hide(), visible, message }` for your own long actions; `show()` does nothing while `fullScreenLoader` is `false`.

> This provider-level `loadingComponent` is the full-screen overlay. It's separate from the gates' `loadingComponent`, which only covers that one gate's loading state and takes a `ReactNode`.

---

## Confirming it's you

A change that needs a recent sign-in (deleting the account, removing a connected account or the phone, or a company's settings) is refused with 403 `reauth_required`. It **never** signs anyone out. The SDK's own screens ask for it themselves and keep the unsent change. For your own screens:

```tsx
import { isReauthRequired, useSaaSAuth } from '@buildbase/sdk/react';

function DangerousButton({ run }: { run: () => Promise<void> }) {
  const { requireReverification } = useSaaSAuth();
  return (
    <button
      onClick={async () => {
        try {
          await run();
        } catch (error) {
          // They come back to this page with the same session, now recent.
          if (isReauthRequired(error) && error.reverifiable !== false)
            await requireReverification({ factors: error.factors });
          else throw error;
        }
      }}
    >
      Save
    </button>
  );
}
```

`requireReverification({ returnUrl?, factors?, maxAgeSeconds?, workspaceId?, methods?, purpose? })` sends the browser to the hosted sign-in page and back with the same session. With `maxAgeSeconds` it resolves `'recent'` without leaving when the session already is. `await consumeReverified()` says once that the person just came back confirmed. It rejects with `reverify_unavailable` for a session nobody signed in to (one your team opened as the person, an agent's): sign out and in again there. `auth.callbacks.onReauthRequired(refusal)` on the provider, or `onReauthRequired(listener)` outside React, hears every refusal first.

For custom screens on the headless enterprise hooks, `useStepUp(scope, { workspaceId?, purpose?, methods? })` and `<ConfirmItsYou stepUp={...} />` keep the draft across the round trip.

---

## Access refusals and ended sessions

Three kinds of refusal come from a person's company (enterprise single sign-on customers) rather than from the session itself. The first two keep the session; the third ends it and the SDK signs out for you. Never sign out yourself on any of them.

| Refusal | What it is | Read it with |
|---|---|---|
| 403 `ip_not_allowed`, 403 `tenant_restricted`, 400 `tenant_header_invalid` | The company's access policy or network refuses this network. The session is kept and works elsewhere | `useAccessRefused()` (`{ refusal, dismiss }`), `auth.callbacks.onAccessRefused`, `isAccessRefused(error)` |
| 403 `workspace_access_refused` | The company's stricter rules for one of its workspaces. The session works in every other workspace | `useWorkspaceAccess(workspaceId?)` (`{ refusal, action, working, problem, confirm, signInAgain, dismiss }`) or `<WorkspaceAccessRefused />`, which the settings dialog already shows |
| 401 `session_ended` | The company ended the session (idle, too long, signed out by an admin). The SDK signs out as for any expiry | `useSessionEnded()` (`{ ended, dismiss }`), `auth.callbacks.onSessionEnded`, `sessionEndedCopy(ended, locale)` for the reader's language |

```tsx
import { useAccessRefused, useSessionEnded } from '@buildbase/sdk/react';

function AppChrome({ children }: { children: React.ReactNode }) {
  const { refusal } = useAccessRefused();
  const { ended, dismiss } = useSessionEnded();
  return (
    <>
      {refusal && <div role="alert">{refusal.message}</div>}
      {ended && (
        <p role="status">
          {ended.message} <button onClick={dismiss}>OK</button>
        </p>
      )}
      {children}
    </>
  );
}
```

The SDK's data hooks leave a read refused by `workspace_access_refused` with `error: null` and no data, so a page of your own on those hooks reads `useWorkspaceAccess(workspaceId).refusal` beside them, or renders `<WorkspaceAccessRefused />`.

---

## Workspace Settings Sections

Open specific sections of the built-in settings dialog. The full list of 18 sections, and when each one shows, is in [pre-built-ui.md](./pre-built-ui.md).

```tsx
const { openWorkspaceSettings } = useSaaSAuth();

openWorkspaceSettings();                    // the default, Profile
openWorkspaceSettings('security');          // Password, phone, two-step, connected accounts, passkeys, delete account
openWorkspaceSettings('devices');           // Devices and active sessions
openWorkspaceSettings('general');           // Workspace name, icon
openWorkspaceSettings('users');             // Members and invitations
openWorkspaceSettings('subscription');      // Plan & Billing
openWorkspaceSettings('usage');             // Quota usage dashboard
openWorkspaceSettings('features');          // Feature toggles
openWorkspaceSettings('connected-agents');  // Connected AI agents
openWorkspaceSettings('enterprise');        // Single sign-on, when the org offers it
openWorkspaceSettings('danger');            // Delete (owner) or leave (other members)
```

Since 1.0.0 a person in no workspace can still open their own sections: `openWorkspaceSettings()` opens the dialog on Profile, and `openAccountBilling()` on their own Billing, once the workspace list has answered, instead of reporting "No current workspace". An app that wants its own "create a workspace first" prompt checks `currentWorkspace` before calling.

---

## Auth Callbacks Reference

Callbacks are functions you pass to the provider that the SDK calls at specific moments (restoring a session, exchanging a code, signing out). You write what happens; the SDK decides when.

```ts
auth: {
  clientId: string;
  redirectUrl: string;
  locale?: string;   // the hosted sign-in page's language; defaults to the provider's locale
  callbacks: {
    // Required: restore session on page refresh
    getSession: () => Promise<string | null>;

    // Required: exchange OAuth code for sessionId
    handleAuthentication: (code: string) => Promise<{ sessionId: string }>;

    // Required: clear session on sign out
    onSignOut: () => Promise<void>;

    // Optional: the session is missing or the server refused it
    // (never when the server just could not be reached)
    onSessionExpired?: (reason: 'missing' | 'expired' | 'invalid') => void;

    // Optional: the person's company ended the session (401 session_ended);
    // called before onSessionExpired('expired'), which still follows
    onSessionEnded?: (ended: SessionEnded) => void;

    // Optional: the person's company refused this network or one of its
    // workspaces; the session is kept
    onAccessRefused?: (refusal: AccessRefusal) => void;

    // Optional: a change was refused with 403 reauth_required; for your own prompt
    onReauthRequired?: (refusal: ReauthRequired) => void;

    // Optional: listen to SDK events (workspace:changed, user:created, etc.)
    handleEvent?: (eventType: EventType, data: EventData) => void | Promise<void>;

    // Optional: prep before workspace switch; reject to abort the switch
    onWorkspaceChange?: (params: OnWorkspaceChangeParams) => Promise<void>;
  };
}
```

---

## onWorkspaceChange vs handleEvent

A **workspace** is one tenant (a team/company, or a single user in Personal Mode) - see [workspace.md](./workspace.md). A **role** is that user's permission level *within* a workspace: `admin`, `editor`, `viewer` or a role you add. No member row is ever `owner`; the workspace's creator is told apart by `usePermissions().isOwner`. These two callbacks fire around a workspace switch but serve different purposes:

| Callback | When called | Use for |
|----------|------------|---------|
| `onWorkspaceChange` | BEFORE workspace switch completes (also when restoring the workspace on page load) | Token generation, data prep that must happen before new workspace loads |
| `handleEvent('workspace:changed')` | AFTER workspace switch completes | Notifications, analytics, updating app state |

```tsx
// onWorkspaceChange: generate a workspace-scoped JWT before the switch
onWorkspaceChange: async ({ workspace, user, role }) => {
  const token = await generateWorkspaceToken(user?.id, workspace._id, role);
  localStorage.setItem('auth_token', token);
},

// handleEvent: update analytics after switch
// (import type { WorkspaceChangedEventData } from '@buildbase/sdk/react')
handleEvent: async (type, data) => {
  if (type === 'workspace:changed') {
    const { workspace } = data as WorkspaceChangedEventData; // EventData is a union
    analytics.track('workspace_switched', { workspaceId: workspace._id });
  }
}
```

`user` and `role` in `OnWorkspaceChangeParams` are nullable (`AuthUser | null`, `string | null`).

---

## Available Event Types

`SDKEvent` holds these; each has its own payload type (`WorkspaceChangedEventData`, `WorkspaceUserAddedEventData`, ...).

```ts
'user:created'
'user:updated'
'workspace:changed'                 // After switch completes
'workspace:created'
'workspace:updated'
'workspace:deleted'
'workspace:user-added'
'workspace:user-removed'
'workspace:user-role-changed'
'workspace:invitation-sent'
'workspace:invitation-accepted'
'workspace:invitation-declined'
'workspace:invitation-revoked'
```

These are in-browser SDK events. Server-side webhooks are a different catalog: see [../http-api/webhooks.md](../http-api/webhooks.md).

---

## User and Session Shape

`useSaaSAuth().user` (the type is not exported by name; use `NonNullable<ReturnType<typeof useSaaSAuth>['user']>` if you need it):

```ts
{
  id: string;
  name: string;
  org: string;
  email: string;            // empty for a guest
  emailVerified: boolean;
  clientId: string;
  role: string;             // Global role (not workspace role)
  image?: string;
  createdAt?: string;
  firstAuthAt?: string;     // first completed authentication, for telling a sign-up from a login
  mfaEnabled: boolean;      // has a second step (authenticator app or text message codes)
  canChangeEmail: boolean;
  externalId?: string;      // id in the system the user was imported from
  phone?: string;           // E.164
  phoneVerified?: boolean;
  username?: string;
  claims: Record<string, unknown>;  // custom claims the app owner set; {} when none
  isAnonymous: boolean;     // a guest; see useGuestUpgrade
  deleteAfter?: string;     // a scheduled account deletion
}
```

`useSaaSAuth().session` is `{ user, sessionId, expires }` plus, from servers that record them, `signInMethod` (`password`, `magic_link`, `passkey`, `social`, `sso`, `app_team`, `unknown`), `authTime`, `amr`, `reverifiable` and `impersonation` (present while an app owner views the app as this person; the provider pins `<ImpersonationBanner />` for as long as it lasts).

The domain types `IUser`, `IUserProfile`, `IWorkspace` and `ISettings` are exported from both entries. `getProfile()` and `updateUserProfile()` resolve to `IUserProfile`: read `profile.id`, since `_id` is deprecated there and undefined at runtime.

---

## Account security screens

The settings dialog's account sections already cover the person's own sign-in. Prefer them to hand-built screens:

- **`security`**: change password, phone number and text message codes, two-step sign-in (authenticator app, or text message where the app allows it), connected social accounts and Ethereum or Solana wallets, passkeys (rename and remove), and Delete account with a grace period. Each part can be hidden through `ui.settings.security` (`password`, `phone`, `twoStep`, `connectedAccounts`, `wallets`, `deleteAccount`, `passkeyRename`, `passkeyDelete`).
- **`profile`**: name, email (with change of email where the server allows it), username where the app has usernames on, language, country, currency, timezone.
- **Guests**: a guest (`useSaaSAuth().user.isAnonymous`) becomes a real account, keeping their id, data and session, with `<GuestUpgrade />` or `useGuestUpgrade()`.

For your own UI the same calls are on `WorkspaceApi` (`getConnectedAccounts`, `linkAccount`, `completeAccountLink`, `addPhone`, `confirmPhone`, `getMfaStatus`, `renamePasskey`, `deletePasskey`, `requestAccountDeletion`, `setUsername`, ...). Refusals carry the server's sentence and a `code`; the SDK package's `docs/ERROR_CODES.md` lists them.

---

## Devices, sessions and connected agents

Three self-service surfaces the SDK ships, all session-authed and scoped to the signed-in user.

```tsx
import { useConnectedAgents, useDevices, useSessions } from '@buildbase/sdk/react';

const { devices, maxDevices, loading, error, busyId, refresh, rename, signOut, forget } = useDevices();
const { sessions, revoking, refresh: refreshSessions, revoke } = useSessions();
const { agents, revoking: revokingAgent, refresh: refreshAgents, revoke: revokeAgent } = useConnectedAgents();
```

Ready-made `<Devices />`, `<Sessions />` and `<ConnectedAgents />` components exist too, and the settings dialog already includes them (`devices` holds devices and sessions; `connected-agents`). The Devices screen offers no Sign out or Remove on the device you are using: both would end the app's own session too, so that row keeps Rename, and signing out there is the app's own sign-out. Server-side the same actions are `bb.devices.list/rename/signOut/forget` and `bb.sessions.list/revoke`.

Device identity is server-issued as of 0.0.57 and entirely transparent: after login the SDK fetches a server-signed device token and echoes it as `x-device-id`, so "this device", per-device sign-out and new-device alerts are anchored to an id the client cannot forge. It is best-effort and never blocks login, and your `handleAuthentication` still returns only `{ sessionId }`.

---

## Enterprise single sign-on

Enterprise single sign-on (SAML and OIDC) and Directory Sync (SCIM) work through the app owner's own WorkOS account. You set it up in the BuildBase console (Users, Authentication, Enterprise): your WorkOS keys, an enterprise per customer, their verified domains, and the workspaces each enterprise is bound to. There is nothing to configure in code: an SSO sign-in comes back through the same hosted page, `?code=` and `handleAuthentication`.

On the app side, since 1.0.0:

- The settings section `enterprise` (`<EnterpriseAccess />` on its own) shows while `enterpriseSsoAvailable(settings)` is true: whether the workspace's company connection works, **Set up SSO** for the company's IT admin, directory sync and certificate cards, and the company's own admin screens.
- The company screens and hooks (`useEnterprise`, `useEnterprisePolicy`, `useEnterpriseGroups`, ... and `EnterpriseApi`) are listed in the SDK package's `agents/react.md`. Their changes may answer `reauth_required`, handled by [Confirming it's you](#confirming-its-you).

---

## Development and staging environments

`environment` on `SaaSOSProvider` (and `BuildBaseProvider`, its brand-aligned alias with the same props) is a development or staging environment's key from the console: eight lowercase letters. The SDK then sends `<orgId>-<key>` wherever it sent `orgId`, and keeps that environment's browser session, device and current workspace apart. Unset (or `'production'`) is production. It is never inferred from `NODE_ENV`, so a preview deployment is production unless you set it.

```tsx
<SaaSOSProvider
  serverUrl={process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!}
  version={ApiVersion.V1}
  orgId={process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!}
  environment={process.env.NEXT_PUBLIC_BUILDBASE_ENVIRONMENT}
  auth={{ clientId, redirectUrl, callbacks }}
>
```

Your token route passes the same key to `exchangeAuthCode({ ..., environment })` (or uses `environmentId(orgId, environment)` when it calls the HTTP API itself).

---

## Security Notes

- `sessionId` is stored by your server in an httpOnly cookie, which `getSession()` reads to restore the session on refresh
- The SDK also keeps a copy of the session id in `localStorage` for its own API calls (sent as `x-session-id`) and clears it on sign-out; user data lives in memory (React context). Ordinary XSS hygiene still matters
- `clientSecret` is used only server-side - never expose it in client code or `NEXT_PUBLIC_` vars
- Session lifetime is controlled by your server's cookie `maxAge` and by the platform; a company can also end sessions (`session_ended`)
