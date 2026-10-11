#!/usr/bin/env bash
# Installs the reviewed Chakra Switch snapshots to ~/.local/share/chakra-switch-local,
# the user path unit that re-applies them after every extension update, and
# applies them once now. Install chakra-switch@narkagni itself first.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="$HOME/.local/share/chakra-switch-local"
units="$HOME/.config/systemd/user"

mkdir -p "$dest" "$units"
for f in apply.py README.md known-sources.json ChakraSwitcher.local.js \
         chakra-switch.gschema.local.xml DiagonalBlade.carousel.js \
         extension.local.js PeekView.coverflow.js prefs.local.js; do
  cp "$here/$f" "$dest/$f"
done
chmod +x "$dest/apply.py"
cp "$here/systemd/chakra-switch-repatch.path" "$here/systemd/chakra-switch-repatch.service" "$units/"
systemctl --user daemon-reload
systemctl --user enable --now chakra-switch-repatch.path
"$dest/apply.py" || true
echo "Log out and back in to load the patched extension."
