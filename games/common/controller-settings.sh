#!/usr/bin/env bash
# Controller Settings, started from its Steam shortcut through steam-launch.sh.
# It reads the pads the way the game launchers do, so what it shows is what
# the games get. Log: ~/.cache/wine-games/pad-settings.log
LOG_DIR="$HOME/.cache/wine-games"
mkdir -p "$LOG_DIR"
exec python3 -I "$(dirname "$(readlink -f "$0")")/pad-settings.py" >"$LOG_DIR/pad-settings.log" 2>&1
