#!/usr/bin/env bash
# Build upload-ready zips of the Buildbase skills for claude.ai
# (Settings → Capabilities → Skills → Upload).
#
# Output (one zip per skill, each with a top-level folder
# containing SKILL.md + knowledge/ — no dev artifacts, no plugin manifest):
#   dist/buildbase.zip            — SDK integration skill
#   dist/buildbase-selfhost.zip   — self-hosting skill
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"

rm -rf "$DIST"
mkdir -p "$DIST"

package() {
  local name="$1"                    # plugin dir name = skill name = zip name
  local src="$ROOT/plugins/$name"
  local stage="$DIST/$name"

  mkdir -p "$stage"
  # Copy only what ships with the skill: SKILL.md + knowledge/
  cp "$src/SKILL.md" "$stage/SKILL.md"
  cp -R "$src/knowledge" "$stage/knowledge"

  # Zip from inside dist/ so the archive root is `<name>/`
  ( cd "$DIST" && zip -r -q "$name.zip" "$name" )
  rm -rf "$stage"

  echo "Built: $DIST/$name.zip"
}

package "buildbase"
package "buildbase-selfhost"

echo
echo "Contents:"
for z in "$DIST"/*.zip; do
  echo "  $z"
  unzip -l "$z" | tail -n +4 | head -6 | sed 's/^/    /'
done
echo
echo "Upload each at claude.ai → Settings → Capabilities → Skills."
