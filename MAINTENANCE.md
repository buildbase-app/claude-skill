# Maintenance Guide

How to keep this skill accurate as the Buildbase SDK / API grows. The golden rule that made this skill reliable: **the SDK source is the source of truth — never document an API you haven't confirmed in code.**

## Ground-truth sources

| What | Where |
|------|-------|
| SDK package | [`@buildbase/sdk`](https://www.npmjs.com/package/@buildbase/sdk) (source: [buildbase-app/sdk](https://github.com/buildbase-app/sdk)) — verified against **v0.0.70**. The `/mcp` surface is accurate for 0.0.54 plus the 0.0.55 additions (resources, prompts, rich tool results, the connect guide); the newer 0.0.56-0.0.70 changes it must track are `signOut` ending the server session (0.0.70), the `tracking` prop (0.0.62), and devices and sessions (0.0.57) |
| Reference apps | [buildbase-app/nextjs-starter](https://github.com/buildbase-app/nextjs-starter) (auth wiring, token-exchange shape, React version); [buildbase-app/nextjs-agent-mcp-starter](https://github.com/buildbase-app/nextjs-agent-mcp-starter) for the MCP/agent-readiness wiring |
| Official docs | https://docs.buildbase.app — for facts not in the package. `reference/admin-api` is the source for `knowledge/http-api/org-api.md`, and `self-hosted/*` is the source for the self-host plugin's compose blocks, which are generated output and must be copied rather than paraphrased |
| Dashboard | https://console.buildbase.app |

## When the SDK version bumps

1. **Re-point at the new source** and check `package.json` for the new version, exports, and peer deps.
2. **Re-verify the public surface** the skill documents:
   - Hooks/gates/components — confirm each named symbol still exists (`src/react.ts`, `src/providers/**`, `src/hooks/**`).
   - Server modules/methods — `src/lib/server-client.ts`.
   - Field shapes inside code samples (this is where drift hides — e.g. credit consume uses `amount`, not `quantity`). Check `src/api/types.ts`.
3. **Regenerate the HTTP-API catalog** (`plugins/buildbase/knowledge/http-api/`) from `src/lib/api-base.ts` + `src/api/services/*-api.ts` if endpoints changed.
4. **Update `plugins/buildbase/SKILL.md`** version note and any changed validation rules (orgId format, `ApiVersion`, etc.).
5. **Bump the version** in `plugins/buildbase/.claude-plugin/plugin.json` (semver). Plugin installs pin to this; bumping it is how users get the update.

## Accuracy audit (run before every release)

Re-run the verification that caught real bugs during authoring — for each knowledge file, confirm every API symbol, code snippet, endpoint, and factual claim against the SDK source. Classify findings as HALLUCINATION / INACCURATE / UNVERIFIABLE / OK and fix the first two. The recurring drift points to watch:

- `switchToWorkspace(workspace)` takes the **object**, not an id
- credit consume uses **`amount`** (usage record uses `quantity`)
- runtime values (`AuthStatus`, pricing utils) import from `@buildbase/sdk`, not `@buildbase/sdk/react` (the `/react` entry is types-only)
- `IWorkspace` / `IUser` are **not** exported from the public type surface
- only `INSUFFICIENT_CREDITS` is a guaranteed error-code string

## Verifying a change (the three gates)

A skill is prose plus sample commands, so "it works" has to be shown three ways. Gate 1 is mechanical and must pass before any push.

**Gate 1 - the facts match the code.** All of it automatic:

1. `python3 scripts/validate.py` - manifests, SKILL size, description budget (1536 chars), link resolution, the regression list, and every `/api/...` path in `org-api.md` against `scripts/api-routes.txt`.
2. `./scripts/package.sh` - both zips build.
3. **Symbol check.** Every `use*` and `When*` name in `plugins/buildbase/**` must exist in the published `.d.ts` export lists for the version in the table above. The one expected miss is the prose in `decision-trees/which-feature-to-use.md` stating that `WhenTrialEnded` does not exist.
4. **Self-host block check.** Every fenced compose, env and nginx block in the self-host plugin must byte-match the corresponding fence in `docs/content/self-hosted/*.mdx`, which is generated from `packages/shared/src/constants/self-hosted.ts`. Those blocks are copied, never paraphrased.

When adding a regression rule, plant the defect and confirm the rule fires before trusting it. Every rule in the current list was confirmed that way, and doing so found a stale `(Node.js only)` claim in `SKILL.md` that had been missed by hand.

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

**Gate 3 results, 2026-09-22.** The eight prompts from `GATE-2-AND-3-LOCAL.md` were run through a separate headless `claude -p --plugin-dir plugins/`, from an empty directory so the model could not read BuildBase source and had to answer from the skill. All eight passed on a line-by-line read, not only the regex first pass: it confirmed an API key now reaches org webhooks but declined to guess an undocumented payload; it refused an irreversible workspace delete and showed the request instead; it said deliveries carry no event id; it handed out a compose with no `read_only` on client or auth and named all five secrets; and it never divided yen by 100. Run on the default model only - repeat on a smaller one before trusting it for weaker models.

`docker compose config` needs no daemon, which is worth knowing: the compose blocks can be parse-checked anywhere the CLI exists.

**Gate 2 - the samples actually run.** Execute the curl and code samples against a throwaway org: the org-API path with a real key, a key on a narrow API role being refused where the role lacks the permission, `token/exchange` then a session-authed read, an `idempotencyKey` sent twice counting once, and the webhook HMAC recipe verifying and then failing on a six-minute-old timestamp. Scaffold a Next.js app and typecheck the quick-start files as shown.

**Gate 3 - the model behaves.** Install the plugin locally and run the prompts in `evaluation/`, one per audience, against the expected answer recorded beside each.

Not verifiable outside a browser or Docker, and left as a human checklist: the self-host "Test Connection" wizard, a full `docker compose up`, Stripe checkout, browser sign-in, push notifications.

## Evals (regression tests)

The eval suite is kept **local-only** (gitignored, not published) under `evaluation/` — `evaluation/evals/evals.json` holds 21 prompts with objective assertions, and `evaluation/eval-results.md` records the last run (100% with-skill, +54pt over baseline, 0 hallucinations). After any substantive change, re-run the prompts with vs without the skill and re-grade. Recommended: test on more than one model (Haiku + Sonnet + Opus) — what Opus infers, Haiku may need spelled out.

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
