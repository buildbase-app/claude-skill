# Building a whole app with an agent driving

For when someone says "build me a SaaS with BuildBase" and expects the agent to do the work. This is the order that produces a working app, and the three points where the agent cannot proceed alone.

Read [../sdk/quick-start.md](../sdk/quick-start.md) for the file-by-file auth wiring; this page is the arc around it, and the judgment calls.

## The three things a coding agent gets wrong here

1. **Rebuilding UI that ships.** 13 settings screens, a workspace switcher, a pricing page and a credit store already exist. Read [../sdk/pre-built-ui.md](../sdk/pre-built-ui.md) before writing any account, billing or members screen.
2. **Inventing hooks for modules that have none.** Eight of twenty modules have no React surface. Check [../product/module-map.md](../product/module-map.md) before reaching for `useCollections`.
3. **Writing code for things only a human can do in the console.** Plans, slugs, credentials and OAuth redirect URLs are console work. Code that references a slug which does not exist fails silently, so the agent appears to succeed and the app quietly does nothing.

## The order

Each step is testable before the next. Do not batch them; an agent that writes all seven at once cannot tell you which one broke.

**0. Decide the shape.** B2B with teams, or B2C where each user is their own workspace? That sets Platform or Personal mode in the console, and it is awkward to change later. Ask if it is not obvious from what they described.

**1. Human: create the org and OAuth app.** They need `serverUrl`, `orgId`, `clientId`, `clientSecret`, `redirectUrl`, and at least one enabled login method with the redirect URL allow-listed. The agent cannot do this. Stop and hand back a numbered list.

**2. Scaffold and install.** `npx create-next-app@latest` with TypeScript, App Router, `src/`, and the `@/*` alias, then `npm install @buildbase/sdk`. Verify the app runs before touching BuildBase.

**3. Auth, end to end.** The factory, three auth routes, the provider, the CSS import, one gate. Per [../sdk/quick-start.md](../sdk/quick-start.md). **Stop here and have a human sign in.** Every later step assumes a real session; debugging billing on top of broken auth wastes hours.

**4. Mount what already exists.** A settings button, the workspace switcher, and upgrade entry points. This is where an app stops looking like a scaffold, and it is roughly fifteen lines.

```tsx
const { openWorkspaceSettings, openPlanPicker } = useSaaSAuth();
```

**5. Human: configure billing.** Stripe under Billing then Credentials, a plan, a **published** plan version, a pricing group. Then `<PricingPage slug="...">` renders and `selectPlan` works. Skip the publish step and the page is empty with no error.

**6. Gate the product on entitlement.** Subscription, feature, quota and credit gates around the features that should be paid. Record usage server-side, not in the browser, for anything that bills.

**7. Make it agent-ready, if they want that.** `createAgentStack` and the `mcp` prop, per [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md). This is what lets their customers point Claude or Cursor at the app they just built.

## Where the agent must stop

Three places, and they are not negotiable because no credential or cleverness substitutes for them:

| Blocked on | Why |
|---|---|
| Console configuration | Plans, slugs, credentials, redirect URLs. The API cannot create an OAuth app for the org it is authenticating against |
| A real sign-in | Needs a browser and a human identity |
| Stripe checkout | Real payment credentials and a hosted flow |

Say so plainly and give the exact clicks. An agent that fakes progress past a console step produces an app that compiles and does nothing.

## Verifying without a browser

An agent can get further than it might assume:

- `tsc --noEmit` proves the wiring compiles against the installed SDK version.
- `GET /api/v1/public/{orgId}/settings` needs no session and proves `serverUrl` and `orgId` are right.
- `GET /api/v1/public/{orgId}/plans/{slug}` proves the pricing group exists and is published, before anyone opens the page.
- For anything server-side, an org key exchanged for a session covers the whole authenticated surface without a browser. See [../http-api/using-from-any-language.md](../http-api/using-from-any-language.md).

Browser sign-in, Stripe checkout and push notifications stay human checks. List them explicitly at the end rather than implying the app is fully verified.

## What to hand back

When the build is done, the person should get: the console steps still outstanding, the human checks above, which slugs the code references so they can confirm each exists, and where the secrets live. A build that ends with "done" and no such list is not finished, it is abandoned.
