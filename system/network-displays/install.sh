#!/usr/bin/env bash
# Low-latency launcher for GNOME Network Displays (Miracast to a TV).
#   ./install.sh               build the shim, add the menu launcher
#   ./install.sh --uninstall   remove both
# GND_LATENCY_MS (default 20) sets the sender buffer the launcher uses.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
lib="$HOME/.local/lib/gnd-low-latency"
desk="$HOME/.local/share/applications/org.gnome.NetworkDisplays.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -rf "$lib" "$desk"
    update-desktop-database -q "$HOME/.local/share/applications" 2>/dev/null || true
    echo "removed"; exit 0
fi

ms="${GND_LATENCY_MS:-20}"
mkdir -p "$lib" "$(dirname "$desk")"
cp "$here/gnd-low-latency.c" "$lib/"
gcc -O2 -shared -fPIC -o "$lib/gnd-low-latency.so" "$lib/gnd-low-latency.c" -ldl

# Same entry as the RPM's, so the menu shows one app; only Exec differs.
sed -e "s|^Exec=.*|Exec=env GND_LATENCY_MS=$ms LD_PRELOAD=$lib/gnd-low-latency.so gnome-network-displays|" \
    /usr/share/applications/org.gnome.NetworkDisplays.desktop > "$desk"
update-desktop-database -q "$HOME/.local/share/applications" 2>/dev/null || true
echo "installed: buffer ${ms} ms"
