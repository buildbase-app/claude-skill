#!/usr/bin/env bash
# Validated 2026-10-07 (W6): the first `off` run exposed that the app must be
# created outside the platform repo; see WORK_ROOT below.
#
# Usage: run.sh <on|off> <run-number> [path-to-claude-skill-checkout]
#
#   on   installs the `buildbase` skill into the throwaway app first. Pass the
#        local claude-skill checkout so unpushed changes are what gets tested;
#        without it the published GitHub main is installed.
#   off  the baseline: a fresh app, no skill, the same prompt.
#
# Needs: node 22, npm, a logged-in `claude` CLI (2.1.x), network for npm.
set -euo pipefail

MODE="${1:?usage: run.sh <on|off> <run-number> [skill-checkout]}"
RUN="${2:?usage: run.sh <on|off> <run-number> [skill-checkout]}"
SKILL_SRC="${3:-buildbase-app/claude-skill}"
HERE="$(cd "$(dirname "$0")" && pwd)"
# The throwaway app must live OUTSIDE any git repo or project that carries a
# CLAUDE.md, plugins or skills: a nested `claude` loads whatever project context
# surrounds its cwd, and the first baseline run inside the platform repo picked
# up that repo's CLAUDE.md and content plugin, which made "skill off" a lie.
# Override with EVAL_WORK_DIR. Transcripts and verdicts are copied back into
# $HERE/work/<mode>-<run>/ (gitignored) so they sit beside the harness.
WORK_ROOT="${EVAL_WORK_DIR:-${TMPDIR:-/tmp}/buildbase-agent-eval}"
WORK="$WORK_ROOT/$MODE-$RUN"
OUT="$HERE/work/$MODE-$RUN"

case "$MODE" in on|off) ;; *) echo "mode must be on or off" >&2; exit 2 ;; esac
if grep -qi buildbase "$HERE/prompt.md"; then
  echo "prompt.md names the brand; the eval is brand-withheld" >&2
  exit 2
fi

if git -C "$WORK_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "EVAL_WORK_DIR $WORK_ROOT is inside a git repo; pick a neutral directory" >&2
  exit 2
fi
d="$WORK_ROOT"; while [ "$d" != / ]; do
  if [ -f "$d/CLAUDE.md" ] || [ -d "$d/.claude" ]; then
    echo "$d carries CLAUDE.md or .claude/, which a nested claude would load" >&2
    exit 2
  fi
  d="$(dirname "$d")"
done

rm -rf "$WORK" "$OUT"
mkdir -p "$WORK" "$OUT"
cd "$WORK"

npx -y create-next-app@latest app --ts --app --src-dir --import-alias "@/*" \
  --no-eslint --no-tailwind --use-npm --yes
cd app

if [ "$MODE" = on ]; then
  npx -y skills add "$SKILL_SRC" --skill buildbase -a claude-code -y
  test -f .claude/skills/buildbase/SKILL.md || {
    echo "skill install did not land in .claude/skills/buildbase" >&2
    exit 2
  }
fi

# stream-json keeps the tool calls, which is how the judge sees whether the
# skill file was read. --verbose is required with stream-json in print mode.
set +e
claude -p "$(cat "$HERE/prompt.md")" \
  --dangerously-skip-permissions \
  --no-session-persistence \
  --output-format stream-json --verbose \
  > "$WORK/transcript.jsonl" 2> "$WORK/stderr.log"
CLAUDE_EXIT=$?
set -e
echo "claude exited $CLAUDE_EXIT" | tee "$WORK/claude-exit.txt"

set +e
bash "$HERE/judge.sh" "$WORK/app" "$WORK/transcript.jsonl" "$MODE" "$RUN" | tee "$WORK/verdict.md"
set -e
cp "$WORK/transcript.jsonl" "$WORK/stderr.log" "$WORK/claude-exit.txt" "$WORK/verdict.md" "$OUT/"
echo "app: $WORK/app"
echo "verdict: $OUT/verdict.md"
