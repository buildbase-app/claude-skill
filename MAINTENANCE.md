# Maintenance Guide

How to keep this skill accurate as the Buildbase SDK / API grows. The golden rule that made this skill reliable: **the SDK source is the source of truth - never document an API you haven't confirmed in code.**

## Ground-truth sources

| What | Where |
|------|-------|
| SDK package | [`@buildbase/sdk`](https://www.npmjs.com/package/@buildbase/sdk) (the npm tarball is the truth; the public mirror lags it) - verified against **v1.9.0** (2026-11-24). Check `npm view @buildbase/sdk dist-tags` first; as of 2026-11-24 `latest` is 1.9.0, so a bare `npm install` resolves the pinned version. Semver since 1.0.0: a minor release only adds. The tarball ships its own agent docs, `AGENTS.md` and `agents/*.md`, whose test fails on any name not exported: read them first, then the `.d.ts` files. Its `CHANGELOG.md` marks every behaviour change with ⚠️. Dated facts the skill still states ("since 0.0.73") are kept on purpose |
| Webhook event catalog | `plugins/buildbase/knowledge/http-api/webhook-events.json`, vendored from `packages/shared/src/constants/system-events.ts` (`ALL_SYSTEM_EVENTS`, grouped by `EVENT_CATEGORIES` in `platform-stats.ts`, headers from `WEBHOOK_HEADERS`) in the platform repo; its `source` block records the commit and date. It follows the platform, so it can hold names newer than the pinned SDK's `WEBHOOK_EVENTS` (say which in `webhooks.md`). Re-render `webhooks.md` with `python3 scripts/render-webhook-catalog.py` after refreshing it; `validate.py` fails on a stated count that differs from the JSON. The platform's `openapi/public-v1.json` (`webhooks`) has one schema per event, published at `docs.buildbase.app/http-api/reference/webhooks/<name>` |
| BuildBase's hosted MCP server | `https://api.console.buildbase.app/mcp`; its tools are `CONSOLE_MCP_TOOLS` in `packages/shared/src/constants/console-mcp-tools.ts` (20 on 2026-11-24) and the docs page `docs/content/console/ai-agents.mdx`; the public connector repo is [buildbase-app/mcp](https://github.com/buildbase-app/mcp) |
| Reference apps | [buildbase-app/nextjs-starter](https://github.com/buildbase-app/nextjs-starter) (auth wiring, token-exchange shape, React version); [buildbase-app/nextjs-agent-mcp-starter](https://github.com/buildbase-app/nextjs-agent-mcp-starter) for the MCP/agent-readiness wiring |
| Official docs | https://docs.buildbase.app - for facts not in the package. `reference/admin-api` is the source for `knowledge/http-api/org-api.md`, and `self-hosted/*` is the source for the self-host plugin's compose blocks, which are generated output and must be copied rather than paraphrased |
| Dashboard | https://console.buildbase.app |

## When the SDK version bumps

0. **Check the dist-tags first**: `npm view @buildbase/sdk dist-tags versions --json`. Pin the newest *published* version, and say in the install line when `latest` has not caught up with it, because that is the version `npm install @buildbase/sdk` will actually resolve.
1. **Re-point at the new source** and check `package.json` for the new version, exports, and peer deps.
2. **Re-verify the public surface** the skill documents:
   - Hooks/gates/components - confirm each named symbol still exists (`src/react.ts`, `src/providers/**`, `src/hooks/**`).
   - Server modules/methods - `src/lib/server-client.ts`.
   - Field shapes inside code samples (this is where drift hides - e.g. credit consume uses `amount`, not `quantity`). Check `src/api/types.ts`.
3. **Regenerate the HTTP-API catalog** (`plugins/buildbase/knowledge/http-api/`) from `src/lib/api-base.ts` + `src/api/services/*-api.ts` if endpoints changed. HTTP calls also live outside `services/`: `src/tracking/*` (tracking config, consent, checkout return), `src/lib/agent-discovery.ts` (agent readiness) and `src/lib/server-content/client.ts` (the org-token content client), plus a socket.io channel in `src/lib/inbox-socket.ts`. Diff all of them. `scripts/api-routes.txt` was last synced on 2026-11-24 (106 paths); the org API's full path list is also in the platform's `openapi/org-api.json`, served live at `/api/v1/openapi/org-api.json`.
3b. **Refresh the webhook catalog** from the platform's `SYSTEM_EVENTS` constant (regenerate `webhook-events.json`, update its `source.commit` and `source.syncedOn`, run `python3 scripts/render-webhook-catalog.py`). `validate.py` fails when the rendered section and the JSON disagree.
4. **Update `plugins/buildbase/SKILL.md`** version note and any changed validation rules (orgId format, `ApiVersion`, etc.).
5. **Bump the version** in `plugins/buildbase/.claude-plugin/plugin.json` (semver). Plugin installs pin to this; bumping it is how users get the update.

## Accuracy audit (run before every release)

Re-run the verification that caught real bugs during authoring - for each knowledge file, confirm every API symbol, code snippet, endpoint, and factual claim against the SDK source. Classify findings as HALLUCINATION / INACCURATE / UNVERIFIABLE / OK and fix the first two. The recurring drift points to watch:

- `switchToWorkspace(workspace)` takes the **object**, not an id
- credit consume uses **`amount`** (usage record uses `quantity`)
- runtime values (`AuthStatus`, pricing utils) import from `@buildbase/sdk`; since 0.0.51 `@buildbase/sdk/react` re-exports them by value too, so either import is correct
- `IWorkspace` / `IUser` / `ISettings` **are** exported by name since 0.0.53 (the older claim that they were not is itself a regression rule now)
- error codes: since 1.x the package's `docs/ERROR_CODES.md` lists exactly the codes the SDK sets, and changing one is a major release; the old vocabulary (`AUTH_REQUIRED`, `SESSION_EXPIRED`, ...) was never thrown and must not come back. Until 1.x the skill said only `INSUFFICIENT_CREDITS` was guaranteed
- `users.invite` / `users/add` adds an **existing** account and answers 404 otherwise; reaching an address with no account is the invitations surface (0.0.71)
- there **is** a permission endpoint since 0.0.73, `GET workspaces/{id}/permissions/me`; the local three-GET computation is the fallback for older servers, not the only way
- every interpolated path segment is URL-encoded (0.0.51), not only slugs
- webhook deliveries **do** carry an event `id` (`evt_...`, header `x-buildbase-event-id`) on the platform release that added event ids, typed `id?` by SDK 1.x; dedupe on it and hash the raw body only when it is absent. The skill said the opposite until 2026-11-24, and `validate.py` now bans the old claim
- BuildBase **does** host an MCP server (`https://api.console.buildbase.app/mcp`, BuildBase Console) and a coding agent **can** create a claimable organization (`npx @buildbase/sdk init --claim`); both were listed as "does not exist" until 2026-11-24
- outside a project that has the SDK installed, the CLI is `npx @buildbase/sdk <command>`, never `npx buildbase` (the unscoped npm package is not ours)
- a billing event names its `subject` (`workspace` or `user`); `workspaceId` is present only for a workspace subject

## Verifying a change (the three gates)

A skill is prose plus sample commands, so "it works" has to be shown three ways. Gate 1 is mechanical and must pass before any push.

**Gate 1 - the facts match the code.** All of it automatic:

1. `python3 scripts/validate.py` - manifests, SKILL size, description budget (1536 chars), link resolution, the regression list, and every `/api/...` path in `org-api.md` against `scripts/api-routes.txt`.
2. `./scripts/package.sh` - both zips build.
3. **Symbol check.** Every `use*` and `When*` name in `plugins/buildbase/**` must exist in the published `.d.ts` export lists for the version in the table above. The one expected miss is the prose in `decision-trees/which-feature-to-use.md` stating that `WhenTrialEnded` does not exist.
4. **Self-host block check.** Every fenced compose, env and nginx block in the self-host plugin must byte-match the corresponding fence in `docs/content/self-hosted/*.mdx`, which is generated from `packages/shared/src/constants/self-hosted.ts`. Those blocks are copied, never paraphrased.

When adding a regression rule, plant the defect and confirm the rule fires before trusting it. Every rule in the current list was confirmed that way, and doing so found a stale `(Node.js only)` claim in `SKILL.md` that had been missed by hand.

**Re-verification, 2026-11-24 (pin 1.8.0 -> 1.9.0).** A minor release, diffed source to source (`v1.8.0..v1.9.0`) and against its own agent docs. Nothing outside commerce and pricing changed: no webhook event, no built-in MCP tool (still 82; `get_checkout_status` is still missing from the `BuiltinMcpToolName` union), no CLI, `init` template, agent-setup or API route, and no export removed. Added to the skill: the review screens (`ReviewList`, `ReviewForm`, `RatingSummary`), `SellerStats` (shown by `SellerHome` unless `showStats={false}`), the booking-request list in `SellerBookings`, the licence-key states in `HoldingKeys`, `BuyButton gift` and `seats` (all in `sdk/commerce.md`), `PricingPage initialData` / `usePublicPlans(slug, { initialData })` with a server-component example on `plans.getPublic`, and `PricingPlanTerms` beside a custom paid button (both in `sdk/billing.md` and `sdk/pre-built-ui.md`), and the one-file-per-module `/react` build in `SKILL.md`. Every "verified against" line moved to 1.9.0; dated "since 1.8.0" facts stay. `WEBHOOK_EVENTS` in 1.9.0 still holds 253 names, so the three newer platform names are still outside it.

**Re-verification, 2026-11-24 (pin 0.0.79 -> 1.8.0).** Twenty-five releases (0.0.80 to 0.0.90, 1.0.0 to 1.8.0) since the last pass. Every knowledge file was re-read against the published 1.8.0 tarball (its `.d.ts` files, its own `AGENTS.md` and `agents/*.md`, `docs/ERROR_CODES.md` and the `CHANGELOG.md` behaviour flags) and the platform's main branch at `e11b4805`. Nothing in 1.0.0 was removed, so the work was correcting behaviour changes and adding the 1.x surface. What changed the most:

- **Claims that had become false:** webhook deliveries carry an event `id` (dedupe on it); BuildBase hosts an MCP server and a coding agent can create a claimable organization; the provider renders the app while it restores a session; the SDK keeps a copy of the session id in localStorage; workspace roles are `admin`, `editor`, `viewer` (no member is `owner`); a new org starts in Personal mode; subscription gates count a live subscription by default; a hard quota limit throws `402 QUOTA_EXHAUSTED`; 18 settings screens, not 13; six modules have no React surface, not eight; the old error-code vocabulary (`AUTH_REQUIRED` and the rest) was never thrown; list pages cap at 500 rows; the token exchange allows 120 a minute; the org API has a generated OpenAPI document; the email-provider line (Resend, SendGrid) was invented.
- **New surface documented:** `npx @buildbase/sdk init` with `--claim`, `--agent`, `--dev` and TanStack Start; environments; a plan, wallet and add-ons for a person; entitlements; seats, embedded and in-app checkout; credit holds; scheduled notifications; enterprise SSO through the app owner's own WorkOS account; `@buildbase/sdk/server` email, subscribers and commerce; commerce (new `sdk/commerce.md`); regional `serverUrl` and 421; the Standard Webhooks headers; the 82 built-in MCP tools and their write scopes; BuildBase's hosted console MCP server.
- **Webhook catalog:** 112 -> 256 names from `ALL_SYSTEM_EVENTS`; three of them (`user.passkey_added`, `user.passkey_removed`, `auth.domain_unverified`) are newer than 1.8.0's `WEBHOOK_EVENTS`, and `webhooks.md` says so.
- **Symbol check (gate 1, item 3):** every `use*` and `When*` name in `plugins/buildbase/**` is in the 1.8.0 `.d.ts`, except names the prose states do not exist (`WhenTrialEnded`, `useCollections`, `useWorkflows`, `useEmailCampaigns`, `useUserEntitlement`) and an example app's own `useRunAgent`.
- **Quick-start (gate 2):** `CI=1 npx buildbase init --framework nextjs --org-id 000000000000000000000000` run twice in a minimal App Router app (root `app/` and `src/app/`), with next 16.4.5, react 19.3.1, typescript 5.9.3, @types/react 19.3.0, @types/node 20.19.43 and Node 22.23.5. The first run wrote the provider, the three auth routes and the webhook route, edited the layout and wrote `.env.example` and `.env.local` with secrets empty; the second said `already configured` and changed nothing. Every code fence in `sdk/quick-start.md` and `patterns/nextjs-integration.md` compiles with `tsc --noEmit` under `strict` and matches init's output ignoring comments; the ts/tsx blocks in billing, credits, quota-usage and commerce compile too. `--claim` was not run (it creates a real organization).
- **Local MCP server:** `mcp/` pinned to `^1.8.0` with a new stdio mode; over stdio, `initialize`, `tools/list`, `list_events` (256 names, 43 categories) and `verify_webhook` (valid, then tampered) behave.
- **`validate.py`:** the `event.id` ban is reversed; new rules ban "no hosted MCP", "no claimable organization", a BuildBase publishable key, the removed error codes, the old token-exchange and page-size limits, "no OpenAPI document" and "Eight of twenty modules"; a new check fails on any stated webhook-name count that differs from the JSON.
- **Found along the way, outside this repo:** SDK 1.8.0 serves the built-in MCP tool `get_checkout_status` but its `BuiltinMcpToolName` union omits it, so an `include` list naming it fails `tsc`; the platform's `docs/content/reference/admin-api.mdx` still says `pagination=false` returns a plain array, the token exchange allows 10 a minute, and errors are 503 rather than 500.

**Self-host re-verification, 2026-11-24.** Every fenced compose, env and nginx block in `plugins/buildbase-selfhost` was compared byte-for-byte with `docs/content/self-hosted/*.mdx` on saas-os/os main; the docs fences match the generator output of `self-hosted.ts` after prettier. 19 fences compared: 12 copied fences had drifted (both composes, `nginx-lb.conf`, `.env.selfhost`, four generate-secrets commands that now print `BULLMQ_DASHBOARD_PASSWORD` too, two update commands, the verify block, the directory layout) and were recopied, and two new docs blocks were added (manual migrations, the overage-to-meters migration). Both composes parse with `docker compose config` (also with `--profile scanner`); without secrets they abort on the five `:?` variables. The copied fences keep the docs' em dashes, as os's own em-dash check exempts them; prose stays dash-free. The tenant server's start-up refusal is now the self-hosted edition guard, which names a missing `INSTALLATION_ID` or `INSTALLATION_API_KEY`, as the docs' overview documents. `MAILGUN_API_KEY` is gone from the self-hosted docs. Not run here: a real `docker compose up` (no Docker daemon in the session).

**Re-verification, 2026-10-08 (pin 0.0.78 -> 0.0.79).** 0.0.79 was published from the release workflow and the npm `latest` tag now points at it, so the "install the pinned version explicitly" caveat is gone from this file, `AGENTS.md`, `README.md` and `SKILL.md`. 0.0.79 adds `npx buildbase init`, which writes the provider, the three auth routes, the webhook route and the env placeholders into an existing Next.js, Vite or Express app, and exports the webhook catalog as `WEBHOOK_EVENTS`, `WebhookEventName` and `isWebhookEvent`. The HTTP catalog itself did not change between 0.0.78 and 0.0.79: the release adds a CLI command and one export, no endpoints. Checked against the published tarball: `npx buildbase init --help` runs from a bare `npm install @buildbase/sdk`, and `dist/cli.mjs` ships in the package. The quick-start now names `init` as the shortcut past steps 3 to 6 while keeping every step written out.

**Re-verification, 2026-10-07 (pin 0.0.70 -> 0.0.78).** The HTTP catalog was diffed line by line against the 0.0.78 source. Added to `endpoints.md`: `POST logout`, `GET device-token`, passkeys, devices, sessions, connected agents, workspace invitations (0.0.71), `GET workspaces/{id}/permissions/me` (0.0.73), the notification inbox routes and `notification-preferences/me` (0.0.71), the unauthenticated tracking, consent, checkout-return and agent-readiness routes, the beta routes, and the org-token content client (`@buildbase/sdk/server`, 0.0.73). Corrected: the "one header" claim (browser mode also sends `x-device-id`), path encoding, the `auth/request` and create-workspace bodies, the checkout, update and purchase response fields, what the `notification-preferences` routes hold, what `users/add` does, the factory's module list and `version` option, where app permissions come from, and the Node-only wording in `webhooks.md`. Added the vendored webhook event catalog (112 names) and Step 8 (the webhook route) to the quick-start. Gate 2 typecheck re-run against 0.0.78: see the eval table in `eval/README.md`.

**Gate 2 results, 2026-09-22.** Three of the five parts ran here; the live-API parts cannot, because the agent proxy denies `api.console.buildbase.app` (403 on CONNECT) regardless of credentials.

| Check | Result |
|---|---|
| Both composes abort without `REDIS_PASSWORD` | **Observed.** `docker compose config` exits 1 with `required variable REDIS_PASSWORD is missing a value` |
| Both composes parse with all five secrets | **Observed.** exit 0 |
| Webhook HMAC recipe | **10/10 against the real 0.0.70 package.** Valid verifies; 6-minute-old timestamp rejected and 4-minute accepted; tampered body, wrong secret and missing `sha256=` prefix all rejected; `parseWebhookEvent` returns the event, its type field is `event`, it has no `id`, and an invalid one returns null rather than throwing |
| Quick-start files typecheck | **Observed.** All eight files extracted verbatim from `sdk/quick-start.md` pass `tsc --noEmit` under `strict` against `@buildbase/sdk@0.0.70`, `next@16.3.5`, `react@19.3.0` |
| Live org API, API roles, token exchange, idempotency | **Not run.** Reachable from a local machine; needs a throwaway org's API token |
| Real `docker compose up` from the skill's own files (2026-09-22, local) | **Observed.** Mongo, Redis and auth healthy. Redis started with `--requirepass` and its authenticated healthcheck passed, with zero Redis auth errors in the tenant-server log. `tenant-server` exits only on `Missing API key. Set INSTALLATION_API_KEY`, so `/api/ready` needs a real Installation from the console |
| `read_only` negative control, auth portal | **Observed.** With `read_only` on, as the old compose had it, 5 files still hold the literal `__NEXT_PUBLIC_SERVER_URL__` and the container reports *running*. With it off, 0 remain and 5 are rewritten to the real URL. The broken case looks healthy, which is why it shipped |
| Published images match the docs | **Observed.** `:latest` for all three is a multi-arch manifest (amd64, arm64) on Node 22.21.1 |

**Gate 3, second run 2026-09-23.** Ten prompts now, after the pre-built-UI, module-map and build-an-app pages were added. All ten pass on a read. The two new ones matter most: asked to "build a settings page with profile, invites and billing", it opened with "you don't need to build these screens" and wrote a wrapper around `openWorkspaceSettings` rather than a members form; asked for the Collections hook, it answered "There isn't one", named all eight modules with no React surface, and declined to guess the record-read endpoint.

**Gate 3 results, 2026-09-22.** The eight prompts from `GATE-2-AND-3-LOCAL.md` were run through a separate headless `claude -p --plugin-dir plugins/`, from an empty directory so the model could not read BuildBase source and had to answer from the skill. All eight passed on a line-by-line read, not only the regex first pass: it confirmed an API key now reaches org webhooks but declined to guess an undocumented payload; it refused an irreversible workspace delete and showed the request instead; it said deliveries carry no event id; it handed out a compose with no `read_only` on client or auth and named all five secrets; and it never divided yen by 100. Run on the default model only - repeat on a smaller one before trusting it for weaker models.

`docker compose config` needs no daemon, which is worth knowing: the compose blocks can be parse-checked anywhere the CLI exists.

**Gate 2 - the samples actually run.** Execute the curl and code samples against a throwaway org: the org-API path with a real key, a key on a narrow API role being refused where the role lacks the permission, `token/exchange` then a session-authed read, an `idempotencyKey` sent twice counting once, and the webhook HMAC recipe verifying and then failing on a six-minute-old timestamp. Scaffold a Next.js app and typecheck the quick-start files as shown.

**Gate 3 - the model behaves.** Install the plugin locally and run the prompts in `evaluation/`, one per audience, against the expected answer recorded beside each.

Not verifiable outside a browser or Docker, and left as a human checklist: the self-host "Test Connection" wizard, a full `docker compose up`, Stripe checkout, browser sign-in, push notifications.

## Evals (regression tests)

The eval suite is kept **local-only** (gitignored, not published) under `evaluation/` - `evaluation/evals/evals.json` holds 21 prompts with objective assertions, and `evaluation/eval-results.md` records the last run (100% with-skill, +54pt over baseline, 0 hallucinations). After any substantive change, re-run the prompts with vs without the skill and re-grade. Recommended: test on more than one model (Haiku + Sonnet + Opus) - what Opus infers, Haiku may need spelled out.

## Conventions to keep consistent

- File paths use `src/`; framework examples assume Next.js App Router + TypeScript (with a plain-JS note).
- `serverUrl` = `https://api.console.buildbase.app` (hosted) unless self-hosting.
- Keep `SKILL.md` body under 500 lines; reference files over 100 lines get a `## Contents` table.
- Third-person, trigger-rich `description` frontmatter (≤1024 chars).

## Releasing

1. Run the accuracy audit + evals.
2. Bump `plugin.json` version.
3. Commit + push to `main`. Plugin-marketplace users get the update via `/plugin marketplace update buildbase-skills`.
4. For claude.ai: re-run `./scripts/package.sh` and re-upload `dist/buildbase.zip`.
