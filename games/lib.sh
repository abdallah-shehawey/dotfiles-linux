# Shared by install.sh and check.sh: where things are, and the game table.
# Override the games folder with GAMES_DIR=/path (default /media/Games).
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
GAMES="${GAMES_DIR:-/media/Games}"
COMMON="$GAMES/common"
LOG_DIR="$HOME/.cache/wine-games"
STEAM_TOOL="$HERE/tools/steam/steam-shortcut.py"
SETTINGS_TOOL="$HERE/tools/pes-settings-dat.py"
KONAMI="$HOME/Documents/KONAMI"
APPS="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
export GAMES_DIR="$GAMES"

# One line per game, fields separated by "|":
# repo dir | Steam name | game folder | exe Steam's --exe points at | launcher |
# prefix | window class | icon name | dock entry id | KONAMI folder (PES only)
GAME_TABLE=(
    "pes-2021|eFootball PES 2021|eFootball-PES-2021|PES2021.exe|$GAMES/eFootball-PES-2021/play-pes2021.sh|$HOME/.wine|pes2021.exe|3FAA_PES2021.0|game-pes-2021|eFootball PES 2021 SEASON UPDATE"
    "pes-2019|PES 2019|PES-2019|PES2019.exe|$COMMON/play-pes2019.sh|$HOME/.wine-games|pes2019.exe|pes-2019|game-pes-2019|PRO EVOLUTION SOCCER 2019"
    "blur|Blur|Blur|Blur.exe|$COMMON/play-blur.sh|$HOME/.wine-games|blur.exe|blur-game|game-blur|"
    "wwe-2k-battlegrounds|WWE 2K Battlegrounds|WWE-2K-Battlegrounds|WWEBattlegrounds.exe|$COMMON/play-wwe2k-battlegrounds.sh|$HOME/.wine-games|wweplaygrounds-win64-shipping.exe|wwe-2k-battlegrounds|game-wwe-2k-battlegrounds|"
)
# Read one table line into REPO_DIR NAME FOLDER EXE LAUNCHER PREFIX WMCLASS ICON_NAME DESKTOP_ID KONAMI_DIR
game_fields() {
    IFS='|' read -r REPO_DIR NAME FOLDER EXE LAUNCHER PREFIX WMCLASS ICON_NAME DESKTOP_ID KONAMI_DIR <<<"$1"
}
# settings.dat size each PES accepts
declare -A DAT_SIZE=([pes-2021]=612 [pes-2019]=352)

# The packages the setup needs (Fedora names)
PACKAGES=(steam wine wine-mono wine-dxvk winetricks gamemode gamemode.i686 sdl2-compat SDL3
          python3-gobject python3-cairo gtk4 libadwaita gcc zstd)

if [[ -t 1 ]]; then
    G=$'\e[32m' Y=$'\e[33m' R=$'\e[31m' B=$'\e[1m' D=$'\e[2m' N=$'\e[0m'
else
    G='' Y='' R='' B='' D='' N=''
fi
ok()   { echo "  ${G}✓${N} $*"; }
bad()  { echo "  ${R}✗${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; }
info() { echo "  ${D}$*${N}"; }
part() { echo; echo "${B}== $*${N}"; }

steam_running() { pgrep -x steam >/dev/null || pgrep -x steamwebhelper >/dev/null; }
in_gamemode_group() { getent group gamemode | cut -d: -f4 | tr ',' '\n' | grep -qx "$USER"; }
real_sdl2() { readlink -f /usr/lib64/libSDL2-2.0.so.0 2>/dev/null; }
# is rumble-boost built against the SDL2 file that is installed now?
rumble_fresh() {
    local so="$COMMON/rumble-boost/libSDL2-2.0.so.0" real
    real=$(real_sdl2)
    [[ -f $so && -n $real ]] && readelf -d "$so" 2>/dev/null | grep -qF "[$real]"
}
# Is the Steam shortcut NAME right? Reads `steam-shortcut.py show` on stdin.
# Prints "ok ..." (exit 0) or what is wrong (exit 1).
#   msg=$(shortcut_state "PES 2019" "$COMMON/play-pes2019.sh" <<<"$SHOW")
shortcut_state() {
    python3 -I -c '
import json, sys
name, launcher = sys.argv[1], sys.argv[2]
for line in sys.stdin:
    if not line.strip():
        continue
    s = json.loads(line)
    if s["name"] != name:
        continue
    if s["exe"].strip("\"").rsplit("/", 1)[-1] != "steam-launch.sh":
        sys.exit(print("target is " + s["exe"] + ", not common/steam-launch.sh") or 1)
    if s["launch"].strip("\"") != launcher:
        sys.exit(print("launch options are " + repr(s["launch"]) + ", not " + launcher) or 1)
    if s["overlay"] != 0:
        sys.exit(print("Steam overlay is on") or 1)
    missing = [k for k, v in s["art"].items() if not v]
    if missing:
        sys.exit(print("artwork missing: " + ", ".join(missing)) or 1)
    print("ok (appid " + str(s["appid"]) + ", Steam Input " + s["steam_input"] + ")")
    sys.exit(0)
sys.exit(print("no shortcut with this name") or 1)
' "$1" "$2"
}
# a game running from this setup? (comm names; never pgrep -f, see AI-PROMPT rule 8)
running_games() {
    ps -eo comm= | grep -E '^(PES2021\.exe|PES2019\.exe|Blur\.exe|WWEPlaygrounds-|WWEBattlegrounds)' | sort -u
}
