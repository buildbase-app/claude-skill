# Maintenance Guide

How to keep this skill accurate as the Buildbase SDK / API grows. The golden rule that made this skill reliable: **the SDK source is the source of truth — never document an API you haven't confirmed in code.**

## Ground-truth sources

| What | Where |
|------|-------|
| SDK package | `@buildbase/sdk` — the local checkout used during authoring was `codebase/sdk` (v0.0.47) |
| Reference app | `codebase/nextjs-starter` (auth wiring, token-exchange shape, React version) |
| Official docs | https://docs.buildbase.app (dashboard labels, hosted `serverUrl`) — for facts not in code |
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
