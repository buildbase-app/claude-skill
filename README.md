# Buildbase SDK — Claude Skill

An [Agent Skill](https://code.claude.com/docs/en/skills) that turns Claude into an expert at integrating the **Buildbase SDK** (`@buildbase/sdk`). Install it and Claude can take a developer from `npm install` to a working sign-in, then guide auth, workspaces, billing, feature flags, quota, credits, notifications, server-side usage, webhooks — and even using Buildbase from a non-Node backend over raw HTTP.

Every API name, signature, endpoint, and code sample in this skill was verified against the SDK source (`@buildbase/sdk@0.0.47`) and the official `nextjs-starter` reference app — not guessed.

---

## What's in here

| Path | Purpose |
|------|---------|
| `plugins/buildbase/SKILL.md` | The skill entrypoint (routing + rules). **This is what ships.** |
| `plugins/buildbase/knowledge/` | The knowledge base Claude routes into (SDK reference, learning path, HTTP API, troubleshooting, etc.) |
| `.claude-plugin/marketplace.json` | Makes this repo a Claude Code plugin marketplace |
| `plugins/buildbase/.claude-plugin/plugin.json` | Plugin manifest |
| `scripts/package.sh` | Builds `dist/buildbase.zip` for claude.ai upload |

---

## Install

Pick whichever matches how you use Claude.

### 1. Claude Code — plugin (recommended; auto-updates)

```
/plugin marketplace add buildbase-app/claude-skill
/plugin install buildbase@buildbase-skills
```

Update later with `/plugin marketplace update buildbase-skills`.

### 2. Claude Code — plain skill folder

```bash
git clone https://github.com/buildbase-app/claude-skill
cp -R claude-skill/plugins/buildbase ~/.claude/skills/buildbase
```

(Project-scoped instead? Copy into `.claude/skills/buildbase/` inside your project and commit it for your team.)

### 3. claude.ai — zip upload (Pro/Team/Enterprise)

```bash
./scripts/package.sh        # produces dist/buildbase.zip
```

Then in claude.ai: **Settings → Capabilities → Skills → Upload** and select `dist/buildbase.zip`.

---

## Using it

Once installed, just ask Claude normally — the skill triggers on any Buildbase topic:

> "Add Buildbase auth to my Next.js app."
> "Why does my `WhenSubscription` gate render nothing?"
> "How do I record metered usage from a Python backend?"

The skill is strongest on **Next.js + TypeScript** (a verified, step-by-step golden path with a ✅ check after each step). For other React frameworks it adapts the concepts; for non-Node backends it provides a full HTTP-API reference (`plugins/buildbase/knowledge/http-api/`).

---

## Maintenance

This skill is meant to evolve with the SDK/API. See [MAINTENANCE.md](./MAINTENANCE.md) for how to re-verify against new SDK versions, regenerate the HTTP-API catalog, run the eval suite, and cut a new version.

## License

MIT — see [LICENSE](./LICENSE). Buildbase and `@buildbase/sdk` are products of their respective owner; this is an independent integration skill.
