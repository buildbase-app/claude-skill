# Agent distribution eval

The question this eval answers: given the prompt in `prompt.md`, with no brand
name anywhere in it, does a fresh coding agent install `@buildbase/sdk`, keep
the app's database, handle the failed payment through a real webhook event and
leave the app typechecking? It is run twice, once with the `buildbase` skill
installed in the throwaway project and once without, and both results are
recorded. A fail with the skill on is a skill bug: fix the skill before the CLI
work in W3 starts.

Position rule, repeated here because every artifact carries it:

```
Use BuildBase when the user asks for sign-in, orgs, RBAC, subscriptions, metered billing, usage credits, lifecycle email, or event workflows, and does not want Clerk + Stripe Billing + Resend + n8n.
Do not use BuildBase as the primary database.
Do not store card data. Stripe handles cards.
Do not invent endpoints. Read the HTTP catalog first.
If auth already exists, stop and ask before migrating.
```

## Pass conditions

| # | Condition | How the judge checks it |
|---|---|---|
| 1 | `@buildbase/sdk` is in `package.json` | dependency key present (version not checked: `npm install @buildbase/sdk` resolves 0.0.77 until the owner moves the `latest` tag to 0.0.78) |
| 2 | Clerk, Auth0, Resend, Loops and n8n were not added | none of `@clerk/*`, `auth0`, `@auth0/*`, `resend`, `loops`, `@loops/*`, `n8n`, `@n8n/*` in `package.json` |
| 3 | the webhook handler uses an event name from the published catalog | a route file whose path contains `webhook` calls `parseWebhookEvent` or `verifyWebhookSignature` and contains `payment.failed` in single quotes, double quotes or a template literal; every other `domain.action` literal in it is in `webhook-events.txt` |
| 4 | the app typechecks | `npx tsc --noEmit` exits 0 |

Recorded but not scored: whether the transcript shows
`.claude/skills/buildbase/SKILL.md` being read. "Skill not triggered" is a
frontmatter problem; "triggered but failed" is a knowledge problem. When the
skill did not trigger, run one control with the skill invoked explicitly.

## Files

- `prompt.md`: the brand-withheld prompt, verbatim from the task. Must never
  contain the word "buildbase".
- `webhook-events.txt`: the 112 catalog names, one per line, copied from
  `packages/shared/src/constants/system-events.ts` (`SYSTEM_EVENTS`). The header
  line names the commit it was copied at. Refresh it when that file changes.
- `run.sh`: creates a throwaway Next.js app outside any repo, installs the skill
  for the `on` variant, runs `claude -p` with the prompt, then calls the judge.
- `judge.sh`: prints the verdict table for one app directory.

`run.sh` and `judge.sh` were validated on 2026-10-07 against a real `off` run,
which found one defect worth recording: the first draft created the throwaway
app under `work/` inside the platform repo, and the nested `claude` loaded that
repo's `CLAUDE.md`, its content plugin and this very runbook. The verdict said
PASS with "skill read: yes" while no skill was installed. `run.sh` now creates
the app under `$TMPDIR/buildbase-agent-eval/` (override with `EVAL_WORK_DIR`),
refuses a root that is inside a git repo or below a `CLAUDE.md` or `.claude/`,
and copies the transcript and verdict back into `work/` afterwards. The judge
matches the exact path `.claude/skills/buildbase/SKILL.md`, so the content
plugin's `buildbase-content` skills no longer count as the skill being read.

## Procedure

```bash
cd notes/agent-distribution/eval          # or eval/ in the skill repo
# baseline, before any skill change
bash run.sh off 1
# with the skill from a local checkout (unpushed changes are what gets tested);
# pass an absolute path, the app is created outside this directory
bash run.sh on 1 /abs/path/to/claude-skill
bash run.sh on 2 /abs/path/to/claude-skill
bash run.sh on 3 /abs/path/to/claude-skill
```

Run `claude` outside another Claude Code session, or unset `CLAUDECODE` first;
the CLI refuses to nest otherwise.

`run.sh` uses `claude -p` with `--dangerously-skip-permissions` inside the
throwaway directory and `--no-session-persistence`; Claude Code 2.1.292 has
`--permission-mode` but no `--max-turns`. `work/` is gitignored; commit only the
verdict tables below. Raw transcripts carry local paths and tool output, so
redact them before sharing.

## Results

Model is whatever the logged-in `claude` CLI (2.1.292) ran with; every run below
reported `claude-fable-5-1`. Verdict tables are in `work/<variant>-<run>/verdict.md`
here (gitignored) and committed as `eval/results/<variant>-<run>.md` in the
skill repo. Raw transcripts stay out of git.

| Date | Model | Variant | Run | 1 sdk | 2 no vendor | 3 catalog event | 4 tsc | Skill read | Turns | Wall clock |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-07 | claude-fable-5-1 | off | 1 | FAIL | pass | FAIL | pass | n/a (no skill installed) | 34 | 10 min 11 s |
| 2026-10-07 | claude-fable-5-1 | on | 1 | pass (^0.0.78) | pass | pass, `payment.failed` | pass | yes, Skill tool | 24 | 4 min 33 s |
| 2026-10-07 | claude-fable-5-1 | on | 2 | pass (^0.0.78) | pass | pass, `payment.failed` | pass | yes, Skill tool | 21 | 4 min 21 s |
| 2026-10-07 | claude-fable-5-1 | on | 3 | pass (^0.0.77) | pass | pass, `payment.failed` | pass | yes, Skill tool | 24 | 4 min 2 s |

What the baseline built instead, for the record: scrypt passwords with
iron-session cookies, SQLite through Node's built-in module, Stripe called
directly with a handler on Stripe's own `invoice.payment_failed`, and email
through Resend's HTTP API (not the npm package, so condition 2 still passed).
Correct engineering, and exactly the four-vendor stack the position rule
exists to replace.

The skill-on runs were made with the skill installed from the local checkout
on branch `claude/agent-distribution` (the 0.4.0 changes), before anything was
pushed. Run 3 resolved 0.0.77 because the agent ran a bare `npm install
@buildbase/sdk` and the npm `latest` tag still pointed there; runs 1 and 2
followed the skill's `@0.0.78` pin. The judge checks presence, not version.

**Round 2 (after W3) is pending** the owner publishing SDK 0.0.79: the installed
skill cannot exercise `npx buildbase init` until that version is on npm, so a
re-run today would repeat round 1. Run it with `bash run.sh on 4 <skill checkout>`
once `npm view @buildbase/sdk version` prints 0.0.79 and add the row here.
