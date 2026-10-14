#!/usr/bin/env sh
# Install the Burn Rate skills for Claude Code or Codex.
#
#   ./install.sh --platform claude            # user-wide: ~/.claude/skills
#   ./install.sh --platform codex             # user-wide: ~/.codex/skills
#   ./install.sh --platform claude --scope project --project /path/to/folder
#   ./install.sh --platform codex --link      # symlink instead of copy (handy if you hack on the skills)
#
# Use user scope. Scheduled runs start in the burn home (~/.burn-rate), so project scope
# only works if that project folder is your burn home.
# On Windows (Git Bash), --link needs native symlinks; install.ps1 -Link is simpler there.
#
# Running it again updates the skills in place. It only touches folders named burn*.

set -eu

platform=""
scope="user"
project="$(pwd)"
mode="copy"
windows_link=""

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
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

if [ "$mode" = "link" ]; then
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      # Git Bash's ln -s copies by default. Ask for a real symlink, and fail if it can't make one.
      MSYS=winsymlinks:nativestrict
      CYGWIN=winsymlinks:nativestrict
      export MSYS CYGWIN
      windows_link=1 ;;
  esac
fi

mkdir -p "$dest"

for skill in "$src"/burn*; do
  name="$(basename "$skill")"
  target="$dest/$name"
  rm -rf "$target"
  if [ "$mode" = "link" ]; then
    if ! ln -s "$skill" "$target"; then
      if [ -n "${windows_link:-}" ]; then
        echo "Couldn't make a symlink. Windows needs Developer Mode (or an admin shell) for that."
        echo "Use the PowerShell installer instead: .\\install.ps1 -Platform $platform -Link"
      fi
      exit 1
    fi
    echo "linked  $name -> $target"
  else
    cp -R "$skill" "$target"
    echo "copied  $name -> $target"
  fi
done

echo
echo "Done. Open $platform and run the burn-setup skill to get started."
