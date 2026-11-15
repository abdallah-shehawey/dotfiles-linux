# Shared setup for the games started from this folder, sourced by their launchers.
# They use their own prefix (~/.wine-games) because Wine reads the pad map only
# when a prefix starts, and it keeps the repacks away from ~/.wine.
COMMON="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
GAMES="$(dirname "$COMMON")"
LOG_DIR="$HOME/.cache/wine-games"

export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-games}"
export WINEDEBUG="${WINEDEBUG:-fixme-all}"

# Run on the RTX 3050 Ti instead of the Intel iGPU
export __NV_PRIME_RENDER_OFFLOAD=1
export __VK_LAYER_NV_optimus=NVIDIA_only
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export DXVK_LOG_LEVEL="${DXVK_LOG_LEVEL:-none}"
export DXVK_CONFIG_FILE="$COMMON/dxvk.conf"

# Keep compiled shaders between runs so their stutter only happens once
export __GL_SHADER_DISK_CACHE=1
export __GL_SHADER_DISK_CACHE_SKIP_CLEANUP=1

# Every pad with each button where a PlayStation pad has it. The games show
# Xbox letters on screen: A is Cross, B is Circle, X is Square, Y is Triangle.
source "$COMMON/pads.sh"

# Run the game in the current folder and log to $LOG_DIR/$GAME_ID.log.
# 0-11 are the i7-12700H P-cores. wineserver -w keeps the session open when the
# .exe only starts the real game and exits.
run_game() {
    mkdir -p "$LOG_DIR"
    exec python3 "$COMMON/game-session.py" taskset -c 0-11 gamemoderun \
        bash -c 'wine "$@"; wineserver -w' wine "$@" >"$LOG_DIR/$GAME_ID.log" 2>&1
}
