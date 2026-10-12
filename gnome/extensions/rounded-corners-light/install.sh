#!/usr/bin/env bash
# Installs rounded-corners-light@local into the user's GNOME Shell and
# enables it. GNOME imports an extension's code once per session, so the
# new code runs only after a log out and back in (Wayland has no Alt+F2 r).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uuid=rounded-corners-light@local
dest="$HOME/.local/share/gnome-shell/extensions/$uuid"

if [ -d "$dest" ]; then
  stamp="$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$HOME/.local/state/rounded-corners"
  cp -a "$dest" "$HOME/.local/state/rounded-corners/installed-before-$stamp"
  echo "kept the installed copy in ~/.local/state/rounded-corners/installed-before-$stamp"
fi
mkdir -p "$dest"
install -m 644 "$here/$uuid"/{extension.js,metadata.json,README.md} "$dest/"
gnome-extensions enable "$uuid" 2>/dev/null || true
echo "installed $uuid revision $(python3 -c "import json;print(json.load(open('$dest/metadata.json'))['version'])")"
echo "Log out and back in to load it."
