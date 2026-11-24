# Complete Next.js Integration Pattern

This is the production-ready integration pattern for the Next.js App Router. The core files (Sections 1 to 5) are exactly the ones `npx @buildbase/sdk init` writes in `@buildbase/sdk` 1.8.0; the official [`nextjs-starter`](https://github.com/buildbase-app/nextjs-starter) and the [`with-buildbase`](https://github.com/buildbase-app/examples/tree/main/with-buildbase) example are the same wiring in running apps.

> **New to BuildBase? Start with the beginner golden path in [`../sdk/quick-start.md`](../sdk/quick-start.md).** That guide gets you from zero to signed in with the minimal set of files, and explains each one. THIS file is the complete/production reference: it stays consistent with quick-start but goes further, adding the advanced/production pieces (`defaultPermissions`, `onWorkspaceChange`, the `/api/auth/workspace-token` route, environments, server-side route protection).

**Conventions (same as quick-start):** TypeScript + Next.js App Router + React (18 or 19). All files live under `src/` (`src/lib`, `src/app`, `src/components`), and the `@/` import alias maps to `./src/*`. (`init` writes the same files at the root, `lib/`, `app/`, `components/`, when the app has no `src/` folder.)

## Contents

- [Let init write the core files](#let-init-write-the-core-files) - one command, or `--claim` with no account
- [How sign-in works (the short version)](#how-sign-in-works-the-short-version) - the auth flow in brief
- [Project Structure](#project-structure) - file/folder layout
- [1. Environment Variables](#1-environment-variables) - `.env.local` keys, and development or staging environments
- [2. src/lib/buildbase.ts](#2-srclibbuildbasets) - server-side factory
- [3. API Auth Endpoints](#3-api-auth-endpoints) - token, session, signout routes
- [4. src/components/saas-provider.tsx](#4-srccomponentssaas-providertsx) - provider with `defaultPermissions` and optional `onWorkspaceChange`
- [5. src/app/layout.tsx](#5-srcapplayouttsx) - root layout + CSS import
- [6. Protected Page Example](#6-protected-page-example) - client-side auth gating and session restore
- [7. Server-Side Protected API Route](#7-server-side-protected-api-route) - guarding an API route
- [8. Advanced (optional) - your app's own workspace-scoped JWT](#8-advanced-optional---your-apps-own-workspace-scoped-jwt) - minting your own JWT
- [9. Webhooks, agents and the hosted console MCP](#9-webhooks-agents-and-the-hosted-console-mcp) - what else to wire, and what not to confuse

---

## Let init write the core files

```bash
npm install @buildbase/sdk
npx buildbase init --org-id <24 hex>
```

It writes Sections 1 to 5 plus the webhook route (`src/app/api/webhooks/buildbase/route.ts`, switching on `payment.failed`), with every secret left empty, and is idempotent: a second run says `already configured` and changes nothing. Outside a project that has the SDK installed, run `npx @buildbase/sdk init ...`, never `npx buildbase` (the unscoped package is not ours).

**An agent (or a person) with no account and no org id yet:** `npx @buildbase/sdk init --claim --yes` creates a claimable organization through central's `POST /api/organizations/agent/identity`, makes a sign-in client for the app's local redirect URL, writes the org id, client id, client secret and the organization's key (`BUILDBASE_API_TOKEN`) to `.env.local`, and prints a claim URL and code once. A person claims it (signs in or up on that page and types the code); unclaimed it is deleted after 72 hours. Details and exit codes: [quick-start.md](../sdk/quick-start.md#no-account-yet-a-person-or-a-coding-agent-starting-from-nothing).

Then add what this page adds on top: `defaultPermissions` (Section 4), the protected pages and routes (Sections 6 and 7), and the optional pieces.

---

## How sign-in works (the short version)

When you call `signIn()`, the SDK redirects the browser to BuildBase's hosted sign-in page. After the user logs in, BuildBase sends them back to your `redirectUrl` with a one-time `?code=` in the URL. **You don't write code to parse the `code`**: the SDK reads it automatically when the provider mounts, then calls your `handleAuthentication` callback, which posts to your token route (`/api/auth/token`; it's your own route, and the name only has to match between the provider and the route). That route trades the code (using your secret) for a `sessionId` and stores it in an httpOnly cookie, `bb-session-id`. The SDK then sends the user back to the page where they pressed Sign In. On every refresh the SDK restores the session via `/api/auth/session`.

The only requirement is that your `redirectUrl` points at a page your provider wraps. `init` uses the app root, `http://localhost:3000`, allow-listed on the auth client's **Redirect URLs** in the console; a dedicated `/callback` page also works (see [quick-start.md](../sdk/quick-start.md) Step 7).

---

## Project Structure

```
src/
  lib/
    buildbase.ts        - Server-side BuildBase() factory
    auth.ts             - JWT utilities (for your own app auth, Section 8 only)
  components/
    saas-provider.tsx   - 'use client' wrapper for SaaSOSProvider
  app/
    api/
      auth/
        token/route.ts          - Exchange OAuth code for sessionId
        session/route.ts        - Read cookie, return sessionId
        signout/route.ts        - Clear cookie
        workspace-token/route.ts - (ADVANCED/OPTIONAL) Mint your app's OWN workspace-scoped JWT
      webhooks/buildbase/route.ts - Verify and handle BuildBase webhooks (quick-start Step 8)
    layout.tsx                  - Root layout with CSS import + SaaSProvider
```

---

## 1. Environment Variables

The names `init` writes, in its order:

```env
# .env.local
NEXT_PUBLIC_BUILDBASE_SERVER_URL=https://api.console.buildbase.app
NEXT_PUBLIC_BUILDBASE_ORG_ID=<24-char-hex-from-console>
NEXT_PUBLIC_BUILDBASE_ENVIRONMENT=
NEXT_PUBLIC_BUILDBASE_CLIENT_ID=<client-id-from-console>
NEXT_PUBLIC_BUILDBASE_REDIRECT_URL=http://localhost:3000
# Server-side only. Paste the values after the = sign; never commit them.
BUILDBASE_CLIENT_SECRET=
BUILDBASE_WEBHOOK_SECRET=
```

### Development and staging environments

`NEXT_PUBLIC_BUILDBASE_ENVIRONMENT` is empty for production. Set it to a development or staging environment's key (eight lowercase letters, from the console) and the SDK sends `<orgId>-<key>` wherever it sent `orgId`, against that environment's own database, users and auth client. It is never inferred from `NODE_ENV`. The session cookie becomes `bb-session-id-<key>` (Section 2), so two environments of one app on localhost never read each other's session.

The CLI does the wiring after `npx @buildbase/sdk login` (a device-code sign-in the person approves in the console): `npx @buildbase/sdk init --dev [--env <name>]` points `.env.local` at an environment with its client id and secret filled in (the secret only when git ignores `.env.local`), and `npx @buildbase/sdk env <list|use|create|diff|push|pull>` lists environments, switches between them, creates one (owner or admin, within the plan) and compares or promotes email templates, workflows and plans with production. Ask the person before `env create` and `env push`.

---

## 2. src/lib/buildbase.ts

```ts
// src/lib/buildbase.ts
// Server-side BuildBase client. Import from here in route handlers and server
// components; never from a client component.
import BuildBase from '@buildbase/sdk';
import { cookies } from 'next/headers';

// One cookie name per environment, so two environments on one host never
// read each other's session.
const environment = process.env.NEXT_PUBLIC_BUILDBASE_ENVIRONMENT;
export const SESSION_COOKIE_NAME =
  environment && environment !== 'production' ? `bb-session-id-${environment}` : 'bb-session-id';

export const {
  auth,
  exchangeCode,
  workspace,
  subscription,
  users,
  plans,
  usage,
  credits,
  features,
  settings,
  notification,
  permissions,
  withSession,
  client,
} = BuildBase({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL || 'https://api.console.buildbase.app',
  // Empty until .env.local is filled in: `next build` still succeeds, and the
  // first call throws an error that names NEXT_PUBLIC_BUILDBASE_ORG_ID.
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID ?? '',
  environment: process.env.NEXT_PUBLIC_BUILDBASE_ENVIRONMENT || undefined,
  getSessionId: async () => {
    const c = await cookies();
    return c.get(SESSION_COOKIE_NAME)?.value ?? null;
  },
});
```

`init` writes this file without `client` (the low-level client; add it when you need `client.forSession`). `sessionCookieName(environment)` from `@buildbase/sdk` computes the same cookie name.

---

## 3. API Auth Endpoints

### src/app/api/auth/token/route.ts

Exchanges the OAuth code for a BuildBase sessionId and sets the httpOnly cookie. `refuseCrossSiteAuthPost` goes first: it answers `415` unless the body is JSON and `403` for another site's `Origin`, so a form on another site cannot sign the visitor in to someone else's account (login CSRF).

```ts
// src/app/api/auth/token/route.ts
import { AuthCodeExchangeError, refuseCrossSiteAuthPost } from '@buildbase/sdk';
import { NextRequest, NextResponse } from 'next/server';

import { exchangeCode, SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST(request: NextRequest) {
  const refused = refuseCrossSiteAuthPost(request);
  if (refused) return refused;
  const { code } = (await request.json()) as { code?: string };
  if (!code) return NextResponse.json({ error: 'Missing code' }, { status: 400 });

  try {
    // POST /api/v1/auth/token on the platform, with the org and environment filled in.
    const { sessionId } = await exchangeCode({
      code,
      clientId: process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID ?? '',
      clientSecret: process.env.BUILDBASE_CLIENT_SECRET ?? '',
    });
    const response = NextResponse.json({ sessionId });
    response.cookies.set(SESSION_COOKIE_NAME, sessionId, {
      httpOnly: true,
      // From the request, not NODE_ENV: a production build on a plain-http
      // host would set a Secure cookie the browser drops.
      secure: request.nextUrl.protocol === 'https:',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // 30 days
    });
    return response;
  } catch (error) {
    // The platform's status and sentence ("Invalid client secret"), never the secret.
    const e = error instanceof AuthCodeExchangeError ? error : null;
    return NextResponse.json(
      {
        error: 'Sign-in failed',
        ...(e?.message ? { message: e.message } : {}),
        ...(e?.code ? { code: e.code } : {}),
      },
      { status: e && e.status >= 400 ? e.status : 502 }
    );
  }
}
```

### src/app/api/auth/session/route.ts

Called by the SDK on page refresh to restore the session.

```ts
// src/app/api/auth/session/route.ts
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function GET() {
  const c = await cookies();
  return NextResponse.json({ sessionId: c.get(SESSION_COOKIE_NAME)?.value ?? null });
}
```

### src/app/api/auth/signout/route.ts

Clears the session cookie.

```ts
// src/app/api/auth/signout/route.ts
import { refuseCrossSiteAuthPost } from '@buildbase/sdk';
import { NextRequest, NextResponse } from 'next/server';

import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST(request: NextRequest) {
  const refused = refuseCrossSiteAuthPost(request);
  if (refused) return refused;
  const response = NextResponse.json({ success: true });
  response.cookies.set(SESSION_COOKIE_NAME, '', {
    httpOnly: true,
    secure: request.nextUrl.protocol === 'https:',
    sameSite: 'lax',
    path: '/',
    maxAge: 0, // Delete cookie
  });
  return response;
}
```

Off Next.js (TanStack Start, a Worker, Hono, any `fetch` handler), `createAuthHandler({ orgId, clientId, clientSecret })` from `@buildbase/sdk` is these three routes, the same cookie and the same cross-site check, as one `(request: Request) => Promise<Response | null>` handler.

---

## 4. src/components/saas-provider.tsx

This is `init`'s provider plus `defaultPermissions`. The `onWorkspaceChange` callback is **ADVANCED / OPTIONAL**: it depends on the optional `/api/auth/workspace-token` route (Section 8). **Skip it for a first integration**; omit the callback and you don't need that route at all.

```tsx
// src/components/saas-provider.tsx
'use client';

import '@buildbase/sdk/css';

import { ApiVersion } from '@buildbase/sdk';
import { KeylessPrompt, SaaSOSProvider } from '@buildbase/sdk/react';

// Until the env is filled in, render the app without BuildBase instead of throwing.
const isConfigured = Boolean(
  process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID &&
    process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID &&
    process.env.NEXT_PUBLIC_BUILDBASE_REDIRECT_URL
);

export function SaaSProvider({ children }: { children: React.ReactNode }) {
  if (!isConfigured) return <>{children}</>;

  return (
    <SaaSOSProvider
      serverUrl={process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL || 'https://api.console.buildbase.app'}
      version={ApiVersion.V1}
      orgId={process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!}
      environment={process.env.NEXT_PUBLIC_BUILDBASE_ENVIRONMENT || undefined}
      auth={{
        clientId: process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID!,
        redirectUrl: process.env.NEXT_PUBLIC_BUILDBASE_REDIRECT_URL!,
        callbacks: {
          getSession: async () => {
            const res = await fetch('/api/auth/session');
            return ((await res.json()) as { sessionId: string | null }).sessionId;
          },
          handleAuthentication: async (code: string) => {
            const res = await fetch('/api/auth/token', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ code }),
            });
            const body = (await res.json().catch(() => ({}))) as {
              sessionId?: string;
              message?: string;
            };
            if (!res.ok || !body.sessionId) {
              throw new Error(`Sign-in failed (${res.status}): ${body.message ?? 'no session'}`);
            }
            return { sessionId: body.sessionId };
          },
          onSignOut: async () => {
            // The JSON header is what refuseCrossSiteAuthPost checks for.
            await fetch('/api/auth/signout', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
            });
          },
          // ADVANCED / OPTIONAL: remove this callback (and Section 8's route)
          // for a first integration. Mints your app's OWN workspace-scoped JWT.
          onWorkspaceChange: async ({ workspace, user, role }) => {
            if (!user?.id || !workspace?._id) return;
            const res = await fetch('/api/auth/workspace-token', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ userId: user.id, workspaceId: workspace._id, userRole: role }),
            });
            const data = (await res.json()) as { token?: string };
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
      {/* Keyless development only; renders nothing without NEXT_PUBLIC_BUILDBASE_KEYLESS. */}
      <KeylessPrompt config={process.env.NEXT_PUBLIC_BUILDBASE_KEYLESS} />
    </SaaSOSProvider>
  );
}
```

- **`BuildBaseProvider`** is the same component as `SaaSOSProvider` under its brand name (props type `BuildBaseProviderProps`); prefer either, they are interchangeable.
- **`environment`** is the development or staging key from Section 1; unset is production.
- **`defaultPermissions`** declares which permissions your app has and which roles get them by default; workspace owners can change them per workspace in the settings dialog.
- Other callbacks in the `callbacks` object of the `auth` prop: `onSessionExpired(reason)`, `onAccessRefused(refusal)`, `onSessionEnded(ended)`, `onReauthRequired(refusal)`, and `handleEvent(eventType, data)` for the SDK's client-side events (`SDKEvent`). Anything that must reach your backend reliably belongs in a webhook, not `handleEvent`.

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

The layout is a **server** component. If it (or any server file) needs an SDK value such as `ApiVersion`, import it from the root entry, `@buildbase/sdk`: `@buildbase/sdk/react` is a `"use client"` boundary, and a server layout that reads an enum from it fails `next build`. That is also why the provider lives in its own `'use client'` file: a server component cannot pass the auth callbacks as props.

---

## 6. Protected Page Example

```tsx
// src/app/dashboard/page.tsx
'use client';

import { useSaaSAuth, useSaaSWorkspaces, WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';

export default function DashboardPage() {
  const { user, signIn, isLoading, isSessionUnverified } = useSaaSAuth();
  const { currentWorkspace } = useSaaSWorkspaces();

  // Restoring the session on page load: not signed out yet.
  if (isLoading) {
    return <p>{isSessionUnverified ? 'Cannot reach the server. Retrying...' : 'Loading...'}</p>;
  }

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

**Session restore rules** (the same for every page):

- The provider renders the app while it restores a stored session; its full-screen overlay shows only mid sign-in (`?code=` in the URL) and while sending the user to the hosted pages (`fullScreenLoader={false}` turns it off). **Gate on `useSaaSAuth().isLoading`**, and never treat `!isAuthenticated` while `isLoading` as signed out (no redirect to a login page, no automatic `signIn()`).
- **`isSessionUnverified: true`**: a session is stored but the API could not confirm it (no answer, a timeout of 8 s, a 5xx or a 429). The SDK keeps it and retries with backoff and on the browser's `online` event. Show "can't reach the server", never a sign-in prompt, and do not sign the user out yourself.
- A session ends only when the API refuses it: a 401, 403 or 404 on the page-load profile check clears it and calls `onSessionExpired('expired')`. A company's access refusal (`isAccessRefused`: 403 `ip_not_allowed` or `tenant_restricted`, 400 `tenant_header_invalid`) keeps the session and is reported through `onAccessRefused`.

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

  // session.sessionId is available if needed.
  // All buildbase actions now use the session automatically.

  return Response.json({ data: 'protected' });
}
```

---

## 8. Advanced (optional) - your app's own workspace-scoped JWT

> **Skip this for a first integration.** This route is referenced by the optional `onWorkspaceChange` callback in Section 4. It mints your app's **OWN** signed token (JWT) so your own backend can identify the user + workspace, independent of BuildBase's session. Most apps don't need this initially; if you don't, omit the `onWorkspaceChange` callback and don't create this file.

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

> **Note:** `createAuthToken`, `workspaceTokenSchema`, `validateBody`, `isValidationError` and `logger` are the **APP'S OWN helpers** (JWT signing, Zod schema/validation, logging). They are **not** exported by `@buildbase/sdk`. Implement them yourself (e.g. `@/lib/auth`, `@/lib/validation/schemas`, `@/lib/validation/api`, `@/lib/logger`) or remove this route if you don't need your own JWT.

---

## 9. Webhooks, agents and the hosted console MCP

- **Webhooks.** The route `init` writes, `src/app/api/webhooks/buildbase/route.ts`, is shown and explained in [quick-start.md](../sdk/quick-start.md#step-8---the-webhook-route): raw body, `parseWebhookEvent`, `isWebhookEvent`, dedupe on `event.id`, a `payment.failed` case. The secret is `BUILDBASE_WEBHOOK_SECRET`.
- **Make this app agent-ready** (its own MCP server, so its users' agents can sign in and use it): `npx @buildbase/sdk init --agent` writes `lib/agent.ts` (`createAgentStack` from `@buildbase/sdk/mcp`), `app/api/mcp/[[...card]]/route.ts`, the discovery routes and the agent sign-in routes (`/api/auth/agent-token`, `/api/auth/agent-revoke`). See [mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md).
- **Do not confuse that with BuildBase's hosted MCP server**, `https://api.console.buildbase.app/mcp` ("BuildBase Console"). It is how an AI tool manages the person's BuildBase organization (members, settings, content, blueprints) after the person signs in as themselves over OAuth; it is not part of your app. `npx @buildbase/sdk agent setup --console` adds it to the AI tools on a machine.
