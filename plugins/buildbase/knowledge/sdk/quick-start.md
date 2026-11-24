# Quick Start - From Zero to Signed In

This is the **golden path**: follow it top to bottom and you'll go from an empty folder to a working app where a user can sign in. Every file is shown in full. Every step tells you what it does and how to check it worked. You can paste most of it as-is.

There are two ways to get the same files:

- **Let the CLI write them.** `npx @buildbase/sdk init` writes every file below into your app in one command (see [The fastest path](#the-fastest-path-let-init-write-the-files)).
- **Write them yourself**, step by step (Steps 0 to 8). The files below are the ones `init` writes in `@buildbase/sdk` 1.8.0, with the comments expanded, so you learn what each one does and can fix it when something breaks.

> **This guide assumes Next.js (App Router) with TypeScript.** That's what `init` writes for a Next.js app and what the official examples use. `init` also wires TanStack Start, Vite and Express apps (the file names differ; see [The fastest path](#the-fastest-path-let-init-write-the-files)). For anything else, the *ideas* are the same but the file paths differ: ask for framework-specific help before pasting.
>
> **Prefer plain JavaScript?** You can. Use `.js`/`.jsx` instead of `.ts`/`.tsx` and delete the TypeScript bits: the `: Type` annotations (like `{ children }: { children: React.ReactNode }`), the `as { ... }` casts and the `!` after env vars. Everything else is identical.

## Contents

- [What you're about to build (the 30-second mental picture)](#what-youre-about-to-build-the-30-second-mental-picture) - what BuildBase does for you
- [How signing in actually works](#how-signing-in-actually-works-read-this-once) - the end-to-end login flow
- [The fastest path: let init write the files](#the-fastest-path-let-init-write-the-files) - `npx @buildbase/sdk init`, and `--claim` with no account
- [Before you start - collect your credentials](#before-you-start---collect-your-credentials) - the console values you need
- [Step 0 - Create the project](#step-0---create-the-project-skip-if-you-already-have-one) - scaffold a Next.js app
- [Step 1 - Install the SDK](#step-1---install-the-sdk) - add `@buildbase/sdk`
- [Step 2 - Add your credentials as environment variables](#step-2---add-your-credentials-as-environment-variables) - set up `.env.local`
- [Step 3 - Create the server-side "factory"](#step-3---create-the-server-side-factory) - configure `src/lib/buildbase.ts`
- [Step 4 - Create the three auth endpoints](#step-4---create-the-three-auth-endpoints) - token, session, signout routes
- [Step 5 - Create the React provider](#step-5---create-the-react-provider) - wrap your app with `SaaSOSProvider`
- [Step 6 - Wrap your app and import the CSS](#step-6---wrap-your-app-and-import-the-css) - root layout setup
- [Step 7 - Add a sign-in page and confirm it works](#step-7---add-a-sign-in-page-and-confirm-it-works) - test the full login flow
- [Step 8 - The webhook route](#step-8---the-webhook-route) - hear about failed payments and other events
- [One concept to carry forward: gates have THREE states](#one-concept-to-carry-forward-gates-have-three-states) - loading vs met vs not-met, and session restore
- [If something didn't work](#if-something-didnt-work) - symptom-to-cause troubleshooting table
- [What's next](#whats-next) - billing, feature flags, quotas, deeper guides

---

## What you're about to build (the 30-second mental picture)

BuildBase is a service that handles the boring-but-hard parts of a SaaS app for you: **logging users in, billing them, and tracking what they're allowed to do.** Think of it like hiring a security company for your building: they handle the locks, the membership cards, and the billing desk, so you just build the actual shop inside.

To connect your app to that service, you need to do two things:
1. **Tell BuildBase who your app is** (some credentials you copy from the BuildBase console).
2. **Wire up sign-in** (a few small files that pass login info safely between your app, your server, and BuildBase).

That's it. The rest of the SDK (billing, feature flags, etc.) builds on top of this foundation.

---

## How signing in actually works (read this once)

When you understand the flow, the files below stop looking like random rituals:

```
1. User clicks "Sign In"  ->  the SDK sends them to BuildBase's hosted sign-in page
2. User logs in there     ->  BuildBase sends them BACK to your redirectUrl
                              with a one-time "code" in the URL (?code=...)
3. The SDK automatically reads that code  ->  hands it to your /api/auth/token route
4. Your route trades the code (using your client secret) for a "sessionId"
                              ->  stores it in an httpOnly cookie
5. The SDK sends the user back to the page where they clicked "Sign In".
   From now on they are logged in. On every refresh, the SDK asks
   /api/auth/session for the cookie's sessionId.
```

Three things worth knowing:
- **You don't write any code to read the `code` from the URL.** The SDK does that automatically when the provider loads. The page BuildBase redirects back to (your `redirectUrl`) only has to be wrapped by your provider. Since the provider lives in your root layout (Step 6), every page qualifies, so `init` simply uses your app's root, `http://localhost:3000`.
- A **`sessionId`** is just BuildBase's word for "proof this user is logged in." You keep it in a cookie so it survives page refreshes.
- **On page load the session is restored in the background.** The provider renders your app straight away and `useSaaSAuth().isLoading` is `true` until the API has confirmed the stored session. Never treat "not authenticated yet" during that time as "signed out" (more in [the gates section](#one-concept-to-carry-forward-gates-have-three-states)).

---

## The fastest path: let init write the files

In the root of an existing Next.js, TanStack Start, Vite or Express app:

```bash
npm install @buildbase/sdk
npx buildbase init --org-id <your 24-character org id>
```

Outside a project that has `@buildbase/sdk` installed, always run the scoped form, `npx @buildbase/sdk init ...`. Never `npx buildbase` there: the unscoped `buildbase` package on npm is not ours.

On a Next.js App Router app, `init` 1.8.0 writes exactly the files of Steps 2 to 8 (under `src/` when your app uses it):

| File | What it is | Step |
|---|---|---|
| `lib/buildbase.ts` | The server-side factory, with the `bb-session-id` cookie name | 3 |
| `app/api/auth/token/route.ts` | Trades the sign-in code for a session in an **httpOnly** cookie | 4 |
| `app/api/auth/session/route.ts` | Tells the provider who is signed in after a refresh | 4 |
| `app/api/auth/signout/route.ts` | Clears the cookie | 4 |
| `components/saas-provider.tsx` | The provider, as a client component | 5 |
| `app/layout.tsx` | Edited in place: the CSS import and the `<SaaSProvider>` wrapper | 6 |
| `app/api/webhooks/buildbase/route.ts` | Verifies webhooks and switches on `payment.failed` | 8 |
| `.env.example`, `.env.local` | The env names, with every secret left **empty** (`.env.local` only when `.gitignore` covers it, and readable only by you) | 2 |

It is **idempotent**: a second run says `already configured` and changes nothing, and a file that already exists is kept. Then fill in `NEXT_PUBLIC_BUILDBASE_CLIENT_ID` (or pass `--client-id`) and `BUILDBASE_CLIENT_SECRET` in `.env.local`, add `http://localhost:3000` (init's default redirect URL; `--redirect-url` changes it) to your client's redirect URLs in the console, and skip to [Step 7](#step-7---add-a-sign-in-page-and-confirm-it-works). Until the client id is set, the provider init writes renders your app without BuildBase instead of throwing.

Other frameworks: **TanStack Start** gets the provider, the three auth routes as one server route (`src/routes/api/auth/$.ts`) and the webhook route; a **Vite** SPA, which has no server, gets `server/buildbase-auth.ts` to mount in its host's functions; **Express** gets a server-side client and a webhook handler. Non-interactive runs (CI, an agent) need `--framework <name>` for an empty directory (or `--yes` for Next.js) and `--org-id` always, unless you use `--claim`. Secrets are never flags.

### No account yet (a person or a coding agent starting from nothing)

```bash
npx @buildbase/sdk init --claim --yes --name "Acme" --email you@example.com
```

`--name` and `--email` are optional. This creates a **claimable organization** with no account (central's `POST /api/organizations/agent/identity`), gives it a sign-in client for your app's local URL, writes the files above, and puts the org id, client id, redirect URL, the client secret and the organization's key (`BUILDBASE_API_TOKEN`) into `.env.local`. It prints the expiry, a claim URL and a claim code, once, and never prints the key or the secret.

- **A person claims it.** Give them the claim URL and code: they sign in or sign up there and type the code. An agent never does this step for them. Unclaimed, the organization is deleted after **72 hours**.
- A code lasts 15 minutes; `npx @buildbase/sdk claim-code` prints a fresh one.
- After the claim the org id and client keep working, but the temporary key stops. Get permanent keys with `npx @buildbase/sdk init --dev` (after `npx @buildbase/sdk login`) or copy them from the console.
- Until it is claimed it runs on caps: at most 50 end users, Stripe test keys only, no invitations, no extra environments, and its only email is sign-in and verification mail in BuildBase's fixed wording. Add an email sender after the claim, before real users sign up.
- Exit codes: `2` refused (`.env.local` already names an organization), `3` the daily limit for that email address, `4` the platform has no claimable organizations, `5` (`claim-code`) the key was refused because the organization was claimed or expired.

`init` also takes `--agent` (make the app agent-ready too: its own MCP server at `/api/mcp` and the agent sign-in routes; see [mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md)) and `--dev` (wire it to a development or staging environment, after `npx @buildbase/sdk login`). Every command is in `node_modules/@buildbase/sdk/agents/cli.md`.

> **Managing the BuildBase organization itself from an AI tool** (plans, members, settings, blueprints) is a different thing: BuildBase's hosted MCP server, `https://api.console.buildbase.app/mcp`, where the person signs in as themselves. `npx @buildbase/sdk agent setup --console` adds it to the AI tools on their machine.

The rest of this page writes the same files by hand.

---

## Before you start - collect your credentials

**Don't have a BuildBase account yet?** Sign up and log in at **[console.buildbase.app](https://console.buildbase.app)**. That's the **console**, where you create and manage everything (your org, auth clients, plans, features). Official docs live at **[docs.buildbase.app](https://docs.buildbase.app)**. (The console is a *different* address from the `serverUrl` you'll copy below: `serverUrl` is the API your app talks to, not a site you log into.) No account and you want to start anyway? Use [`init --claim`](#no-account-yet-a-person-or-a-coding-agent-starting-from-nothing).

Once you're in the console, find these values. Keep them somewhere handy; you'll paste them into a file in Step 2.

| Value | What it is | Where to look |
|------|------------|---------------|
| `serverUrl` | The BuildBase API your app talks to | **It's a fixed value: `https://api.console.buildbase.app`** (unless you self-host) |
| `orgId` | Your organization's unique ID: a **24-character hex string** like `507f1f77bcf86cd799439011` (not a name!) | **Settings** > **General**, or the dialog shown when you create the auth client |
| `clientId` | Public ID for your app's login | Left rail **Users**, then **Authentication** under **Access**, **Settings** tab: your auth client's row |
| `clientSecret` | **Secret** key for your app's login, like a password. Never goes in the browser. | The dialog shown when you create the auth client, **and only there** (lost it? **Edit** the client and **Regenerate**) |
| `redirectUrl` | Where BuildBase sends users back after login. For local dev: `http://localhost:3000` | You set this yourself, then allow-list it (below) |
| `environment` (optional) | A development or staging environment's key (eight lowercase letters). Leave it empty for production | The console's environments, or `npx @buildbase/sdk env list` |

> **Three things beginners miss in the console:**
> 1. **Create an auth client** (Authentication, **Settings** tab, **Create auth client**) and **add at least one sign-in method** (Authentication, **Methods** tab, for example Email/Password or Magic link), then **tick that method on the client**. A client with no method shows "This app has no sign-in methods yet." on its sign-in page.
> 2. Add your `redirectUrl` under the client's **Edit**, **Redirect URLs**, or login fails with "Invalid redirect URL". It must match exactly (a `localhost` address matches any port).
> 3. **Connect an email sender** (left rail **Messaging**, **Sender accounts**). Sign-in codes, magic links and password resets are email: until a sender is connected, nobody receives them.

---

## Step 0 - Create the project (skip if you already have one)

If you don't already have a Next.js app, create one. This exact command sets up everything this guide assumes (TypeScript, App Router, the `src/` folder, and the `@/` import shortcut):

```bash
npx create-next-app@latest my-app --typescript --app --src-dir --import-alias "@/*"
cd my-app
```

When prompted, the defaults are fine. The `@/` import alias it sets up is what makes `import { x } from '@/lib/buildbase'` work: it's a shortcut for "the `src/` folder."

✅ **Check:** `npm run dev`, open http://localhost:3000. You should see the default Next.js welcome page.

---

## Step 1 - Install the SDK

```bash
npm install @buildbase/sdk
```

The SDK needs React to run but doesn't bundle its own (so it can't clash with yours). It works with React 18 or 19, and Node 18 or later. This guide was checked against `@buildbase/sdk` 1.8.0.

✅ **Check:** `npm ls @buildbase/sdk` prints a version with no errors.

---

## Step 2 - Add your credentials as environment variables

Create a file named exactly `.env.local` in your **project root** (the same folder as `package.json`). These are the names `init` writes, in its order. Fill in the values you collected:

```env
# Safe to expose to the browser (that's what NEXT_PUBLIC_ means):
NEXT_PUBLIC_BUILDBASE_SERVER_URL=https://api.console.buildbase.app
NEXT_PUBLIC_BUILDBASE_ORG_ID=your-24-char-hex-org-id
# A development or staging environment's key. Empty is production.
NEXT_PUBLIC_BUILDBASE_ENVIRONMENT=
NEXT_PUBLIC_BUILDBASE_CLIENT_ID=your-client-id
NEXT_PUBLIC_BUILDBASE_REDIRECT_URL=http://localhost:3000

# SECRETS - server-side only. NEVER add NEXT_PUBLIC_ to these.
# Paste the client secret after the = sign. The webhook secret comes in Step 8.
BUILDBASE_CLIENT_SECRET=
BUILDBASE_WEBHOOK_SECRET=
```

**Why the `NEXT_PUBLIC_` prefix matters:** In Next.js, any variable starting with `NEXT_PUBLIC_` gets shipped to the browser where anyone can read it. That's fine for the public IDs, but the **`clientSecret` must never have that prefix**, or you'd be handing your password to every visitor.

`create-next-app` already tells git to ignore `.env.local` (its `.env*` line), so your secrets won't be committed. That line hides `.env.example` too: to commit an example file with the same names, add `!.env.example` to `.gitignore` (as `init` does) and leave every secret in it empty.

✅ **Check:** After creating or editing `.env.local`, **restart `npm run dev`**: environment changes don't hot-reload.

---

## Step 3 - Create the server-side "factory"

Create `src/lib/buildbase.ts`. A **factory** here just means "a function you call once that hands you back a set of ready-to-use tools." You configure BuildBase once, and get back tools (`auth`, `exchangeCode`, `workspace`, `subscription`, ...) you'll use in your server code.

```ts
// src/lib/buildbase.ts
// Server-side BuildBase client. Import from here in route handlers and server
// components; never from a client component.
import BuildBase from '@buildbase/sdk';
import { cookies } from 'next/headers';

// The cookie that carries the signed-in user's session id. Used in several
// files, so it is defined once here. A development or staging environment gets
// its own name, so two environments of one app on localhost never read each
// other's session.
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
} = BuildBase({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL || 'https://api.console.buildbase.app',
  // Empty until .env.local is filled in: `next build` still succeeds, and the
  // first call throws an error that names NEXT_PUBLIC_BUILDBASE_ORG_ID.
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID ?? '',
  // A development or staging environment's key; unset is production.
  environment: process.env.NEXT_PUBLIC_BUILDBASE_ENVIRONMENT || undefined,
  // The SDK calls this whenever it needs the current user's session.
  // We read it from the httpOnly cookie.
  getSessionId: async () => {
    const c = await cookies();
    return c.get(SESSION_COOKIE_NAME)?.value ?? null;
  },
});
```

**About that big `export const { ... } =`:** this is "destructuring": it pulls many tools out of one function call and exports them all at once. You won't use most of them today; exporting them now just saves you editing this file later. Paste it as-is.

**About `environment`:** leave `NEXT_PUBLIC_BUILDBASE_ENVIRONMENT` empty for production. Set it to a development or staging environment's key and every request names `<orgId>-<key>` instead, against that environment's own users and data. It is never guessed from `NODE_ENV`.

✅ **Check:** No red squiggles / no TypeScript errors in this file. (It won't *do* anything yet; that's expected.)

---

## Step 4 - Create the three auth endpoints

These three small server routes are the secure middlemen between your app and BuildBase. In Next.js App Router, a file at `src/app/api/auth/token/route.ts` automatically becomes the URL `/api/auth/token`: **the folder path is the URL.**

### `src/app/api/auth/token/route.ts` - trade the login code for a session

This is the only file that touches your secret. It runs on the server, where the secret is safe.

```ts
// src/app/api/auth/token/route.ts
// Trades the one-time code from the hosted sign-in page for a session, and
// stores it in an httpOnly cookie. The only file that reads the client secret.
import { AuthCodeExchangeError, refuseCrossSiteAuthPost } from '@buildbase/sdk';
import { NextRequest, NextResponse } from 'next/server';

import { exchangeCode, SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST(request: NextRequest) {
  // Only this app's own JSON call: a form another site submits must not sign
  // the visitor in to someone else's account (login CSRF).
  const refused = refuseCrossSiteAuthPost(request);
  if (refused) return refused;
  const { code } = (await request.json()) as { code?: string };
  if (!code) return NextResponse.json({ error: 'Missing code' }, { status: 400 });

  try {
    // POSTs the code, your client id and secret to BuildBase's
    // /api/v1/auth/token, with the org (and environment) filled in.
    const { sessionId } = await exchangeCode({
      code,
      clientId: process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID ?? '',
      clientSecret: process.env.BUILDBASE_CLIENT_SECRET ?? '',
    });
    const response = NextResponse.json({ sessionId });
    // An httpOnly cookie is one your browser JavaScript CANNOT read, so a
    // script-injection attack can't steal the user's session.
    response.cookies.set(SESSION_COOKIE_NAME, sessionId, {
      httpOnly: true,
      // From the request, not NODE_ENV: `next start` on a plain-http host is
      // production, and a browser drops a Secure cookie sent over http.
      secure: request.nextUrl.protocol === 'https:',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24 * 30, // keep the user logged in for 30 days
    });
    return response;
  } catch (error) {
    // The platform's status and reason ("Invalid client secret", "Invalid or
    // expired authorization code"), so a wrong BUILDBASE_CLIENT_SECRET is
    // diagnosable. Never the secret itself.
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

`refuseCrossSiteAuthPost` answers `415` unless the body is `application/json` and `403` when an `Origin` header names another site, so call it first in any hand-written token or signout route. `exchangeCode` comes from the factory in Step 3; outside it, `exchangeAuthCode({ code, orgId, clientId, clientSecret })` from `@buildbase/sdk` does the same. (Not on Next.js? `createAuthHandler` from `@buildbase/sdk` is all three routes as one standard `Request -> Response` handler.)

### `src/app/api/auth/session/route.ts` - restore the session on refresh

The SDK calls this on every page load to ask "is anyone logged in?"

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

### `src/app/api/auth/signout/route.ts` - log out

```ts
// src/app/api/auth/signout/route.ts
import { refuseCrossSiteAuthPost } from '@buildbase/sdk';
import { NextRequest, NextResponse } from 'next/server';

import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST(request: NextRequest) {
  // Only this app's own JSON call: another site must not sign the visitor out.
  const refused = refuseCrossSiteAuthPost(request);
  if (refused) return refused;
  const response = NextResponse.json({ success: true });
  // Setting maxAge: 0 deletes the cookie.
  response.cookies.set(SESSION_COOKIE_NAME, '', {
    httpOnly: true,
    secure: request.nextUrl.protocol === 'https:',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
  return response;
}
```

✅ **Check:** Visit http://localhost:3000/api/auth/session in your browser. You should see `{"sessionId":null}`: the route works and nobody's logged in yet. (If you get a 404, the file path is wrong; it must be exactly `src/app/api/auth/session/route.ts`.)

---

## Step 5 - Create the React provider

The **provider** is one component that wraps your whole app and gives every page access to BuildBase (the logged-in user, their workspace, etc.). You write **one** provider; the SDK builds everything underneath it for you.

Create `src/components/saas-provider.tsx`. The `'use client'` line at the top tells Next.js this code runs in the browser: required, because the SDK's hooks only work there, and a server component cannot pass the callback functions below as props.

```tsx
// src/components/saas-provider.tsx
'use client';

import '@buildbase/sdk/css';

import { ApiVersion } from '@buildbase/sdk';
import { KeylessPrompt, SaaSOSProvider } from '@buildbase/sdk/react';

// Until the env is filled in there is no organization to connect to, so the
// app renders without BuildBase instead of throwing on the first page.
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
          // Who is signed in? Answered by Step 4's session route from the cookie.
          getSession: async () => {
            const res = await fetch('/api/auth/session');
            return ((await res.json()) as { sessionId: string | null }).sessionId;
          },
          // The SDK calls this automatically with the ?code from the login redirect.
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
            // The platform's reason, such as "Invalid client secret", in the error.
            if (!res.ok || !body.sessionId) {
              throw new Error(`Sign-in failed (${res.status}): ${body.message ?? 'no session'}`);
            }
            return { sessionId: body.sessionId };
          },
          // The SDK calls this on sign-out. The JSON header is what
          // refuseCrossSiteAuthPost in the signout route checks for.
          onSignOut: async () => {
            await fetch('/api/auth/signout', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
            });
          },
        },
      }}
    >
      {children}
      {/* Keyless development only (withBuildBaseKeyless from @buildbase/sdk/keyless):
          where to claim the temporary organization. Without
          NEXT_PUBLIC_BUILDBASE_KEYLESS it renders nothing. */}
      <KeylessPrompt config={process.env.NEXT_PUBLIC_BUILDBASE_KEYLESS} />
    </SaaSOSProvider>
  );
}
```

**Wait, why do `serverUrl` and `orgId` appear here AND in Step 3?** Because there are two separate worlds: your **server** code (Step 3) and your **browser** code (here). Each needs its own copy of the public config. That's expected, not a mistake.

**`BuildBaseProvider`** is the same component as `SaaSOSProvider` under its brand name, with the same props (`BuildBaseProviderProps`). New code may use either; `init` writes `SaaSOSProvider`.

✅ **Check:** No TypeScript errors. Note where each import comes from: `ApiVersion` from the root entry `@buildbase/sdk`, the provider from `@buildbase/sdk/react`. `version` is required and typed as the `ApiVersion` enum: a bare `"v1"` passes at runtime but fails `tsc`. Import `ApiVersion` from the root entry everywhere, and always in a **server** file such as a layout: `@buildbase/sdk/react` is a `"use client"` boundary, and a server layout that reads an enum from it fails `next build`.

---

## Step 6 - Wrap your app and import the CSS

Open your root layout `src/app/layout.tsx`. You need to do two things: **import the SDK's CSS** and **wrap your app in the provider**. If `create-next-app` gave you a layout with fonts/metadata, keep that; just add the two BuildBase lines (the CSS import and the `<SaaSProvider>` wrapper). This is the edit `init` makes.

```tsx
// src/app/layout.tsx
import { SaaSProvider } from '@/components/saas-provider';
import '@buildbase/sdk/css'; // REQUIRED: without it, SDK components are invisible/unstyled

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

**Why the CSS import is non-negotiable:** the SDK's built-in screens (the pricing pages, settings dialogs, the workspace switcher) are styled with this CSS. Forget it and they render as invisible or broken: the #1 "it's not working" cause. (`init` imports it in both the layout and the provider; once is enough, twice is harmless.)

✅ **Check:** App still compiles and the homepage still loads at http://localhost:3000.

---

## Step 7 - Add a sign-in page and confirm it works

Replace the contents of `src/app/page.tsx` with this test page:

```tsx
// src/app/page.tsx
'use client';

import { useSaaSAuth, WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';

export default function Home() {
  const { user, signIn, signOut, isLoading, isSessionUnverified } = useSaaSAuth();

  // On page load the SDK restores the session in the background. Until it has
  // an answer nobody is "signed out" yet, so show a neutral state, not a Sign In button.
  if (isLoading) {
    return (
      <main style={{ padding: 40 }}>
        {isSessionUnverified ? 'Cannot reach the server. Retrying...' : 'Checking your session...'}
      </main>
    );
  }

  return (
    <main style={{ padding: 40 }}>
      {/* Shown only when NOT logged in */}
      <WhenUnauthenticated>
        <h1>Welcome</h1>
        <button onClick={() => signIn()}>Sign In</button>
      </WhenUnauthenticated>

      {/* Shown only when logged in */}
      <WhenAuthenticated>
        <h1>Hello, {user?.name ?? 'there'}!</h1>
        <button onClick={() => signOut()}>Sign Out</button>
      </WhenAuthenticated>
    </main>
  );
}
```

`WhenAuthenticated` and `WhenUnauthenticated` are **gates**: components that show their contents only when a condition is true. (More on gates and their hidden third state below.) Write `onClick={() => signIn()}`, not `onClick={signIn}`: `signIn` takes an optional return URL, and passing it straight to `onClick` hands it the click event instead, which TypeScript rejects. `signIn('/dashboard')` sends the user to `/dashboard` after they sign in; with no argument they come back to the page they were on.

> **Prefer a dedicated `/callback` page?** Set `NEXT_PUBLIC_BUILDBASE_REDIRECT_URL=http://localhost:3000/callback`, allow-list that exact URL on the client, and add a page there. It needs no parsing and no redirect of its own: the provider reads the code, and the SDK then sends the user back to the page where they pressed Sign In.
>
> ```tsx
> // src/app/callback/page.tsx
> import Link from 'next/link';
> import { WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';
>
> export default function CallbackPage() {
>   return (
>     <main style={{ padding: 40 }}>
>       <WhenAuthenticated loadingComponent={<p>Signing you in...</p>}>
>         <Link href="/">Continue</Link>
>       </WhenAuthenticated>
>       <WhenUnauthenticated>
>         <p>
>           Sign-in did not finish. <Link href="/">Back to the home page</Link>
>         </p>
>       </WhenUnauthenticated>
>     </main>
>   );
> }
> ```
>
> It needs no `'use client'`: it calls no hook and passes no function, and the SDK's components are client components already.

✅ **The moment of truth.** Run `npm run dev`, open http://localhost:3000:
1. You should see "Welcome" and a **Sign In** button (after a brief "Checking your session...").
2. Click it: you're redirected to the BuildBase sign-in page.
3. Log in: BuildBase sends you back, and the page shows **"Hello, &lt;your name&gt;!"**.
4. **Refresh the page: you stay logged in.** That's the cookie and the session route doing their job.

If that worked, **you've integrated BuildBase.** Everything else (billing, feature flags, quotas) builds on this exact foundation.

---

## Step 8 - The webhook route

Sign-in works. The last piece of the foundation is the route BuildBase calls *you* on: when a payment fails, a subscription changes, a member joins. Without it your app only learns about these things when a user happens to reload a page.

In the console, open **Settings**, then **Webhooks** under **Configuration**, and press **Create webhook**. Set its **Endpoint URL** to `https://<your-domain>/api/webhooks/buildbase`, tick the events you care about, press **Create**, and copy its **signing secret** (shown once). Production takes only an `https` URL; a development or staging environment also takes `http://` or a tunnel (such as ngrok) to your machine. Paste the secret into `.env.local`, server-side only, with no `NEXT_PUBLIC_` prefix:

```env
# Server-side only. Signs every webhook BuildBase sends you.
BUILDBASE_WEBHOOK_SECRET=
```

Then create `src/app/api/webhooks/buildbase/route.ts`. Three rules the code follows: read the body as **raw text** (the signature covers the exact bytes, so `request.json()` would break it), switch only on event names that exist, and handle each event once. The full list of names is in [webhook-events.json](../http-api/webhook-events.json), rendered in [webhooks.md](../http-api/webhooks.md#event-catalog). A failed payment is `payment.failed`.

```ts
// src/app/api/webhooks/buildbase/route.ts
// Verify against the raw body, never parsed JSON. Event names come from the
// platform catalog (WEBHOOK_EVENTS from @buildbase/sdk). Do not invent one:
// a name the server never sends is a handler that never runs.
import { isWebhookEvent, parseWebhookEvent } from '@buildbase/sdk';

export async function POST(request: Request) {
  // Raw text, not request.json(): the signature is over these exact bytes.
  const body = await request.text();

  // Verifies the HMAC signature and the 5-minute timestamp window, then parses.
  // Returns null when anything is off, so an unsigned request never reaches the switch.
  const event = parseWebhookEvent({
    body,
    signature: request.headers.get('x-buildbase-signature'),
    timestamp: request.headers.get('x-buildbase-timestamp'),
    secret: process.env.BUILDBASE_WEBHOOK_SECRET ?? '',
  });
  if (!event) return Response.json({ error: 'invalid_signature' }, { status: 401 });
  if (!isWebhookEvent(event.event)) return Response.json({ ignored: event.event });
  // event.id (also the x-buildbase-event-id header) is the same on every retry:
  // record the ids you handle and skip a repeat before any side effect.

  switch (event.event) {
    case 'payment.failed': {
      // data: workspaceId, subscriptionId, invoiceId, dunningState ('notified' |
      // 'warning' | 'final'), amount (minor units), currency, failedAt,
      // nextRetryAt (ISO 8601 or null). This handler is for YOUR side effects:
      // flag the workspace in your DB, pause a job, tell your team.
      break;
    }
    case 'subscription.suspended': {
      // The last failed attempt: the subscription is now suspended.
      break;
    }
    default:
      // Unknown to this app: acknowledge so BuildBase does not retry it.
      break;
  }
  return Response.json({ received: true });
}
```

**Why no email here?** A failed-payment email is a *lifecycle* email, and BuildBase sends it already when the console's notification for `payment.failed` (with the `payment-failed` template) or a workflow on that event is on. Adding Resend or another email vendor here would send the customer two emails. Your handler's job is what only your app can do.

> **Deduplicate on `event.id`.** Each event has an `id` starting `evt_`, the same on every endpoint and every retry, and also sent as the `x-buildbase-event-id` header. Store the ids you have handled (a unique index works) and skip a repeat. `id` is optional in the type: a delivery from a platform release older than event ids has none, so fall back to a hash of the raw body when it is missing.
>
> **Standard Webhooks.** Deliveries also carry the Standard Webhooks headers (`webhook-id`, `webhook-timestamp`, `webhook-signature`), signed with the same secret. `verifyStandardWebhook` / `parseStandardWebhookEvent` from `@buildbase/sdk` check them; when `webhook-signature` is absent (an older platform), use `parseWebhookEvent` as above.

✅ **Check:** With `npm run dev` running, `curl -X POST http://localhost:3000/api/webhooks/buildbase -d '{}'` returns `401 {"error":"invalid_signature"}`: the route exists and rejects an unsigned body. Then, with the endpoint pointing at your deployed app (or a tunnel), make an event happen (signing in as a test user sends `user.logged_in` if the endpoint subscribes to it) and press **Logs** on the endpoint's row: the delivery reads **OK** when your route answered `2xx`.

---

## One concept to carry forward: gates have THREE states

This trips up everyone, so learn it now. A gate like `<WhenAuthenticated>` doesn't just show/hide; it has three states:

1. **Loading**: the SDK is still checking. The gate renders **nothing** (or a `loadingComponent` if you give it one).
2. **Condition met**: renders its children.
3. **Condition not met**: renders nothing (or a `fallbackComponent`).

So if a gate "shows nothing," it's almost always **still loading** or a **console config is missing**, not a bug. Add a `loadingComponent` to see the difference:

```tsx
<WhenAuthenticated loadingComponent={<p>Checking your session...</p>}>
  <Dashboard />
</WhenAuthenticated>
```

**Session restore follows the same rule.** The provider renders your app while it restores a stored session on page load; its full-screen overlay shows only mid sign-in (a `?code=` in the URL) and while sending the user to the hosted pages (`fullScreenLoader={false}` turns it off, `loadingComponent` restyles it). So in your own code:

- **Gate on `useSaaSAuth().isLoading`.** While it is `true`, `isAuthenticated` is `false` but the user is *not* signed out. Do not redirect to a login page or call `signIn()` yet.
- **`isSessionUnverified: true`** means a session is stored but the API could not be reached to confirm it (offline, a timeout, a 5xx or a 429). The SDK keeps the session and retries until the API answers. Show "can't reach the server", never a sign-in prompt, and never sign the user out yourself.
- A session ends only when the API refuses it (a 401, 403 or 404 on the profile check), and then `onSessionExpired('expired')` is called. A company's access refusal (`isAccessRefused`) keeps the session.

---

## If something didn't work

| What you see | Most likely cause |
|---|---|
| App crashes with `Invalid orgId: "..." Must be a valid MongoDB ObjectId` | `orgId` isn't exactly 24 hex characters: check for quotes/spaces in `.env.local`, and that you used the ID, not the org name |
| App renders but BuildBase does nothing, no sign-in | An env value is empty: the provider renders your app without BuildBase until org id, client id and redirect URL are all set. Fill them in and restart `npm run dev` |
| Server call throws `BuildBase: orgId is required, and BuildBase({ orgId }) was given an empty value` | `NEXT_PUBLIC_BUILDBASE_ORG_ID` is empty on the server: fill it in and restart |
| "Invalid redirect URL" on the BuildBase sign-in page | Your `redirectUrl` isn't on the client's **Redirect URLs**, or doesn't match it exactly |
| "This app has no sign-in methods yet." | No sign-in method added on the **Methods** tab, or not ticked on the client |
| Sign-in code or magic link never arrives | No email sender connected (**Messaging** > **Sender accounts**) |
| Back from sign-in but not logged in; console shows `Sign-in failed (401): Invalid client secret` | `BUILDBASE_CLIENT_SECRET` is wrong or empty. Regenerate it on the client if lost |
| `/api/auth/token` or `/api/auth/signout` answers `415` or `403` | `refuseCrossSiteAuthPost` refused it: the request was not `Content-Type: application/json` (send the header on sign-out too), or came from another origin |
| Logged in but page shows nothing | CSS not imported, or you're seeing a gate's loading state: add a `loadingComponent` |
| Logged out on refresh | The token and session routes use different cookie names: both must import `SESSION_COOKIE_NAME` from `@/lib/buildbase` |
| `next build` fails importing `ApiVersion` in a layout | Import `ApiVersion` from `@buildbase/sdk`, not `@buildbase/sdk/react` (a `"use client"` boundary) |
| `Module not found: '@/lib/buildbase'` | The `@/` alias isn't set up: check `tsconfig.json` has `"paths": { "@/*": ["./src/*"] }` |
| Env changes seem ignored | You didn't restart `npm run dev` after editing `.env.local` |

For a deeper list, see [common-errors.md](../troubleshooting/common-errors.md) and [top-mistakes.md](../failure-library/top-mistakes.md).

---

## What's next

- **Protect more pages**: use `WhenAuthenticated` anywhere, or check `useSaaSAuth().isAuthenticated` (once `isLoading` is `false`) in code
- **Add billing**: [billing.md](./billing.md) (needs Stripe and plans set up in the console first)
- **Handle more webhook events**: [server-side.md](./server-side.md#webhook-verification) and the catalog in [webhooks.md](../http-api/webhooks.md#event-catalog)
- **Feature flags**: [feature-flags.md](./feature-flags.md)
- **Metered usage / quotas**: [quota-usage.md](./quota-usage.md)
- **Make the app agent-ready** (its own MCP server for its users' agents): [mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md)
- **The full milestone-by-milestone path**: [beginner-path.md](../learning/beginner-path.md)
- **Complete production wiring (every file, including advanced bits)**: [nextjs-integration.md](../patterns/nextjs-integration.md)
