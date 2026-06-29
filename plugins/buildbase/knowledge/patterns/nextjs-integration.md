# Complete Next.js Integration Pattern

This is the production-ready integration pattern based on the official `nextjs-starter` reference implementation.

> **New to Buildbase? Start with the beginner golden path in [`../sdk/quick-start.md`](../sdk/quick-start.md).** That guide gets you from zero to signed in with the minimal set of files. THIS file is the complete/production reference: it stays consistent with quick-start but goes further, adding the advanced/production pieces (`onWorkspaceChange`, the `/api/auth/workspace-token` route, events sync, and server-side route protection).

**Conventions (same as quick-start):** TypeScript + Next.js App Router + React (18 or 19; the starter uses 19). All files live under `src/` (`src/lib`, `src/app`, `src/components`), and the `@/` import alias maps to `./src/*`.

## Contents

- [How sign-in works (the short version)](#how-sign-in-works-the-short-version) — the auth flow in brief
- [Project Structure](#project-structure) — file/folder layout
- [1. Environment Variables](#1-environment-variables) — `.env.local` keys
- [2. src/lib/buildbase.ts](#2-srclibbuildbasets) — server-side factory
- [3. API Auth Endpoints](#3-api-auth-endpoints) — token, session, signout routes
- [4. src/components/saas-provider.tsx](#4-srccomponentssaas-providertsx) — provider with optional `onWorkspaceChange`
- [5. src/app/layout.tsx](#5-srcapplayouttsx) — root layout + CSS import
- [6. Protected Page Example](#6-protected-page-example) — client-side auth gating
- [7. Server-Side Protected API Route](#7-server-side-protected-api-route) — guarding an API route
- [8. Advanced (optional) — your app's own workspace-scoped JWT](#8-advanced-optional--your-apps-own-workspace-scoped-jwt) — minting your own JWT

---

## How sign-in works (the short version)

When you call `signIn()`, the SDK redirects the browser to Buildbase's login page. After the user logs in, Buildbase sends them back to your `redirectUrl` with a one-time `?code=` in the URL. **You don't write code to parse the `code`** — the SDK reads it automatically when the provider mounts, then calls your `handleAuthentication` callback, which posts to your token route (named `/api/auth/token` here; the official docs name it `/api/auth/verify` — it's your own route, so either is fine). That route trades the code (using your secret) for a `sessionId` and stores it in an httpOnly cookie. On every refresh the SDK restores the session via `/api/auth/session`.

The only requirement is that your `redirectUrl` points at a page your `SaaSOSProvider` wraps. The official docs use `http://localhost:3000/callback` and allow-list it under Settings → OAuth → Redirect URLs; a minimal `/callback` page (or the root page, if you redirect there) is enough. See [quick-start.md](../sdk/quick-start.md) Step 7 for the callback page.

---

## Project Structure

```
src/
  lib/
    buildbase.ts        — Server-side BuildBase() factory
    auth.ts             — JWT utilities (for your own app auth)
  components/
    saas-provider.tsx   — 'use client' wrapper for SaaSOSProvider
  app/
    api/
      auth/
        token/route.ts          — Exchange OAuth code for sessionId
        session/route.ts        — Read cookie, return sessionId
        signout/route.ts        — Clear cookie
        workspace-token/route.ts — (ADVANCED/OPTIONAL) Mint your app's OWN workspace-scoped JWT
      events/route.ts           — (ADVANCED/OPTIONAL) Sync SDK events to your DB
    layout.tsx                  — Root layout with CSS import + SaaSProvider
```

---

## 1. Environment Variables

```env
# .env.local
NEXT_PUBLIC_BUILDBASE_SERVER_URL=https://api.console.buildbase.app
NEXT_PUBLIC_BUILDBASE_ORG_ID=<24-char-hex-from-dashboard>
NEXT_PUBLIC_BUILDBASE_CLIENT_ID=<client-id-from-dashboard>
NEXT_PUBLIC_BUILDBASE_REDIRECT_URL=http://localhost:3000
BUILDBASE_CLIENT_SECRET=<secret-from-dashboard>   # Server-side only
```

---

## 2. src/lib/buildbase.ts

```ts
// src/lib/buildbase.ts
import BuildBase from '@buildbase/sdk';
import { cookies } from 'next/headers';

export const SESSION_COOKIE_NAME = 'bb-session-id';

export const {
  auth, workspace, subscription, users, plans,
  usage, credits, features, settings, notification,
  withSession, client,
} = BuildBase({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!,
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!,
  getSessionId: async () => {
    const c = await cookies();
    return c.get(SESSION_COOKIE_NAME)?.value ?? null;
  },
});
```

---

## 3. API Auth Endpoints

### src/app/api/auth/token/route.ts

Exchanges OAuth code for Buildbase sessionId. Sets httpOnly cookie.

```ts
// src/app/api/auth/token/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST(request: NextRequest) {
  const { code } = await request.json();

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL}/api/v1/auth/token`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        clientId: process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID,
        clientSecret: process.env.BUILDBASE_CLIENT_SECRET,
        orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID,
      }),
    }
  );

  if (!res.ok) {
    return NextResponse.json({ error: 'Auth failed' }, { status: 401 });
  }

  // Buildbase returns { data: { sessionId, user } }
  const { data } = await res.json();

  const response = NextResponse.json({ sessionId: data.sessionId });
  response.cookies.set(SESSION_COOKIE_NAME, data.sessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 7,  // 7 days
  });
  return response;
}
```

### src/app/api/auth/session/route.ts

Called by SDK on page refresh to restore session.

```ts
// src/app/api/auth/session/route.ts
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function GET() {
  const c = await cookies();
  const sessionId = c.get(SESSION_COOKIE_NAME)?.value ?? null;
  return NextResponse.json({ sessionId });
}
```

### src/app/api/auth/signout/route.ts

Clears the session cookie.

```ts
// src/app/api/auth/signout/route.ts
import { NextResponse } from 'next/server';
import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST() {
  const response = NextResponse.json({ success: true });
  response.cookies.set(SESSION_COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,  // Delete cookie
  });
  return response;
}
```

---

## 4. src/components/saas-provider.tsx

The `onWorkspaceChange` callback below is **ADVANCED / OPTIONAL** — it depends on the optional `/api/auth/workspace-token` route (Section 8). **Skip it for a first integration**; omit the callback and you don't need that route at all.

```tsx
// src/components/saas-provider.tsx
'use client';

import { SaaSOSProvider } from '@buildbase/sdk/react';
import { ApiVersion } from '@buildbase/sdk';

export function SaaSProvider({ children }: { children: React.ReactNode }) {
  return (
    <SaaSOSProvider
      serverUrl={process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!}
      version={ApiVersion.V1}
      orgId={process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!}
      auth={{
        clientId: process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID!,
        redirectUrl: process.env.NEXT_PUBLIC_BUILDBASE_REDIRECT_URL!,
        callbacks: {
          getSession: async () => {
            const res = await fetch('/api/auth/session');
            const data = await res.json();
            return data.sessionId ?? null;
          },
          handleAuthentication: async (code) => {
            const res = await fetch('/api/auth/token', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ code }),
            });
            const data = await res.json();
            return { sessionId: data.sessionId };
          },
          onSignOut: async () => {
            await fetch('/api/auth/signout', { method: 'POST' });
          },
          // ADVANCED / OPTIONAL — remove this callback (and Section 8's route)
          // for a first integration. Mints your app's OWN workspace-scoped JWT.
          onWorkspaceChange: async ({ workspace, user, role }) => {
            if (!user?.id || !workspace?._id) return;
            const res = await fetch('/api/auth/workspace-token', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ userId: user.id, workspaceId: workspace._id, userRole: role }),
            });
            const data = await res.json();
            if (data.token) localStorage.setItem('auth_token', data.token);
          },
        },
      }}
      defaultPermissions={{
        admin: ['create', 'delete', 'export'],
        editor: ['create'],
        viewer: [],
      }}
    >
      {children}
    </SaaSOSProvider>
  );
}
```

---

## 5. src/app/layout.tsx

```tsx
// src/app/layout.tsx
import { SaaSProvider } from '@/components/saas-provider';
import '@buildbase/sdk/css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SaaSProvider>{children}</SaaSProvider>
      </body>
    </html>
  );
}
```

---

## 6. Protected Page Example

```tsx
// src/app/dashboard/page.tsx
'use client';

import { useSaaSAuth, useSaaSWorkspaces, WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';

export default function DashboardPage() {
  const { user, signIn } = useSaaSAuth();
  const { currentWorkspace } = useSaaSWorkspaces();

  return (
    <>
      <WhenUnauthenticated>
        <div className="flex items-center justify-center min-h-screen">
          <button onClick={() => signIn()} className="btn-primary">
            Sign In to Continue
          </button>
        </div>
      </WhenUnauthenticated>

      <WhenAuthenticated>
        <div>
          <h1>Welcome, {user?.name}</h1>
          <p>Workspace: {currentWorkspace?.name ?? 'Loading...'}</p>
        </div>
      </WhenAuthenticated>
    </>
  );
}
```

---

## 7. Server-Side Protected API Route

```ts
// src/app/api/data/route.ts
import { auth } from '@/lib/buildbase';

export async function GET() {
  const session = await auth();
  if (!session) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // session.sessionId is available if needed
  // All buildbase actions now use the session automatically
  
  return Response.json({ data: 'protected' });
}
```

---

## 8. Advanced (optional) — your app's own workspace-scoped JWT

> **Skip this for a first integration.** This route is referenced by the optional `onWorkspaceChange` callback in Section 4. It mints your app's **OWN** signed token (JWT) so your own backend can identify the user + workspace, independent of Buildbase's session. Most apps don't need this initially — if you don't, omit the `onWorkspaceChange` callback and don't create this file.

### src/app/api/auth/workspace-token/route.ts

```typescript
// src/app/api/auth/workspace-token/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { createAuthToken } from '@/lib/auth';
import { workspaceTokenSchema } from '@/lib/validation/schemas';
import { validateBody, isValidationError } from '@/lib/validation/api';
import { logger } from '@/lib/logger';

export async function POST(request: NextRequest) {
  try {
    const validationResult = await validateBody(request, workspaceTokenSchema);
    if (isValidationError(validationResult)) {
      return validationResult;
    }

    const { userId, workspaceId, userRole } = validationResult;

    const token = createAuthToken({ userId, workspaceId, userRole });

    logger.debug('Workspace token generated', { userId, workspaceId, userRole });

    return NextResponse.json({ success: true, token });
  } catch (error) {
    logger.error('Workspace token generation failed', {
      error: error instanceof Error ? error.message : 'Unknown error',
    });
    return NextResponse.json(
      { success: false, message: 'Failed to generate token' },
      { status: 500 }
    );
  }
}
```

> **Note:** `createAuthToken`, `workspaceTokenSchema`, `validateBody`, and `logger` are the **APP'S OWN helpers** (JWT signing, Zod schema/validation, logging) — they are **not** exported by `@buildbase/sdk`. Implement them yourself (e.g. `@/lib/auth`, `@/lib/validation/schemas`, `@/lib/validation/api`, `@/lib/logger`) or remove this route if you don't need your own JWT.
