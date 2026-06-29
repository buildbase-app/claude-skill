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
    skill = os.path.join(SKILL_DIR, "SKILL.md")
    if not os.path.exists(skill):
        errors.append("plugins/buildbase/SKILL.md is missing")
        return
    n = sum(1 for _ in open(skill))
    if n >= 500:
        errors.append(f"SKILL.md is {n} lines (must be < 500)")


def check_links():
    for dp, _, files in os.walk(SKILL_DIR):
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
    # Patterns that were real bugs; they must not reappear.
    bad = [
        (r"switchToWorkspace\((id|workspaceId)\)", "switchToWorkspace takes the workspace object, not an id"),
        (r"<WhenTrialEnded", "WhenTrialEnded is not a real SDK component"),
        (r"consume\w*\(\s*\{\s*quantity", "credit consume uses `amount`, not `quantity`"),
        (r"result\.remaining", "credit consume returns `balanceAfter`, not `remaining`"),
        (r"AuthStatus.*@buildbase/sdk/react", "AuthStatus is imported from @buildbase/sdk (react entry is types-only)"),
    ]
    for dp, _, files in os.walk(SKILL_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            text = open(p).read()
            for pat, msg in bad:
                if re.search(pat, text):
                    rel = os.path.relpath(p, ROOT)
                    errors.append(f"regression in {rel}: {msg}")


def main():
    check_json(".claude-plugin/marketplace.json")
    check_json("plugins/buildbase/.claude-plugin/plugin.json")
    check_skill_size()
    check_links()
    check_regressions()

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("All skill validation checks passed.")


if __name__ == "__main__":
    main()
