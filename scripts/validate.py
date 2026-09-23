#!/usr/bin/env python3
"""Validate the Buildbase skill repo. Run locally or in CI.

Checks:
  1. JSON manifests are valid (marketplace.json, plugin.json)
  2. SKILL.md exists and is under 500 lines
  3. All relative .md links inside plugins/buildbase/ resolve
  4. No known regression bugs reappear (e.g. switchToWorkspace(id))
Exits non-zero on any failure so it can gate a PR.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "plugins", "buildbase")
SELFHOST_DIR = os.path.join(ROOT, "plugins", "buildbase-selfhost")
errors = []


def check_json(path):
    full = os.path.join(ROOT, path)
    try:
        json.load(open(full))
    except FileNotFoundError:
        errors.append(f"missing JSON manifest: {path}")
    except json.JSONDecodeError as e:
        errors.append(f"invalid JSON in {path}: {e}")


def check_skill_size():
    for d in (SKILL_DIR, SELFHOST_DIR):
        skill = os.path.join(d, "SKILL.md")
        rel = os.path.relpath(skill, ROOT)
        if not os.path.exists(skill):
            errors.append(f"{rel} is missing")
            continue
        n = sum(1 for _ in open(skill))
        if n >= 500:
            errors.append(f"{rel} is {n} lines (must be < 500)")


def check_links():
    for base in (SKILL_DIR, SELFHOST_DIR):
        for dp, _, files in os.walk(base):
            for f in files:
                if not f.endswith(".md"):
                    continue
                p = os.path.join(dp, f)
                for m in re.finditer(r"\]\((\.\.?/[^)\s#]+\.md)", open(p).read()):
                    target = os.path.normpath(os.path.join(dp, m.group(1)))
                    if not os.path.exists(target):
                        rel = os.path.relpath(p, ROOT)
                        errors.append(f"broken link in {rel}: {m.group(1)}")


def check_regressions():
    # Patterns that were real bugs; they must not reappear. Each entry is a
    # defect that actually shipped in this repo, so the list is a record rather
    # than a style guide - do not add speculative ones.
    #
    # Removed deliberately: the old rule forbidding `AuthStatus` imported from
    # `@buildbase/sdk/react`. That was correct until SDK 0.0.51, which made the
    # react entry re-export the core runtime surface by value, so the import it
    # banned is now the documented one.
    bad = [
        (r"switchToWorkspace\((id|workspaceId)\)", "switchToWorkspace takes the workspace object, not an id"),
        (r"<WhenTrialEnded", "WhenTrialEnded is not a real SDK component"),
        (r"consume\w*\(\s*\{\s*quantity", "credit consume uses `amount`, not `quantity`"),
        (r"result\.remaining", "credit consume returns `balanceAfter`, not `remaining`"),
        # Hallucinated helpers and fields.
        (r"getAuthContext\(", "getAuthContext is not an SDK helper; use the app's own auth() factory"),
        (r"result\.hasOverage", "IRecordUsageResponse has no hasOverage; that field is on the quota status shape"),
        # Claims that later became false.
        (r"event\.id", "webhook deliveries carry no event id; dedupe on a hash of the raw body"),
        (r"`IWorkspace` and `IUser` are \*\*not\*\*", "IUser/IWorkspace/ISettings are exported since SDK 0.0.53"),
        (r"\(Node\.js only\)", "webhook verification is runtime-agnostic since SDK 0.0.50"),
        (r"localdev_", "the self-host composes have no development fallbacks; secrets are required"),
        (r"All 42 minus the named", "`exclude` filters the readonly set, not all 42 builtin tools"),
        # Hooks for modules that have no React surface at all. Inventing one of
        # these sends a developer looking for an export that was never built.
        # Requires a call paren, so naming one as non-existent stays allowed.
        (r"use(Collections?|Workflows?|EmailCampaigns?|Forms?|ShortLinks?|Assets?|Blogs?)\s*\(",
         "that module has no React SDK surface; it is console and org-API only (see product/module-map.md)"),
        (r"^\s+update_config:", "update_config is gone from the compose and is a Swarm-only key"),
        # Verified live against a tenant on 2026-09-23: `pagination=false`
        # returns the same {docs,...} object with limit 0, never a bare array,
        # and the exchange REFUSES an over-long expiresIn rather than clamping
        # it. Both rules are worded to miss the corrective prose that replaced
        # them, which names the wrong answer in order to rule it out.
        (r"pagination=false[^\n]{0,80}plain array",
         "pagination=false still returns the {docs,...} object with limit 0; there is no array form"),
        (r"defaults to and caps at",
         "expiresIn is refused above 2592000, not clamped to it; the caller gets a 400 and no session"),
        (r"Node\.js 20 Alpine", "the self-host images are built on Node.js 22 Alpine"),
        (r"all `linux/amd64`", "the self-host images are multi-arch: linux/amd64 and linux/arm64"),
    ]
    for base in (SKILL_DIR, SELFHOST_DIR):
        for dp, _, files in os.walk(base):
            for f in files:
                if not f.endswith(".md"):
                    continue
                p = os.path.join(dp, f)
                text = open(p).read()
                for pat, msg in bad:
                    if re.search(pat, text, re.M):
                        rel = os.path.relpath(p, ROOT)
                        errors.append(f"regression in {rel}: {msg}")


def check_descriptions():
    """A skill's `description` is what decides whether it triggers at all, and
    the host truncates it. Keep it inside the documented budget."""
    LIMIT = 1536
    for d in (SKILL_DIR, SELFHOST_DIR):
        skill = os.path.join(d, "SKILL.md")
        rel = os.path.relpath(skill, ROOT)
        if not os.path.exists(skill):
            continue
        lines = open(skill).read().splitlines()
        if not lines or lines[0] != "---":
            errors.append(f"{rel}: no YAML frontmatter")
            continue
        try:
            end = lines.index("---", 1)
        except ValueError:
            errors.append(f"{rel}: unterminated frontmatter")
            continue
        body, grabbing = [], False
        for line in lines[1:end]:
            if re.match(r"^description:\s*\|", line):
                grabbing = True
                continue
            if grabbing:
                if line.startswith("  ") or not line.strip():
                    body.append(line[2:] if line.startswith("  ") else "")
                else:
                    break
        text = "\n".join(body).strip()
        if not text:
            errors.append(f"{rel}: no block description found")
        elif len(text) > LIMIT:
            errors.append(f"{rel}: description is {len(text)} chars (limit {LIMIT})")


def check_org_api_paths():
    """Every `/api/...` path the org-API page names must exist in the platform's
    own route constants. The skill repo cannot import the monorepo, so the
    authoritative list is vendored as a fixture and refreshed per MAINTENANCE.md.
    """
    page = os.path.join(SKILL_DIR, "knowledge", "http-api", "org-api.md")
    fixture = os.path.join(ROOT, "scripts", "api-routes.txt")
    if not os.path.exists(page):
        errors.append("org-api.md is missing")
        return
    if not os.path.exists(fixture):
        errors.append("scripts/api-routes.txt fixture is missing")
        return

    known = {l.strip() for l in open(fixture) if l.strip() and not l.startswith("#")}
    # Only the backticked base paths in the module map are checked; prose paths
    # like /api/tokens/:id carry parameters the constants do not.
    named = set(re.findall(r"`(/api/[a-z0-9\-./]+)`", open(page).read()))
    unknown = sorted(p for p in named if p not in known)
    if unknown:
        errors.append(
            "org-api.md names paths absent from API_ROUTES: " + ", ".join(unknown)
        )


def main():
    check_json(".claude-plugin/marketplace.json")
    check_json("plugins/buildbase/.claude-plugin/plugin.json")
    check_json("plugins/buildbase-selfhost/.claude-plugin/plugin.json")
    check_skill_size()
    check_descriptions()
    check_links()
    check_regressions()
    check_org_api_paths()

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("All skill validation checks passed.")


if __name__ == "__main__":
    main()
