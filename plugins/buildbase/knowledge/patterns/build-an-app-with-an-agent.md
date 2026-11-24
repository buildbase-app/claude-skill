# Building a whole app with an agent driving

For when someone says "build me a SaaS with BuildBase" and expects the agent to do the work. This is the order that produces a working app, and the points where the agent cannot proceed alone.

Read [../sdk/quick-start.md](../sdk/quick-start.md) for the file-by-file auth wiring; this page is the arc around it, and the judgment calls. The installed package's own agent docs (`node_modules/@buildbase/sdk/AGENTS.md` and `agents/*.md`) are checked against its exports on every release: where they and this page disagree, the package wins.

## The three things a coding agent gets wrong here

1. **Rebuilding UI that ships.** A settings dialog with 18 sections (`SettingsScreen`), a workspace switcher, a pricing page and a credit store already exist. Read [../sdk/pre-built-ui.md](../sdk/pre-built-ui.md) before writing any account, billing or members screen.
2. **Inventing hooks for modules that have none.** Several of the twenty modules have no React surface. Check [../product/module-map.md](../product/module-map.md) before reaching for a hook like `useCollections`.
3. **Writing code for things only the console decides.** Plans, slugs, Stripe keys and published versions are console (or blueprint) work. Code that references a slug which does not exist fails silently, so the agent appears to succeed and the app quietly does nothing.

## Two MCP servers, two jobs

Keep these apart; agents mix them up.

| | BuildBase's hosted MCP server | The app's own MCP server |
|---|---|---|
| What | `https://api.console.buildbase.app/mcp`, "BuildBase Console" | Built with `@buildbase/sdk/mcp` (`createAgentStack`), served by the app at `/api/mcp` |
| Who signs in | The person, as themselves (OAuth), with their console role | The app's own end users, through the app's agent sign-in |
| What it does | Manages the person's BuildBase organizations: `list_orgs`, `console_get`, `console_write`, blueprints, `search_docs`, `get_env_template`, `create_org` | Lets the app's users' agents use the app |
| How to get it | `npx @buildbase/sdk agent setup --console`, or BuildBase in Claude's connectors directory | `npx @buildbase/sdk init --agent`; see [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md) |

When the person has connected the hosted server, the agent can read and change their organization itself, within their role and the organization's AI agents setting. Destructive changes (deletes, members, roles, webhooks, money) ask the person to approve each one. Choosing a paid plan or a trial stays the person's, in the console.

## The order

Each step is testable before the next. Do not batch them; an agent that writes all seven at once cannot tell you which one broke.

**0. Decide the shape.** B2B with teams, or B2C where each user is their own workspace? That sets Platform or Personal mode in the console, and it is awkward to change later. Ask if it is not obvious from what they described.

**1. Get an organization and an auth client.** Three ways, in order of preference:

- **The person has an account and has connected the hosted MCP server:** ask which organization (never pick one for them when they have several), say its name back before any change, and read `get_env_template` for the env values. With no organization yet, `create_org` makes one they own, after they approve it.
- **The person has an account, no MCP:** they create the org and the auth client in the console and paste the non-secret values (`orgId`, `clientId`) to you; the client secret goes into `.env.local` by their hand, never through the chat. Hand back a numbered list: organization, auth client, at least one sign-in method ticked on the client, the redirect URL allow-listed, an email sender connected.
- **No account at all:** `npx @buildbase/sdk init --claim --yes` creates a claimable organization (central's `POST /api/organizations/agent/identity`), with a sign-in client for the app's local URL, and writes the keys to `.env.local`. It prints a claim URL and code: give both to the person. **The claim is theirs** (they sign in or up on that page and type the code); never do it for them. Unclaimed, the organization is deleted after 72 hours, and until then it runs on caps (50 end users, Stripe test keys, no invitations, only sign-in and verification email). `npx @buildbase/sdk claim-code` prints a fresh code; codes last 15 minutes.

**2. Scaffold and install.** `npx create-next-app@latest` with TypeScript, App Router, `src/`, and the `@/*` alias, then `npm install @buildbase/sdk`. Verify the app runs before touching BuildBase.

**3. Auth, end to end.** `npx buildbase init --org-id <24 hex>` (or the `--claim` run above, which already did it) writes the factory, the three auth routes, the provider, the CSS import and the webhook route; [../sdk/quick-start.md](../sdk/quick-start.md) shows each file. Gate the first page on `useSaaSAuth().isLoading` (a restoring session is not a signed-out one). **Stop here and have a human sign in.** Every later step assumes a real session; debugging billing on top of broken auth wastes hours.

**4. Mount what already exists.** A settings button, the workspace switcher, and upgrade entry points. This is where an app stops looking like a scaffold, and it is roughly fifteen lines.

```tsx
const { openWorkspaceSettings, openPlanPicker } = useSaaSAuth();
```

**5. Configure billing (human, or the hosted MCP within its limits).** Stripe keys under **Billing** (it opens on Stripe payment setup until a secret key is saved), then the Stripe webhook endpoint (**Credentials**, **Check Stripe setup**), a plan with a **published** plan version, and a **published** pricing group. Then `<PricingPage slug="...">` renders and `selectPlan` works. Skip a publish step and the page is empty with no error. A blueprint plan that changes the billing catalog is refused over MCP: the person makes that change in the console.

**6. Gate the product on entitlement.** Subscription, feature, quota and credit gates around the features that should be paid. Record usage server-side, not in the browser, for anything that bills, and pass an `idempotencyKey` on `usage.record` and `credits.consume`.

**7. Make it agent-ready, if they want that.** `npx @buildbase/sdk init --agent` (or `createAgentStack` and the `mcp` prop by hand), per [../mcp/mcp-and-agent-readiness.md](../mcp/mcp-and-agent-readiness.md). This is what lets their customers point Claude or Cursor at the app they just built. Agents can sign in only after a person turns it on (the claim page's tick, or **Agent readiness** in the console).

**Development and staging.** Build against a non-production environment when the org has one: `environment` (its eight-letter key) on the provider and on `BuildBase()`, or `npx @buildbase/sdk init --dev` after `npx @buildbase/sdk login`. Unset is production. Ask the person before `env create` or `env push`.

## Where the agent must stop

These are not negotiable, because no credential or cleverness substitutes for them:

| Blocked on | Why |
|---|---|
| Claiming a claimable organization | The person signs in or up and types the code themselves |
| A real sign-in | Needs a browser and a human identity |
| Stripe checkout, choosing a paid plan or trial | Real payment credentials and a hosted flow; the person's decision |
| Console configuration with no hosted MCP and no admin key | Plans, slugs, Stripe keys, redirect URLs. A blueprint (`npx @buildbase/sdk blueprint`, or `blueprint_plan` / `blueprint_apply` on the hosted MCP) can set most of it, but `apply` is the person's to approve, and a blueprint never changes the billing catalog over MCP |
| Secrets | Never asked for in the chat; the person puts them in `.env.local` (or `init --claim` writes them) |

Say so plainly and give the exact clicks. An agent that fakes progress past a console step produces an app that compiles and does nothing.

## Verifying without a browser

An agent can get further than it might assume:

- `tsc --noEmit` proves the wiring compiles against the installed SDK version.
- `GET /api/v1/public/{orgId}/settings` needs no session and proves `serverUrl` and `orgId` are right.
- `GET /api/v1/public/{orgId}/plans/{groupSlug}` proves the pricing group exists and is published, before anyone opens the page.
- For anything server-side, an org key exchanged for a session covers the whole authenticated surface without a browser. See [../http-api/using-from-any-language.md](../http-api/using-from-any-language.md).
- Once the app's own MCP server is deployed, `npx @buildbase/sdk agent doctor --url <site>/api/mcp --site <site>` checks it the way clients and directories will.

Browser sign-in, the claim, Stripe checkout and push notifications stay human checks. List them explicitly at the end rather than implying the app is fully verified.

## What to hand back

When the build is done, the person should get: the claim link and code if the org is still unclaimed (and the 72-hour deadline), the console steps still outstanding, the human checks above, which slugs the code references so they can confirm each exists, and where the secrets live. A build that ends with "done" and no such list is not finished, it is abandoned.
