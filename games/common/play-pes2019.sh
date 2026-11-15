#!/usr/bin/env bash
# PES 2019 launcher, the shared setup is in game-env.sh.
# Usage: ./play-pes2019.sh            run the game
#        ./play-pes2019.sh hud        run the game with an FPS overlay
#        ./play-pes2019.sh settings   open the game's Settings.exe
#        ./play-pes2019.sh pads       open the Wine controller test window
export GAME_NAME="PES 2019"
GAME_ID=pes2019
source "$(dirname "$(readlink -f "$0")")/game-env.sh"
cd "$GAMES/PES-2019" || exit 1

# Rumble, as in PES 2021 (same engine, same short weak pulses): common/rumble-boost
# raises any vibration to at least RUMBLE_BOOST_FLOOR % (0 = no boost), sends it
# to both motors and makes each pulse last RUMBLE_BOOST_MIN_MS or more.
# Wine reads these only when the prefix starts.
export RUMBLE_BOOST_FLOOR="${RUMBLE_BOOST_FLOOR:-75}"
export RUMBLE_BOOST_MIX="${RUMBLE_BOOST_MIX:-1}"
export RUMBLE_BOOST_MIN_MS="${RUMBLE_BOOST_MIN_MS:-400}"
export LD_LIBRARY_PATH="$COMMON/rumble-boost${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

export DXVK_CONFIG_FILE="$COMMON/dxvk-pes2019.conf"

case "$1" in
    settings) exec wine Settings.exe ;;
    pads)     exec wine control joy.cpl ;;
    hud)      export DXVK_HUD=fps,frametimes,gpuload; shift ;;
esac

# The ~45 s white screen at start was split locks in the copy protection, which
# cost 7x more on the P-cores: pes2019-cores.py runs start-up on the E-cores and
# pes2019-stack-fix.py (already applied to the exe) makes fewer of them split.
mkdir -p "$LOG_DIR"
python3 "$COMMON/pes2019-cores.py" </dev/null >"$LOG_DIR/pes2019-cores.log" 2>&1 &

run_game PES2019.exe "$@"
