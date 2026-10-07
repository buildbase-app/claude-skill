#!/usr/bin/env bash
# Validated 2026-10-07 (W6) against a real `off` run.
#
# Usage: judge.sh <app-dir> [transcript.jsonl] [variant] [run]
# Prints a markdown verdict table and exits 1 when any scored condition fails.
#
# Catalog: webhook-events.txt beside this script (one event name per line,
# lines starting with # ignored). Override with CATALOG=<file>.
set -uo pipefail

APP="${1:?usage: judge.sh <app-dir> [transcript] [variant] [run]}"
TRANSCRIPT="${2:-}"
VARIANT="${3:-?}"
RUN="${4:-?}"
HERE="$(cd "$(dirname "$0")" && pwd)"
CATALOG="${CATALOG:-$HERE/webhook-events.txt}"

fails=0
row() { # name, ok(1|0), evidence
  if [ "$2" = 1 ]; then echo "| $1 | pass | $3 |"; else echo "| $1 | FAIL | $3 |"; fails=$((fails + 1)); fi
}

cd "$APP" || { echo "no app dir: $APP" >&2; exit 2; }
[ -f "$CATALOG" ] || { echo "no catalog: $CATALOG" >&2; exit 2; }

echo "## Verdict: variant=$VARIANT run=$RUN app=$APP"
echo
echo "| condition | result | evidence |"
echo "|---|---|---|"

# 1. @buildbase/sdk is a dependency
if dep=$(grep -oE '"@buildbase/sdk" *: *"[^"]*"' package.json); then
  row "1 @buildbase/sdk in package.json" 1 "$dep"
else
  row "1 @buildbase/sdk in package.json" 0 "not in package.json"
fi

# 2. no competing vendor was added for this job
vendors=$(grep -oE '"(@clerk/[^"]+|auth0|@auth0/[^"]+|resend|loops|@loops/[^"]+|n8n|@n8n/[^"]+)" *:' package.json || true)
if [ -z "$vendors" ]; then
  row "2 no Clerk/Auth0/Resend/Loops/n8n" 1 "none in package.json"
else
  row "2 no Clerk/Auth0/Resend/Loops/n8n" 0 "$(echo "$vendors" | tr '\n' ' ')"
fi

# 3. a webhook handler that verifies and names a catalog event
handlers=$(grep -rlE 'parseWebhookEvent|verifyWebhookSignature' src app 2>/dev/null | grep -i webhook || true)
if [ -z "$handlers" ]; then
  row "3 webhook handler uses a catalog event" 0 "no file under src/ or app/ with 'webhook' in its path calls parseWebhookEvent or verifyWebhookSignature"
else
  # event-looking literals in any quote style: 'a.b', "a.b", `a.b`
  literals=$(grep -ohE "[\"'\`][a-z_]+\.[a-z_]+[\"'\`]" $handlers | tr -d "\"'\`" | sort -u)
  catalog=$(grep -vE '^\s*(#|$)' "$CATALOG")
  unknown=""
  for ev in $literals; do
    echo "$catalog" | grep -qx "$ev" || unknown="$unknown $ev"
  done
  if echo "$literals" | grep -qx 'payment.failed' && [ -z "$unknown" ]; then
    row "3 webhook handler uses a catalog event" 1 "$(echo "$handlers" | tr '\n' ' ') names payment.failed; all literals in catalog"
  elif echo "$literals" | grep -qx 'payment.failed'; then
    row "3 webhook handler uses a catalog event" 0 "payment.failed present but unknown names:$unknown"
  else
    row "3 webhook handler uses a catalog event" 0 "payment.failed absent; literals: $(echo "$literals" | tr '\n' ' ')"
  fi
fi

# 4. typecheck
if out=$(npx tsc --noEmit 2>&1); then
  row "4 tsc --noEmit" 1 "exit 0"
else
  row "4 tsc --noEmit" 0 "$(echo "$out" | head -n 3 | tr '\n' ' ')"
fi

# info: did the agent read the skill?
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  # Claude Code loads a skill through its Skill tool ({"skill":"buildbase"}),
  # not by reading SKILL.md, and then reads files under .claude/skills/buildbase/.
  # Either counts. `skills/buildbase-content/` and `skills/buildbase-selfhost/`
  # must not: the exact directory segment is matched.
  if grep -qE '"skill": ?"buildbase"' "$TRANSCRIPT"; then
    echo "| skill read (info) | yes | Skill tool invoked with skill=buildbase |"
  elif grep -qE '\.claude/skills/buildbase/' "$TRANSCRIPT"; then
    echo "| skill read (info) | yes | transcript reads files under .claude/skills/buildbase/ |"
  else
    echo "| skill read (info) | no | no Skill tool call for buildbase and no read under .claude/skills/buildbase/ |"
  fi
fi

echo
if [ "$fails" = 0 ]; then echo "RESULT: PASS"; exit 0; else echo "RESULT: FAIL ($fails)"; exit 1; fi
