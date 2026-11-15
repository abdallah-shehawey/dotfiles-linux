#!/usr/bin/env bash
# WWE 2K Battlegrounds launcher, the shared setup is in game-env.sh.
# Usage: ./play-wwe2k-battlegrounds.sh        run the game
#        ./play-wwe2k-battlegrounds.sh hud    run the game with an FPS overlay
#        ./play-wwe2k-battlegrounds.sh pads   open the Wine controller test window
export GAME_NAME="WWE 2K Battlegrounds"
GAME_ID=wwe2k-battlegrounds
source "$(dirname "$(readlink -f "$0")")/game-env.sh"
cd "$GAMES/WWE-2K-Battlegrounds" || exit 1

case "$1" in
    pads) exec wine control joy.cpl ;;
    hud)  export DXVK_HUD=fps,frametimes,gpuload; shift ;;
esac

run_game WWEBattlegrounds.exe "$@"
