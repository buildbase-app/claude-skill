# Developer Personas

Six developer archetypes who integrate the Buildbase SDK. Understanding which persona you're talking to changes what you emphasize and what you warn against.

## Contents

- [1. Solo Founder](#1-solo-founder) — first SaaS, ship in days
- [2. Frontend Developer (Contractor)](#2-frontend-developer-contractor) — methodical, reads docs first
- [3. Full-Stack Developer](#3-full-stack-developer) — skims, copy-runs, moves on
- [4. Agency Developer](#4-agency-developer) — maintainable client handoff
- [5. Enterprise Developer](#5-enterprise-developer) — security and compliance first
- [6. Student / Hobbyist](#6-student--hobbyist) — learning, side project

---

## 1. Solo Founder

**Profile**: Building their first SaaS product alone. No dedicated engineering team. Has product instincts but limited SaaS infrastructure experience. Knows enough React to be dangerous, has never implemented billing or auth from scratch.

**Primary goal**: Ship something real within days, not weeks. Every hour not building features is a liability.

**What they'll try to skip**: Reading the auth endpoint implementation. They'll drop `SaaSOSProvider` into the root layout, see nothing break immediately, and ship — without the three required auth API routes. The app "works" until someone tries to sign in.

**Why that's dangerous**: Without the `/api/auth/token` route, the OAuth code exchange never happens. Users get redirected back with a `?code=` param but nothing processes it. The app silently fails at login. The founder discovers this at demo time.

**First question to Claude**: "How do I add Buildbase to my Next.js app? Show me the fastest way."

**What success looks like**: Users can sign up, subscribe, and use the app without the founder having built billing or auth infrastructure. The product is live and charging money within a week.

**Specific pitfalls**:
- Will store `clientSecret` in a `NEXT_PUBLIC_` env var because they're moving fast
- Will forget `import '@buildbase/sdk/css'` and spend an hour debugging why the UI looks broken
- Will try to build their own subscription check instead of using `WhenSubscription`
- Will not read about workspace modes and accidentally ship in the wrong one for their product type

---

## 2. Frontend Developer (Contractor)

**Profile**: Hired specifically to integrate Buildbase. Technically strong — knows React, TypeScript, and Next.js well. Has never used Buildbase. Will read documentation carefully before writing a line of code. Methodical.

**Primary goal**: Integrate correctly, deliver clean code, and not have to revisit this in three months because something broke.

**What they'll try to skip**: Nothing. But they'll get lost in abstraction before understanding the concrete integration pattern. They'll read about every gate component before creating a single auth endpoint.

**Why that's dangerous**: They'll understand all the leaf nodes but miss the required setup in the middle. Will know what `WhenSubscriptionToPlans` does but not realize the three auth endpoints are mandatory, not optional.

**First question to Claude**: "What's the complete list of files I need to create to integrate Buildbase? I want to understand the full picture first."

**What success looks like**: A clean, well-typed integration with all edge cases handled. PR is reviewable and another developer could understand it without asking.

**Specific pitfalls**:
- May try to implement workspace state management themselves (Redux/Zustand) instead of using `useSaaSWorkspaces`
- May over-engineer the auth layer, adding layers on top of the SDK's session system
- May miss that `onWorkspaceChange` is the right place to generate their own JWT for their own API
- Will want to understand every prop on `SaaSOSProvider` before starting, which leads to analysis paralysis

---

## 3. Full-Stack Developer

**Profile**: Experienced with Next.js, builds fast, ships often. Skims documentation. Will copy a code block, run it, and figure out what the props mean from the errors. Not afraid to experiment.

**Primary goal**: Get it working so they can move on. Time is the resource they're most protective of.

**What they'll try to skip**: The dashboard configuration step. Will assume everything is code-configurable. Will install the SDK, copy the provider setup, and then spend two hours wondering why their feature flags always return false.

**Why that's dangerous**: Feature slugs, plan slugs, and quota slugs must exist in the Buildbase dashboard first. Code that references a slug that doesn't exist in the dashboard silently does nothing. The developer will assume the SDK is broken.

**First question to Claude**: "Show me the full integration — lib/buildbase.ts, the provider, and the auth routes. I'll figure out the rest."

**What success looks like**: It's working in under two hours and they haven't had to context-switch too much.

**Specific pitfalls**:
- Uses `setCurrentWorkspace` instead of `switchToWorkspace` for user-initiated workspace changes (no callbacks fire)
- Skips the `Secure; SameSite=Lax` flags on the session cookie
- Wires up `WhenQuotaAvailable` before creating the quota on the plan in the dashboard
- Calls `BuildBase()` inside a React component or per-request function instead of as a module-level singleton

---

## 4. Agency Developer

**Profile**: Building a product for a client using Buildbase. Has done several SaaS integrations before with other tools (Auth0, Paddle, Stripe). Worried about client lock-in and maintainability. Needs to document what they built.

**Primary goal**: Deliver a maintainable, well-documented integration that the client can hand to another developer in 12 months without disaster.

**What they'll try to skip**: Using the built-in UI components (WorkspaceSwitcher, PricingPage). They'll want to build custom UI everywhere for full control. This is sometimes right — but they'll reinvent things that Buildbase already does well.

**Why that's dangerous**: The built-in components handle edge cases (loading states, error handling, trial logic) that the agency developer will miss in their custom implementation. Custom UI that looks simple gets subtle bugs in edge cases.

**First question to Claude**: "What parts of this SDK should I NOT customize? Where is the SDK opinionated and I should follow it, vs where can I build my own UI?"

**What success looks like**: Delivered on time, client can add features without the agency, codebase is legible to a new developer.

**Specific pitfalls**:
- Will try to implement a custom workspace selector without reading about `WorkspaceSwitcher`'s render-prop pattern
- May want to manage subscriptions in their own database, duplicating what Buildbase already tracks
- Will under-invest in understanding the `onWorkspaceChange` pattern, leading to stale JWT issues
- May not document which slugs were configured in the Buildbase dashboard, creating a gap for the next developer

---

## 5. Enterprise Developer

**Profile**: Works at a company with security reviews, architecture approval processes, and compliance requirements. Has been burned by third-party dependencies before. Will read the source code. Will ask about data residency, token lifetimes, and what data the SDK sends to Buildbase servers.

**Primary goal**: Understand the security model completely before writing code. Justify the integration to their security team.

**What they'll try to skip**: Nothing — but they'll slow down at every security decision point.

**Why that's dangerous**: They'll sometimes reject the recommended patterns (like httpOnly cookies) in favor of patterns they control more directly (like JWT in Authorization headers). This creates security gaps or forces them to build more infrastructure than needed.

**First question to Claude**: "What data does @buildbase/sdk send to Buildbase servers? What is the session token's security model? How is it invalidated?"

**What success looks like**: The integration is fully understood, security team approved, and they can explain every piece of it in a threat model review.

**Specific pitfalls**:
- May want to manage session tokens in their own secure store rather than httpOnly cookies (more complex, no real benefit)
- Will want to verify webhook signatures but may not know the `verifyWebhookSignature` utility exists
- May duplicate auth checks in middleware when the SDK's `auth()` call already handles it
- Will be bothered that `clientSecret` appears in an env var alongside `NEXT_PUBLIC_` vars and need explicit confirmation that it's not exposed

---

## 6. Student / Hobbyist

**Profile**: Learning to build SaaS apps. This is a side project or portfolio piece. Not production-bound. Makes mistakes, reads errors, and fixes them. Has time but limited domain knowledge.

**Primary goal**: Get something working that they can show off and learn from. Understand how real SaaS infrastructure works.

**What they'll try to skip**: The "why" behind each step. Will copy code without understanding what it does.

**Why that's dangerous**: When something breaks (and it will), they won't know where to look because they don't understand the system. Also at risk of accidentally exposing credentials in a public GitHub repo.

**First question to Claude**: "I want to build a SaaS app with auth and billing. I've heard of Buildbase. Where do I start?"

**What success looks like**: A working app that actually signs users in, shows a pricing page, and processes a test payment. Understanding what each file does.

**Specific pitfalls**:
- High risk of committing `.env.local` to a public repo with real credentials
- Will use `localhost` URLs in production redirectUrl config
- Will test with a real Stripe card number instead of the test card
- Will not understand the difference between `@buildbase/sdk` and `@buildbase/sdk/react` and import from the wrong one in Node.js routes
- May not understand workspace modes and accidentally create thousands of test workspaces in the dashboard
