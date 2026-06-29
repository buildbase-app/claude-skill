# Common Errors and Fixes

## Contents

- [Configuration Errors](#configuration-errors) — orgId, serverUrl, version issues
- [Authentication Errors](#authentication-errors) — session, cookie, callback problems
- [Workspace / Gate Issues](#workspace--gate-issues) — gates and feature flags not rendering
- [Styling Issues](#styling-issues) — missing CSS import
- [TypeScript Errors](#typescript-errors) — missing types and exports
- [Performance Issues](#performance-issues) — excessive re-renders

## Configuration Errors

### "Invalid orgId: '...' Must be a valid MongoDB ObjectId"

**Cause**: The `orgId` must be exactly 24 hexadecimal characters.

```tsx
// ❌ Wrong
orgId="my-org"
orgId="123"

// ✅ Correct
orgId="507f1f77bcf86cd799439011"  // 24 hex characters
```

**Where to find it**: Buildbase dashboard → Settings → General → Organization ID

---

### "Invalid serverUrl: '...' Must be a valid URL"

**Cause**: The `serverUrl` must include the protocol.

```tsx
// ❌ Wrong
serverUrl="api.console.buildbase.app"
serverUrl="buildbase.app"

// ✅ Correct (this is the fixed hosted value)
serverUrl="https://api.console.buildbase.app"
// ✅ Or your own origin if self-hosting
serverUrl="http://localhost:3001"
```

---

### "Invalid version: '...'. Only 'v1' is currently supported"

```tsx
// ❌ Wrong
version="v2"
version={2}

// ✅ Correct
import { ApiVersion } from '@buildbase/sdk';
version={ApiVersion.V1}
// or
version="v1"
```

---

## Authentication Errors

### "BuildBase: getSessionId callback is required for authenticated calls"

**Cause**: You're using an exported action (e.g., `workspace.list()`) without providing `getSessionId` in `BuildBase()` config, and without calling `withSession()`.

```ts
// ❌ Wrong — no getSessionId, calling authenticated method directly
const bb = BuildBase({ serverUrl, orgId });
await bb.workspace.list(); // throws

// ✅ Option 1 — provide getSessionId (Next.js)
const bb = BuildBase({ serverUrl, orgId, getSessionId: async () => ... });
await bb.workspace.list();

// ✅ Option 2 — use withSession() (Express/background jobs)
const { workspace } = bb.withSession(sessionId);
await workspace.list();
```

---

### User can sign in but session doesn't persist on refresh

**Cause**: The `handleAuthentication` callback doesn't properly set the httpOnly cookie, or `getSession` isn't reading it correctly.

**Debug steps**:
1. Check that `/api/auth/token` sets the cookie with `httpOnly: true`
2. Check that `/api/auth/session` reads from the same cookie name
3. Verify the `SESSION_COOKIE_NAME` constant is the same in both files
4. In browser DevTools → Application → Cookies — look for `bb-session-id`

```ts
// Ensure cookie name is consistent
export const SESSION_COOKIE_NAME = 'bb-session-id';

// In /api/auth/token — set it
response.cookies.set(SESSION_COOKIE_NAME, sessionId, { httpOnly: true, ... });

// In /api/auth/session — read it
const sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value ?? null;
```

---

### handleAuthentication returns undefined sessionId

**Cause**: Your `/api/auth/token` endpoint isn't returning `sessionId`, or the response shape is wrong.

```ts
// ✅ Your endpoint must return sessionId in the response
return NextResponse.json({ sessionId: data.sessionId });

// ✅ Your callback must return { sessionId: string }
handleAuthentication: async (code) => {
  const res = await fetch('/api/auth/token', { ... });
  const data = await res.json();
  return { sessionId: data.sessionId };  // Must be exactly this shape
}
```

---

## Workspace / Gate Issues

### WhenSubscription renders nothing (even though there IS a subscription)

Most likely causes:
1. **Loading state** — The gate returns null while loading. Add `loadingComponent` to verify.
2. **No current workspace** — The gate requires `currentWorkspace` to be set.
3. **Subscription on wrong workspace** — You're checking the wrong workspace.

```tsx
// Debug loading vs condition-not-met
<WhenSubscription
  loadingComponent={<span style={{ color: 'orange' }}>LOADING...</span>}
  fallbackComponent={<span style={{ color: 'red' }}>NO SUBSCRIPTION</span>}
>
  <span style={{ color: 'green' }}>HAS SUBSCRIPTION</span>
</WhenSubscription>
```

---

### Feature flags always return false

**Causes**:
1. Feature slug doesn't match dashboard exactly (case-sensitive)
2. Feature not defined in the Buildbase dashboard
3. Feature not enabled for this workspace

**Fix**:
```tsx
// Debug: log all features
const { features } = useUserFeatures();
console.log('All features:', features);

// Verify slug matches dashboard definition exactly
<WhenWorkspaceFeatureEnabled slug="advanced-analytics">  // Must match dashboard slug
```

---

### "Invalid orgId" despite having the right ID

**Cause**: Common when using environment variables — the value might have whitespace or the env var isn't loaded.

```ts
// Debug
console.log('orgId length:', process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID?.length);
console.log('orgId:', JSON.stringify(process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID));
```

---

## Styling Issues

### SDK components look unstyled

**Cause**: The CSS import is missing.

```tsx
// app/layout.tsx — must be at root level
import '@buildbase/sdk/css';
```

This is required. The SDK uses Tailwind CSS with a prefix, bundled as a separate CSS file.

---

## TypeScript Errors

### Type error: "Property 'xxx' does not exist on type 'IWorkspace'"

Import the types that the package actually exports:

```tsx
import type { ISubscriptionResponse, ISubscription, IPlan } from '@buildbase/sdk';
```

Note: not every internal interface is part of the public type surface. `ISubscriptionResponse`, `ISubscription`, `IPlan`, and the credit/quota/invoice `I*` types are exported, but `IWorkspace` and `IUser` are **not** re-exported from `@buildbase/sdk` — if you need their shape, derive it from a hook's return value (e.g. `ReturnType`/inference from `useSaaSWorkspaces().currentWorkspace`) rather than importing the interface.

---

### "Module '@buildbase/sdk/react' has no exported member 'xxx'"

Check the SDK version. Features are being added in newer versions.

```bash
npm list @buildbase/sdk  # Check installed version
npm install @buildbase/sdk@latest  # Update to latest
```

---

## Performance Issues

### Component re-renders excessively during workspace switches

**Cause**: Creating new callback functions on every render.

```tsx
// ❌ New functions created on every render
<SaaSOSProvider
  auth={{
    callbacks: {
      getSession: async () => { ... },        // New function every render
      handleAuthentication: async (code) => { ... },  // New function every render
    }
  }}
>

// ✅ Define callbacks outside the component or use useCallback
const authCallbacks = useMemo(() => ({
  getSession: async () => { ... },
  handleAuthentication: async (code) => { ... },
  onSignOut: async () => { ... },
}), []);

<SaaSOSProvider auth={{ clientId, redirectUrl, callbacks: authCallbacks }}>
```

The SDK memoizes callbacks internally by function reference, but defining them inline still causes unnecessary effect re-runs.
