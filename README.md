# Buildbase — Claude Skills

[Agent Skills](https://code.claude.com/docs/en/skills) that turn Claude into a Buildbase expert. This repo is a Claude Code plugin marketplace shipping **two complementary skills**:

| Skill | For | What it does |
|-------|-----|--------------|
| **`buildbase`** | App developers integrating Buildbase | Takes a developer from `npm install` to a working sign-in, then guides auth, workspaces, billing, feature flags, quota, credits, notifications, server-side usage, webhooks — and using Buildbase from a non-Node backend over raw HTTP. |
| **`buildbase-selfhost`** | Operators running Buildbase themselves | Deploys and operates the self-hosted platform — the four-component architecture, the real Docker Compose + Nginx configs, env-var reference, production hardening, upgrades. |

The two skills work together. If you self-host, first use `buildbase-selfhost` to deploy your stack, then use `buildbase` to build your app against it — point `serverUrl` at your own tenant server instead of the Buildbase cloud.

**Grounding** — we don't guess:
- `buildbase` — we verified every API name, signature, endpoint, and code sample against the SDK source (`@buildbase/sdk@0.0.47`) and the official `nextjs-starter` reference app.
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
| `scripts/validate.py` | Validates both plugins (manifests, SKILL size, links, regressions) |

---

## Install

Install one or both skills — `buildbase` to integrate, `buildbase-selfhost` to self-host — using whichever method matches how you run Claude.

### 1. Claude Code — plugin (recommended; auto-updates)

```
/plugin marketplace add buildbase-app/claude-skill
/plugin install buildbase@buildbase-skills            # SDK integration
/plugin install buildbase-selfhost@buildbase-skills   # self-hosting (optional)
```

Update later with `/plugin marketplace update buildbase-skills`.

### 2. Claude Code — plain skill folder

```bash
git clone https://github.com/buildbase-app/claude-skill
cp -R claude-skill/plugins/buildbase          ~/.claude/skills/buildbase
cp -R claude-skill/plugins/buildbase-selfhost ~/.claude/skills/buildbase-selfhost   # optional
```

(Project-scoped instead? Copy into `.claude/skills/<name>/` inside your project and commit it for your team.)

### 3. claude.ai — zip upload (Pro/Team/Enterprise)

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
