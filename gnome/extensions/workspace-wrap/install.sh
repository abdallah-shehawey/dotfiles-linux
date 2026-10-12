#!/usr/bin/env bash
# Installs workspace-wrap@local into the user's GNOME Shell and enables it.
# GNOME only finds a new extension when the shell starts, so it runs after a
# log out and back in (Wayland has no Alt+F2 r).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uuid=workspace-wrap@local
dest="$HOME/.local/share/gnome-shell/extensions/$uuid"

mkdir -p "$dest"
install -m 644 "$here/$uuid"/{extension.js,metadata.json} "$dest/"
gnome-extensions enable "$uuid" 2>/dev/null ||
  gsettings set org.gnome.shell enabled-extensions \
    "$(python3 -c "import ast,sys;l=ast.literal_eval(sys.argv[1].replace('@as ',''));print(l if '$uuid' in l else l+['$uuid'])" \
      "$(gsettings get org.gnome.shell enabled-extensions)")"
echo "installed $uuid. Log out and back in to load it."
