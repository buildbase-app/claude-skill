# Buildbase — Claude Skills

[Agent Skills](https://code.claude.com/docs/en/skills) that turn Claude into a Buildbase expert. This repo is a Claude Code plugin marketplace shipping **two complementary skills**:

| Skill | For | What it does |
|-------|-----|--------------|
| **`buildbase`** | App developers integrating Buildbase, **and org owners automating their own org** | Takes a developer from `npm install` to a working sign-in, then guides auth, workspaces, billing, feature flags, quota, credits, notifications, devices and sessions, server-side usage, webhooks, and using Buildbase from a non-Node backend over raw HTTP. For operators it covers the console's own REST API: an API key with a role, the shared list contract, and what a key can and cannot reach. |
| **`buildbase-selfhost`** | Operators running Buildbase themselves | Deploys and operates the self-hosted platform — the four-component architecture, the real Docker Compose + Nginx configs, env-var reference, production hardening, upgrades. |

The two skills work together. If you self-host, first use `buildbase-selfhost` to deploy your stack, then use `buildbase` to build your app against it — point `serverUrl` at your own tenant server instead of the Buildbase cloud.

**Grounding** — we don't guess:
- `buildbase` - every API name, signature, endpoint and code sample is verified against the published type surface of `@buildbase/sdk@0.0.79` and the official `nextjs-starter` / `nextjs-agent-mcp-starter` reference apps. The org-API half is verified against the platform's own shared route constants, and the webhook event catalog (`knowledge/http-api/webhook-events.json`) is vendored from the platform's `SYSTEM_EVENTS` constant.
- `buildbase-selfhost` — we ground every fact in the self-hosted docs (`self-hosted/{overview,quick-start,configuration,production}`) and reproduce the real `docker-compose.selfhost.yml` and `nginx-lb.conf` verbatim. Where the docs say nothing, the skill answers "not documented" instead of inventing (see [`plugins/buildbase-selfhost/GAPS.md`](./plugins/buildbase-selfhost/GAPS.md)).

---

## What's in here

| Path | Purpose |
|------|---------|
| `plugins/buildbase/SKILL.md` | SDK-integration skill entrypoint (routing + rules). **Ships.** |
| `plugins/buildbase/knowledge/` | Integration knowledge base (SDK reference, learning path, HTTP API, troubleshooting, etc.) |
| `plugins/buildbase-selfhost/SKILL.md` | Self-hosting skill entrypoint. **Ships.** |
| `plugins/buildbase-selfhost/knowledge/` | Self-hosting knowledge base (architecture, deploy, config, operations, diagnostics, handoff) |
| `plugins/buildbase-selfhost/GAPS.md` | Tracker of self-hosted-docs gaps (dev artifact — **not** shipped in the zip) |
| `.claude-plugin/marketplace.json` | Makes this repo a Claude Code plugin marketplace (lists both plugins) |
| `plugins/*/.claude-plugin/plugin.json` | Plugin manifests |
| `scripts/package.sh` | Builds `dist/buildbase.zip` and `dist/buildbase-selfhost.zip` for claude.ai upload |
| `scripts/validate.py` | Validates both plugins (manifests, SKILL size, description budget, links, regressions, the webhook catalog, the org-API paths) |
| `scripts/render-webhook-catalog.py` | Renders `webhook-events.json` into the catalog section of `knowledge/http-api/webhooks.md` |
| `AGENTS.md` / `CLAUDE.md` | The position rule and the install paths, for the agents that read a repo-root instruction file: Codex, Cursor, GitHub Copilot, Gemini CLI, Jules, Windsurf, Zed and others per [agents.md](https://agents.md), and Lovable on every message |
| `distribution/` | Paste prompts and connector knowledge for Lovable, Bolt and v0 (added by the distribution workstream) |
| `eval/` | The brand-withheld eval prompt, pass conditions and recorded runs (added by the distribution workstream) |
| `mcp/` | A local MCP server exposing `create_workspace`, `list_events`, `scaffold_auth`, `verify_webhook` (added by the distribution workstream; not hosted) |

---

## Install

Install one or both skills - `buildbase` to integrate, `buildbase-selfhost` to self-host - using whichever method matches the agent you run.

### 1. Any agent - the skills CLI

Works for Claude Code, Cursor, Codex, Copilot, Windsurf and every other agent that reads [Agent Skills](https://agentskills.io):

```bash
npx skills add buildbase-app/claude-skill                      # both skills, pick agents interactively
npx skills add buildbase-app/claude-skill --skill buildbase    # the SDK skill only
npx skills add buildbase-app/claude-skill -a cursor            # install for one agent

Agent names are the CLI's own identifiers, not the product names: `claude-code`,
`cursor`, `codex`, `github-copilot` (not `copilot`), `gemini-cli`, `windsurf`,
`cline`, `continue`, `zed` and around seventy more. Run the command with no
`-a` to pick from the list. Verified on 2026-10-08: `cursor`, `codex`,
`github-copilot`, `gemini-cli`, `opencode` and `windsurf` each install this
skill byte-identically, with all 33 knowledge files; most share
`.agents/skills/`, while Claude Code uses `.claude/skills/` and Windsurf
`.windsurf/skills/`.
```

The repo's root [`AGENTS.md`](./AGENTS.md) carries the position rule and points at both skills, so an agent that reads only that file still knows when BuildBase applies.

### 2. Claude Code - plugin (auto-updates)

```
/plugin marketplace add buildbase-app/claude-skill
/plugin install buildbase@buildbase-skills            # SDK integration
/plugin install buildbase-selfhost@buildbase-skills   # self-hosting (optional)
```

Update later with `/plugin marketplace update buildbase-skills`.

### 3. Claude Code - plain skill folder

```bash
git clone https://github.com/buildbase-app/claude-skill
cp -R claude-skill/plugins/buildbase          ~/.claude/skills/buildbase
cp -R claude-skill/plugins/buildbase-selfhost ~/.claude/skills/buildbase-selfhost   # optional
```

(Project-scoped instead? Copy into `.claude/skills/<name>/` inside your project and commit it for your team.)

### 4. claude.ai - zip upload (Pro/Team/Enterprise)

```bash
./scripts/package.sh        # produces dist/buildbase.zip and dist/buildbase-selfhost.zip
```

Then in claude.ai: **Settings → Capabilities → Skills → Upload** and select each zip you want (`dist/buildbase.zip` and/or `dist/buildbase-selfhost.zip`).

---

## Using it

Once installed, just ask Claude normally — each skill triggers on its own topics.

**`buildbase` (integration):**
> "Add Buildbase auth to my Next.js app."
> "Why does my `WhenSubscription` gate render nothing?"
> "How do I record metered usage from a Python backend?"

It works best on **Next.js + TypeScript** — a step-by-step golden path that adds a ✅ check after each step. For other React frameworks it adapts the concepts; for non-Node backends it gives you a full HTTP-API reference (`plugins/buildbase/knowledge/http-api/`).

**`buildbase-selfhost` (deploy/operate):**
> "Deploy Buildbase self-hosted with Docker Compose."
> "What does `DB_ENCRYPTION_KEY` do?"
> "My `/api/ready` isn't returning true — what should I check?"
> "Set up the production stack with Nginx and replicas."

It ships the real `docker-compose.selfhost.yml` and `nginx-lb.conf` verbatim, plus a config reference and doc-grounded diagnostics. For anything the self-hosted docs don't cover (e.g. a backup procedure), it says so rather than inventing — those open items live in [`GAPS.md`](./plugins/buildbase-selfhost/GAPS.md).

---

## Maintenance

Both skills evolve with the SDK/API and the self-hosted docs. See [MAINTENANCE.md](./MAINTENANCE.md) to re-verify against new SDK versions, regenerate the HTTP-API catalog, run the eval suite, and cut a new version. When the self-hosted docs change, re-ground `buildbase-selfhost` against them and close the matching rows in [`GAPS.md`](./plugins/buildbase-selfhost/GAPS.md).

## License

MIT — see [LICENSE](./LICENSE). Buildbase and `@buildbase/sdk` belong to their owner; these are independent skills.
