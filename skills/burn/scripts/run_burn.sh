#!/usr/bin/env sh
# Start a scheduled Burn Rate run, if one is due. For the Claude Code CLI and Codex.
# (Claude Desktop uses its own scheduled tasks and doesn't need this.)
#
# Schedule this every hour. Each time it asks `usage.py gate` whether a burn slot is due.
# Most hours the answer is no, and it exits without starting an agent, so it costs nothing.
#
#   run_burn.sh            check the gate, run if due
#   run_burn.sh --force    skip the gate and run now
#
# Environment (all optional):
#   BURN_RATE_HOME   burn home (default ~/.burn-rate)
#   BURN_CLAUDE_BIN  path to the claude binary (default: found on PATH)
#   BURN_CODEX_BIN   path to the codex binary (default: found on PATH)
#
# Output goes to <burn home>/logs/YYYY-MM-DD.log.

set -eu

home="${BURN_RATE_HOME:-$HOME/.burn-rate}"
export BURN_RATE_HOME="$home"
scripts="$(cd "$(dirname "$0")" && pwd)"
py="$(command -v python3 || command -v python || true)"
prompt="Use the burn skill to do a scheduled Burn Rate run."

mkdir -p "$home/logs"
log="$home/logs/$(date -u +%Y-%m-%d).log"
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$log"; }

if [ -z "$py" ]; then say "no python found; can't check the gate"; exit 1; fi
if [ ! -f "$home/config.toml" ]; then say "no config.toml in $home; run burn-setup first"; exit 1; fi

platform="$("$py" -c 'import sys,tomllib;print(tomllib.load(open(sys.argv[1],"rb")).get("platform",""))' "$home/config.toml")"

if [ "${1:-}" != "--force" ]; then
  verdict="$("$py" "$scripts/usage.py" gate)"
  say "gate: $(echo "$verdict" | tr -d '\n' | tr -s ' ')"
  case "$verdict" in
    *'"run": true'*) ;;
    *) exit 0 ;;
  esac
fi

cd "$home"
case "$platform" in
  codex)
    bin="${BURN_CODEX_BIN:-$(command -v codex)}"
    say "starting codex run"
    "$bin" --search exec --skip-git-repo-check --approve-for-me \
      -c sandbox_workspace_write.network_access=true -C "$home" "$prompt" < /dev/null >> "$log" 2>&1 \
      || say "codex exited with $?"
    ;;
  claude-cli)
    bin="${BURN_CLAUDE_BIN:-$(command -v claude)}"
    say "starting claude run"
    "$bin" -p "$prompt" --permission-mode acceptEdits < /dev/null >> "$log" 2>&1 \
      || say "claude exited with $?"
    ;;
  claude-desktop)
    say "platform is claude-desktop: use Desktop scheduled tasks, not this script"; exit 1 ;;
  *)
    say "unknown platform '$platform' in config.toml"; exit 1 ;;
esac
say "run finished"
