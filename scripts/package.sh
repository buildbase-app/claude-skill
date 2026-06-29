#!/usr/bin/env bash
# Build an upload-ready zip of the Buildbase skill for claude.ai
# (Settings → Capabilities → Skills → Upload).
#
# Output: dist/buildbase.zip  — contains a top-level `buildbase/` folder
# with SKILL.md + knowledge/ (no dev artifacts, no plugin manifest).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SRC="$ROOT/plugins/buildbase"
DIST="$ROOT/dist"
STAGE="$DIST/buildbase"

rm -rf "$DIST"
mkdir -p "$STAGE"

# Copy only what ships with the skill: SKILL.md + knowledge/
cp "$SKILL_SRC/SKILL.md" "$STAGE/SKILL.md"
cp -R "$SKILL_SRC/knowledge" "$STAGE/knowledge"

# Zip from inside dist/ so the archive root is `buildbase/`
( cd "$DIST" && zip -r -q buildbase.zip buildbase )
rm -rf "$STAGE"

echo "Built: $DIST/buildbase.zip"
unzip -l "$DIST/buildbase.zip" | tail -n +2 | head -5
echo "..."
echo "Upload this at claude.ai → Settings → Capabilities → Skills."
