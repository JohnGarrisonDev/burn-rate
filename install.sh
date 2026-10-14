#!/usr/bin/env sh
# Install the Burn Rate skills for Claude Code or Codex.
#
#   ./install.sh --platform claude            # user-wide: ~/.claude/skills
#   ./install.sh --platform codex             # user-wide: ~/.codex/skills
#   ./install.sh --platform claude --scope project --project /path/to/repo
#   ./install.sh --platform codex --link      # symlink instead of copy (handy if you hack on the skills)
#
# Running it again updates the skills in place. It only touches folders named burn*.

set -eu

platform=""
scope="user"
project="$(pwd)"
mode="copy"

usage() {
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --platform) platform="$2"; shift 2 ;;
    --scope) scope="$2"; shift 2 ;;
    --project) project="$2"; shift 2 ;;
    --link) mode="link"; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1"; usage 1 ;;
  esac
done

case "$platform" in
  claude)
    if [ "$scope" = "user" ]; then dest="$HOME/.claude/skills"; else dest="$project/.claude/skills"; fi ;;
  codex)
    if [ "$scope" = "user" ]; then dest="${CODEX_HOME:-$HOME/.codex}/skills"; else dest="$project/.agents/skills"; fi ;;
  *)
    echo "pick a platform: --platform claude or --platform codex"; exit 1 ;;
esac

src="$(cd "$(dirname "$0")" && pwd)/skills"
mkdir -p "$dest"

for skill in "$src"/burn*; do
  name="$(basename "$skill")"
  target="$dest/$name"
  rm -rf "$target"
  if [ "$mode" = "link" ]; then
    ln -s "$skill" "$target"
    echo "linked  $name -> $target"
  else
    cp -R "$skill" "$target"
    echo "copied  $name -> $target"
  fi
done

echo
echo "Done. Open $platform and run the burn-setup skill to get started."
