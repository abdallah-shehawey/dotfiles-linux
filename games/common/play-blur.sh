#!/usr/bin/env bash
# Blur launcher, the shared setup is in game-env.sh.
# Usage: ./play-blur.sh           run the game
#        ./play-blur.sh pads      open the Wine controller test window
#        ./play-blur.sh wined3d   run the game on Wine's own D3D9 instead of DXVK
export GAME_NAME="Blur"
GAME_ID=blur
source "$(dirname "$(readlink -f "$0")")/game-env.sh"
cd "$GAMES/Blur" || exit 1

# Blur.exe is 32-bit and Fedora's wine-dxvk is 64-bit only, so the d3d9.dll in
# the game folder is the 32-bit DXVK copied from Proton Experimental
case "$1" in
    pads)    exec wine control joy.cpl ;;
    wined3d) shift ;;
    *)       export WINEDLLOVERRIDES="d3d9=n,b" ;;
esac

run_game Blur.exe "$@"
