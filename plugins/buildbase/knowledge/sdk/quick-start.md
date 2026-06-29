# Quick Start — From Zero to Signed In

This is the **golden path**: follow it top to bottom and you'll go from an empty folder to a working app where a user can sign in. Every file is shown in full. Every step tells you what it does and how to check it worked. You can paste most of it as-is.

> **This guide assumes Next.js (App Router) with TypeScript.** That's what the official Buildbase starter uses. If you're on a different framework (Vite, Create React App, plain Express), the *ideas* are the same but the file paths differ — ask for framework-specific help before pasting.
>
> **Prefer plain JavaScript?** You can. Use `.js`/`.jsx` instead of `.ts`/`.tsx` and delete the TypeScript bits — the `: Type` annotations (like `{ children }: { children: React.ReactNode }`) and the `!` after env vars. Everything else is identical.

## Contents

- [What you're about to build (the 30-second mental picture)](#what-youre-about-to-build-the-30-second-mental-picture) — what Buildbase does for you
- [How signing in actually works](#how-signing-in-actually-works-read-this-once--it-makes-everything-click) — the end-to-end login flow
- [Before you start — collect your credentials](#before-you-start--collect-your-credentials) — the five dashboard values you need
- [Step 0 — Create the project](#step-0--create-the-project-skip-if-you-already-have-one) — scaffold a Next.js app
- [Step 1 — Install the SDK](#step-1--install-the-sdk) — add `@buildbase/sdk`
- [Step 2 — Add your credentials as environment variables](#step-2--add-your-credentials-as-environment-variables) — set up `.env.local`
- [Step 3 — Create the server-side "factory"](#step-3--create-the-server-side-factory) — configure `src/lib/buildbase.ts`
- [Step 4 — Create the three auth endpoints](#step-4--create-the-three-auth-endpoints) — token, session, signout routes
- [Step 5 — Create the React provider](#step-5--create-the-react-provider) — wrap your app with `SaaSOSProvider`
- [Step 6 — Wrap your app and import the CSS](#step-6--wrap-your-app-and-import-the-css) — root layout setup
- [Step 7 — Add a sign-in page and confirm it works](#step-7--add-a-sign-in-page-and-confirm-it-works) — test the full login flow
- [One concept to carry forward: gates have THREE states](#one-concept-to-carry-forward-gates-have-three-states) — loading vs met vs not-met
- [If something didn't work](#if-something-didnt-work) — symptom-to-cause troubleshooting table
- [What's next](#whats-next) — billing, feature flags, quotas, deeper guides

---

## What you're about to build (the 30-second mental picture)

Buildbase is a service that handles the boring-but-hard parts of a SaaS app for you: **logging users in, billing them, and tracking what they're allowed to do.** Think of it like hiring a security company for your building — they handle the locks, the membership cards, and the billing desk, so you just build the actual shop inside.

To connect your app to that service, you need to do two things:
1. **Tell Buildbase who your app is** (some credentials you copy from the Buildbase dashboard).
2. **Wire up sign-in** (a few small files that pass login info safely between your app, your server, and Buildbase).

That's it. The rest of the SDK (billing, feature flags, etc.) builds on top of this foundation.

---

## How signing in actually works (read this once — it makes everything click)

When you understand the flow, the files below stop looking like random rituals:

```
1. User clicks "Sign In"  →  the SDK sends them to Buildbase's login page
2. User logs in on Buildbase  →  Buildbase sends them BACK to your app
                                  with a one-time "code" in the URL (?code=...)
3. The SDK automatically reads that code  →  hands it to your /api/auth/token route
4. Your route trades the code (using your secret key) for a "sessionId"
                                  →  stores it in a secure cookie
5. From now on, the user is logged in. On every refresh, the SDK reads the cookie back.
```

Two things worth knowing:
- **You don't write any code to read the `code` from the URL** — the SDK does that automatically when the provider loads. You only need the page Buildbase redirects back to (your `redirectUrl`) to be wrapped by your `SaaSOSProvider`. Since the provider lives in your root layout (Step 6), every page qualifies — including the small `/callback` page you'll add in Step 7.
- A **`sessionId`** is just Buildbase's word for "proof this user is logged in." You keep it in a cookie so it survives page refreshes.

---

## Before you start — collect your credentials

**Don't have a Buildbase account yet?** Sign up and log in at **[console.buildbase.app](https://console.buildbase.app)** — that's the **dashboard**, where you create and manage everything (your org, OAuth apps, plans, features). Official docs live at **[docs.buildbase.app](https://docs.buildbase.app)**. (Note: the dashboard is a *different* address from the `serverUrl` you'll copy below — `serverUrl` is the API your app talks to, not a site you log into.)

Once you're in the dashboard, find these five values. Keep them somewhere handy — you'll paste them into a file in Step 2.

| Value | What it is | Where to look |
|------|------------|---------------|
| `serverUrl` | The Buildbase API your app talks to | **It's a fixed value: `https://api.console.buildbase.app`** (unless you self-host) |
| `orgId` | Your organization's unique ID — a **24-character hex string** like `507f1f77bcf86cd799439011` (not a name!) | Settings → General |
| `clientId` | Public ID for your app's login | Settings → OAuth |
| `clientSecret` | **Secret** key for your app's login — like a password. Never goes in the browser. | Settings → OAuth (same OAuth app) |
| `redirectUrl` | Where Buildbase sends users back after login. For local dev: `http://localhost:3000/callback` | You set this yourself, then allow-list it (below) |

> **Two things beginners miss in the dashboard:**
> 1. You must **create an OAuth App** first (Settings → OAuth) and **enable at least one login method** (Email/Password, Magic Link, Google, LinkedIn, or API Tokens). An empty OAuth list means there's nothing to copy yet, and no enabled method means the login page will have no way to sign in.
> 2. Add your `redirectUrl` to **Settings → OAuth → Redirect URLs**, or login fails with a "redirect mismatch" error. The official docs use `http://localhost:3000/callback` — whatever you pick, the value in your code must match the allow-listed URL exactly.

---

## Step 0 — Create the project (skip if you already have one)

If you don't already have a Next.js app, create one. This exact command sets up everything this guide assumes (TypeScript, App Router, the `src/` folder, and the `@/` import shortcut):

```bash
npx create-next-app@latest my-app --typescript --app --src-dir --import-alias "@/*"
cd my-app
```

When prompted, the defaults are fine. The `@/` import alias it sets up is what makes `import { x } from '@/lib/buildbase'` work — it's a shortcut for "the `src/` folder."

✅ **Check:** `npm run dev`, open http://localhost:3000 — you should see the default Next.js welcome page.

---

## Step 1 — Install the SDK

```bash
npm install @buildbase/sdk
```

The SDK needs React to run but doesn't bundle its own (so it can't clash with yours). `create-next-app` already installed React 19, which is what we want. The SDK works with React 18 or 19.

✅ **Check:** `npm ls @buildbase/sdk` prints a version with no errors.

---

## Step 2 — Add your credentials as environment variables

Create a file named exactly `.env.local` in your **project root** (the same folder as `package.json`). Paste this and fill in the values you collected:

```env
# Safe to expose to the browser (that's what NEXT_PUBLIC_ means):
NEXT_PUBLIC_BUILDBASE_SERVER_URL=https://api.console.buildbase.app
NEXT_PUBLIC_BUILDBASE_ORG_ID=your-24-char-hex-org-id
NEXT_PUBLIC_BUILDBASE_CLIENT_ID=your-client-id
NEXT_PUBLIC_BUILDBASE_REDIRECT_URL=http://localhost:3000/callback

# SECRET — server-side only. NEVER add NEXT_PUBLIC_ to this one:
BUILDBASE_CLIENT_SECRET=your-client-secret
```

**Why the `NEXT_PUBLIC_` prefix matters:** In Next.js, any variable starting with `NEXT_PUBLIC_` gets shipped to the browser where anyone can read it. That's fine for the public IDs — but the **`clientSecret` must never have that prefix**, or you'd be handing your password to every visitor.

`create-next-app` already tells git to ignore `.env.local`, so your secrets won't be committed.

✅ **Check:** After creating or editing `.env.local`, **restart `npm run dev`** — environment changes don't hot-reload.

---

## Step 3 — Create the server-side "factory"

Create `src/lib/buildbase.ts`. A **factory** here just means "a function you call once that hands you back a set of ready-to-use tools." You configure Buildbase once, and get back tools (`auth`, `workspace`, `subscription`, …) you'll use in your server code.

```ts
// src/lib/buildbase.ts
import BuildBase from '@buildbase/sdk';
import { cookies } from 'next/headers';

// The name of the cookie we store the login in. Used in several files,
// so we define it once here and import it everywhere else.
export const SESSION_COOKIE_NAME = 'bb-session-id';

export const {
  auth, workspace, subscription, users, plans,
  usage, credits, features, settings, notification, withSession,
} = BuildBase({
  serverUrl: process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL!,
  orgId: process.env.NEXT_PUBLIC_BUILDBASE_ORG_ID!,
  // The SDK calls this whenever it needs to know the current user's session.
  // We read it from the secure cookie.
  getSessionId: async () => {
    const c = await cookies();
    return c.get(SESSION_COOKIE_NAME)?.value ?? null;
  },
});
```

**About that big `export const { ... } =`:** this is "destructuring" — it pulls many tools out of one function call and exports them all at once. You won't use most of them today; exporting them now just saves you editing this file later. Paste it as-is.

✅ **Check:** No red squiggles / no TypeScript errors in this file. (It won't *do* anything yet — that's expected.)

---

## Step 4 — Create the three auth endpoints

These three small server routes are the secure middlemen between your app and Buildbase. In Next.js App Router, a file at `src/app/api/auth/token/route.ts` automatically becomes the URL `/api/auth/token` — **the folder path is the URL.**

### `src/app/api/auth/token/route.ts` — trade the login code for a session

This is the only file that touches your secret. It runs on the server, where the secret is safe.

```ts
// src/app/api/auth/token/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST(request: NextRequest) {
  const { code } = await request.json();

  // Trade the one-time code (from the login redirect) for a real session.
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BUILDBASE_SERVER_URL}/api/v1/auth/token`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        clientId: process.env.NEXT_PUBLIC_BUILDBASE_CLIENT_ID,
        clientSecret: process.env.BUILDBASE_CLIENT_SECRET, // safe: server-side only
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
  // Store the session in an httpOnly cookie: a cookie your browser JavaScript
  // CANNOT read, so a script-injection attack can't steal the user's session.
  response.cookies.set(SESSION_COOKIE_NAME, data.sessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production', // https-only in production
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 7, // keep the user logged in for 7 days
  });
  return response;
}
```

### `src/app/api/auth/session/route.ts` — restore the session on refresh

The SDK calls this on every page load to check "is anyone logged in?"

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

### `src/app/api/auth/signout/route.ts` — log out

```ts
// src/app/api/auth/signout/route.ts
import { NextResponse } from 'next/server';
import { SESSION_COOKIE_NAME } from '@/lib/buildbase';

export async function POST() {
  const response = NextResponse.json({ success: true });
  // Setting maxAge: 0 deletes the cookie.
  response.cookies.set(SESSION_COOKIE_NAME, '', {
    httpOnly: true, secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax', path: '/', maxAge: 0,
  });
  return response;
}
```

✅ **Check:** Visit http://localhost:3000/api/auth/session in your browser. You should see `{"sessionId":null}` — that means the route works and nobody's logged in yet. (If you get a 404, the file path is wrong; it must be exactly `src/app/api/auth/session/route.ts`.)

---

## Step 5 — Create the React provider

The **provider** is one component that wraps your whole app and gives every page access to Buildbase (the logged-in user, their workspace, etc.). You write **one** provider — the SDK builds everything underneath it for you.

Create `src/components/saas-provider.tsx`. The `'use client'` line at the top tells Next.js this code runs in the browser — required, because the SDK's hooks only work there.

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
          // The SDK calls this to check who's logged in (hits Step 4's session route).
          getSession: async () => {
            const res = await fetch('/api/auth/session');
            return (await res.json()).sessionId ?? null;
          },
          // The SDK calls this automatically with the ?code from the login redirect.
          handleAuthentication: async (code) => {
            const res = await fetch('/api/auth/token', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ code }),
            });
            return { sessionId: (await res.json()).sessionId };
          },
          // The SDK calls this on sign-out.
          onSignOut: async () => {
            await fetch('/api/auth/signout', { method: 'POST' });
          },
        },
      }}
    >
      {children}
    </SaaSOSProvider>
  );
}
```

**Wait, why do `serverUrl` and `orgId` appear here AND in Step 3?** Because there are two separate worlds: your **server** code (Step 3) and your **browser** code (here). Each needs its own copy of the public config. That's expected, not a mistake.

✅ **Check:** No TypeScript errors. (`version={ApiVersion.V1}` — note `ApiVersion` is a named import from `@buildbase/sdk`, while `BuildBase` in Step 3 was the default import. Both come from the same package.)

---

## Step 6 — Wrap your app and import the CSS

Open your root layout `src/app/layout.tsx`. You need to do two things: **import the SDK's CSS** and **wrap your app in the provider**. If `create-next-app` gave you a layout with fonts/metadata, keep that — just add the two Buildbase lines (the CSS import and the `<SaaSProvider>` wrapper).

```tsx
// src/app/layout.tsx
import { SaaSProvider } from '@/components/saas-provider';
import '@buildbase/sdk/css'; // REQUIRED — without this, SDK components are invisible/unstyled

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

**Why the CSS import is non-negotiable:** the SDK's built-in screens (the login modal, pricing pages, settings dialogs) are styled with this CSS. Forget it and they render as invisible or broken — the #1 "it's not working" cause.

✅ **Check:** App still compiles and the homepage still loads at http://localhost:3000.

---

## Step 7 — Add a sign-in page and confirm it works

Replace the contents of `src/app/page.tsx` with this test page:

```tsx
// src/app/page.tsx
'use client';

import { useSaaSAuth, WhenAuthenticated, WhenUnauthenticated } from '@buildbase/sdk/react';

export default function Home() {
  const { user, signIn, signOut } = useSaaSAuth();

  return (
    <main style={{ padding: 40 }}>
      {/* Shown only when NOT logged in */}
      <WhenUnauthenticated>
        <h1>Welcome 👋</h1>
        <button onClick={() => signIn()}>Sign In</button>
      </WhenUnauthenticated>

      {/* Shown only when logged in */}
      <WhenAuthenticated>
        <h1>Hello, {user?.name ?? 'there'}! 🎉</h1>
        <button onClick={() => signOut()}>Sign Out</button>
      </WhenAuthenticated>
    </main>
  );
}
```

`WhenAuthenticated` and `WhenUnauthenticated` are **gates** — components that show their contents only when a condition is true. (More on gates and their hidden third state below.)

Now add the **callback page** — the page Buildbase redirects back to (your `redirectUrl` ends in `/callback`). You don't parse anything here; the provider does that automatically. This page just needs to exist and show something while the SDK finishes logging the user in, then send them home:

```tsx
// src/app/callback/page.tsx
'use client';

import { useEffect } from 'react';
import { useSaaSAuth } from '@buildbase/sdk/react';
import { useRouter } from 'next/navigation';

export default function Callback() {
  const { isAuthenticated } = useSaaSAuth();
  const router = useRouter();

  // Once the SDK has read the ?code and logged the user in, go home.
  useEffect(() => {
    if (isAuthenticated) router.replace('/');
  }, [isAuthenticated, router]);

  return <p style={{ padding: 40 }}>Signing you in…</p>;
}
```

> If you'd rather keep things to a single page, you can instead set your `redirectUrl` to `http://localhost:3000` (no `/callback`) and skip this file — the homepage is wrapped by the provider too, so the code still gets read. Just make sure the `redirectUrl` in your code matches the URL you allow-listed in the dashboard.

✅ **The moment of truth.** Run `npm run dev`, open http://localhost:3000:
1. You should see "Welcome 👋" and a **Sign In** button.
2. Click it → you're redirected to the Buildbase login page.
3. Log in → Buildbase sends you to `/callback` ("Signing you in…"), which then drops you home showing **"Hello, &lt;your name&gt;! 🎉"**.

If that worked — **you've integrated Buildbase.** Everything else (billing, feature flags, quotas) builds on this exact foundation.

---

## One concept to carry forward: gates have THREE states

This trips up everyone, so learn it now. A gate like `<WhenAuthenticated>` doesn't just show/hide — it has three states:

1. **Loading** — the SDK is still checking. The gate renders **nothing** (or a `loadingComponent` if you give it one).
2. **Condition met** — renders its children.
3. **Condition not met** — renders nothing (or a `fallbackComponent`).

So if a gate "shows nothing," it's almost always **still loading** or a **dashboard config is missing** — not a bug. Add a `loadingComponent` to see the difference:

```tsx
<WhenAuthenticated loadingComponent={<p>Checking your session…</p>}>
  <Dashboard />
</WhenAuthenticated>
```

---

## If something didn't work

| What you see | Most likely cause |
|---|---|
| App crashes on start with "Invalid orgId" | `orgId` isn't exactly 24 hex characters — check for quotes/spaces in `.env.local`, and that you used the ID, not the org name |
| Sign In does nothing / redirect error | Your `redirectUrl` isn't allow-listed under Settings → OAuth → Redirect URLs, or the code value doesn't match it exactly |
| Redirected to Buildbase but no login options | No login method enabled on the OAuth App in the dashboard |
| Logged in but page shows nothing | CSS not imported, or you're seeing the gate's loading state — add a `loadingComponent` |
| `Module not found: '@/lib/buildbase'` | The `@/` alias isn't set up — check `tsconfig.json` has `"paths": { "@/*": ["./src/*"] }` |
| Env changes seem ignored | You didn't restart `npm run dev` after editing `.env.local` |

For a deeper list, see [common-errors.md](../troubleshooting/common-errors.md) and [top-mistakes.md](../failure-library/top-mistakes.md).

---

## What's next

- **Protect more pages** → use `WhenAuthenticated` anywhere, or check `useSaaSAuth().isAuthenticated` in code
- **Add billing** → [billing.md](./billing.md) (needs plans set up in the dashboard first)
- **Feature flags** → [feature-flags.md](./feature-flags.md)
- **Metered usage / quotas** → [quota-usage.md](./quota-usage.md)
- **The full milestone-by-milestone path** → [beginner-path.md](../learning/beginner-path.md)
- **Complete production wiring (every file, including advanced bits)** → [nextjs-integration.md](../patterns/nextjs-integration.md)
