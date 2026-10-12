#!/bin/sh
# nest.py loads the owner's GNOME settings from dconf/*.dconf. They are not
# committed (they carry paired-device ids and shell history); run this once
# on the machine to take them from the live session.
set -eu
cd "$(dirname "$0")"
mkdir -p dconf
dconf dump /org/gnome/shell/ > dconf/shell.dconf
dconf dump /org/gnome/desktop/interface/ > dconf/interface.dconf
dconf dump /org/gnome/desktop/background/ > dconf/background.dconf
dconf dump /org/gnome/desktop/wm/ > dconf/wm.dconf
dconf dump /org/gnome/mutter/ > dconf/mutter.dconf
dconf dump /org/gnome/desktop/peripherals/ > dconf/peripherals.dconf
echo "dconf snapshot written to $(pwd)/dconf"
