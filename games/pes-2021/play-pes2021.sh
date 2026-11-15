#!/usr/bin/env bash
# eFootball PES 2021 launcher: default Wine prefix (~/.wine), DXVK, NVIDIA GPU.
# Usage: ./play-pes2021.sh            run the game
#        ./play-pes2021.sh hud        run the game with an FPS overlay
#        ./play-pes2021.sh settings   open the game's Settings.exe
#        ./play-pes2021.sh pads       open the Wine controller test window
cd "$(dirname "$(readlink -f "$0")")" || exit 1

export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
export WINEDEBUG="${WINEDEBUG:--all}"

# Run on the RTX 3050 Ti instead of the Intel iGPU
export __NV_PRIME_RENDER_OFFLOAD=1
export __VK_LAYER_NV_optimus=NVIDIA_only
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export DXVK_LOG_LEVEL="${DXVK_LOG_LEVEL:-none}"
export DXVK_CONFIG_FILE="$PWD/dxvk.conf"

# Keep compiled shaders between runs so their stutter only happens once
export __GL_SHADER_DISK_CACHE=1
export __GL_SHADER_DISK_CACHE_SKIP_CLEANUP=1

# Pads: the map shared with the other games, set in Controller Settings
# (the game's own Settings tool cannot list pads under Wine Mono)
source /media/Games/common/pads.sh

# Rumble, for every pad the game uses: PES sends short, weak pulses that the
# Twin USB pads cannot feel, so common/rumble-boost raises any vibration to at
# least RUMBLE_BOOST_FLOOR % (0 = no boost), sends it to both motors
# (RUMBLE_BOOST_MIX=1) and makes each pulse last RUMBLE_BOOST_MIN_MS or more.
# Wine reads these only when the prefix starts, so restart PES after a change.
export RUMBLE_BOOST_FLOOR="${RUMBLE_BOOST_FLOOR:-75}"
export RUMBLE_BOOST_MIX="${RUMBLE_BOOST_MIX:-1}"
export RUMBLE_BOOST_MIN_MS="${RUMBLE_BOOST_MIN_MS:-400}"
export LD_LIBRARY_PATH="/media/Games/common/rumble-boost${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

case "$1" in
    settings) exec wine Settings.exe ;;
    pads)     exec wine control joy.cpl ;;
    hud)      export DXVK_HUD=fps,frametimes,gpuload; shift ;;
esac

# 0-11 are the i7-12700H P-cores; on the E-cores (12-19) the game's worker
# threads fall behind and the match stutters
exec python3 game-session.py taskset -c 0-11 gamemoderun wine PES2021.exe "$@"
