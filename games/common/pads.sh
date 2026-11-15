# Pad setup shared by every game launcher. Source it after WINEPREFIX is set:
# Wine reads the pad map only when a prefix starts, so it holds for every game
# in that prefix.
# pad_maps.py says what each pad got in ~/.cache/wine-games/pads.log, and
# Controller Settings (pad-settings.py) changes any pad's buttons.
PAD_LOG="$HOME/.cache/wine-games/pads.log"
mkdir -p "${PAD_LOG%/*}"
echo "== $(date '+%F %T') $WINEPREFIX" >>"$PAD_LOG"
eval "$(python3 -I "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/pad_maps.py" 2>>"$PAD_LOG")"
