#!/usr/bin/env bash
# Checks the whole game setup and changes NOTHING. ✓ = fine, ✗ = broken (the
# line says what to do or which README covers it), ! = worth a look.
#   ./check.sh            everything
#   ./check.sh --quiet    only the ✗ and ! lines
# Exit code: 0 when there is no ✗. GAMES_DIR=/path uses another games folder.
set -u
source "$(dirname "$(readlink -f "$0")")/lib.sh"
QUIET=0; [[ ${1:-} == --quiet ]] && QUIET=1
FAILS=0
yes_() { [[ $QUIET == 1 ]] || ok "$@"; }
no_()  { bad "$@"; FAILS=$((FAILS + 1)); }
row()  { local text=$1; shift; if "$@" >/dev/null 2>&1; then yes_ "$text"; else no_ "$text"; fi; }
# `row` with a hint on failure: hint "text" "fix" command...
hint() { local text=$1 fix=$2; shift 2; if "$@" >/dev/null 2>&1; then yes_ "$text"; else no_ "$text  → $fix"; fi; }
same() { cmp -s "$1" "$2"; }

part "A. Programs"
if command -v rpm >/dev/null; then
    for p in "${PACKAGES[@]}"; do hint "package $p" "sudo dnf install $p" rpm -q "$p"; done
fi
[[ $QUIET == 1 ]] || info "$(wine --version 2>/dev/null), kernel $(uname -r)"
if lspci -d 10de: 2>/dev/null | grep -qE 'VGA|3D|Display'; then
    hint "NVIDIA driver loaded" "AI-PROMPT section 3, step 3" test -e /proc/driver/nvidia/version
fi
hint "Steam opened and signed in once" "open Steam, sign in, Steam > Exit" python3 -I "$STEAM_TOOL" check

part "B. Performance (split locks, CPU, screen)"
hint "in the gamemode group" "sudo usermod -aG gamemode \$USER, then restart" in_gamemode_group
hint "gamemode group active in this session" "restart the laptop" bash -c 'id -nG | tr " " "\n" | grep -qx gamemode'
hint "~/.config/gamemode.ini has defaultgov=powersave" "copy games/config/gamemode.ini" grep -q '^defaultgov=powersave' "$HOME/.config/gamemode.ini"
slm=$(cat /proc/sys/kernel/split_lock_mitigate 2>/dev/null || echo n/a)
if [[ -n $(running_games) ]]; then
    if [[ $slm == 0 ]]; then yes_ "split_lock_mitigate = 0 while $(running_games | head -1) runs"
    else no_ "split_lock_mitigate = $slm while a game runs → GameMode is not switching it off (performance/README.md)"; fi
else
    [[ $QUIET == 1 ]] || info "split_lock_mitigate = $slm (1 is normal with no game running; must be 0 during a game)"
fi
if [[ -r /sys/devices/cpu_core/cpus ]]; then
    pc=$(cat /sys/devices/cpu_core/cpus)
    if [[ $pc == 0-11 ]]; then yes_ "P-cores are 0-11 (what the launchers pin to)"
    else no_ "P-cores are $pc, launchers pin to 0-11 → change taskset in common/game-env.sh and pes-2021/play-pes2021.sh"; fi
fi

part "C. Games folder and launchers"
hint "$GAMES exists" "AI-PROMPT section 5, step 1" test -d "$GAMES"
[[ $QUIET == 1 ]] || info "$GAMES is $(findmnt -no FSTYPE --target "$GAMES" 2>/dev/null || echo '?')"
for line in "${GAME_TABLE[@]}"; do
    game_fields "$line"
    hint "$NAME: $FOLDER/$EXE" "the owner must put the game folder there" test -f "$GAMES/$FOLDER/$EXE"
done
while IFS= read -r -d '' f; do
    rel=${f#"$HERE/common/"}
    if [[ ! -f $COMMON/$rel ]]; then no_ "common/$rel missing → ./install.sh"
    elif ! same "$f" "$COMMON/$rel"; then warn "common/$rel differs from the repo (changed on the laptop, or repo is newer: ./install.sh copies the repo's)"
    else yes_ "common/$rel"; fi
done < <(find "$HERE/common" -type f -print0)
for f in steam-launch.sh play-pes2019.sh play-blur.sh play-wwe2k-battlegrounds.sh controller-settings.sh; do
    hint "common/$f is executable" "chmod +x $COMMON/$f" test -x "$COMMON/$f"
done
P21="$GAMES/eFootball-PES-2021"
if [[ -d $P21 ]]; then
    for f in play-pes2021.sh dxvk.conf game-session.py; do
        if [[ ! -f $P21/$f ]]; then no_ "PES 2021: $f missing in its folder → ./install.sh"
        elif ! same "$HERE/pes-2021/$f" "$P21/$f"; then warn "PES 2021: $f differs from the repo"
        else yes_ "PES 2021: $f"; fi
    done
    hint "PES 2021: play-pes2021.sh is executable" "chmod +x $P21/play-pes2021.sh" test -x "$P21/play-pes2021.sh"
fi
hint "rumble-boost built against $(real_sdl2)" "$COMMON/rumble-boost/build.sh" rumble_fresh

part "D. Wine prefixes and DXVK"
for P in "$HOME/.wine" "$HOME/.wine-games"; do
    hint "prefix $P" "./install.sh creates it" test -f "$P/system.reg"
done
hint "~/.wine-games: Wine makes no app-menu entries" "./install.sh" grep -q '"winemenubuilder.exe"=""' "$HOME/.wine-games/user.reg"
hint "64-bit DXVK active (wine-dxvk alternatives)" "sudo dnf install wine-dxvk" bash -c "alternatives --list | grep -qE 'wine-d3d11\(x86-64\).*dxvk-d3d11'"
hint "DXVK configs: maxFrameLatency 1, no frame limiter" "restore common/dxvk.conf" grep -q 'dxgi.maxFrameRate = -1' "$COMMON/dxvk.conf"
if [[ -d $GAMES/Blur ]]; then
    hint "Blur: 32-bit DXVK d3d9.dll in its folder" "blur/README.md step 1" test -f "$GAMES/Blur/d3d9.dll"
    hint "Blur: launcher sets d3d9=n,b" "restore common/play-blur.sh" grep -q 'WINEDLLOVERRIDES="d3d9=n,b"' "$COMMON/play-blur.sh"
    hint "Blur: msvcr90 = native,builtin (crash fix)" "blur/README.md step 2" grep -qi 'AppDefaults\\\\Blur.exe\\\\DllOverrides' "$HOME/.wine-games/user.reg"
    hint "Blur: Microsoft's msvcr90 9.0.21022.8 in the prefix" "WINEPREFIX=~/.wine-games winetricks -q vcrun2008" \
        bash -c "ls '$HOME/.wine-games/drive_c/windows/winsxs' | grep -qi 'x86_microsoft.vc90.crt_.*9.0.21022.8'"
fi
if [[ -f $GAMES/PES-2019/PES2019.exe ]]; then
    st=$(PES2019_EXE="$GAMES/PES-2019/PES2019.exe" python3 -I "$COMMON/pes2019-stack-fix.py" status 2>&1)
    if [[ $st == patched* ]]; then yes_ "PES 2019: start-up stack fix ($st)"; else no_ "PES 2019: stack fix is '$st' → pes-2019/README.md"; fi
    hint "PES 2019: dxgi.hideNvidiaGpu = False (white screen fix)" "restore common/dxvk-pes2019.conf" grep -q '^dxgi.hideNvidiaGpu = False' "$COMMON/dxvk-pes2019.conf"
    hint "PES 2019: launcher uses dxvk-pes2019.conf" "restore common/play-pes2019.sh" grep -q 'dxvk-pes2019.conf' "$COMMON/play-pes2019.sh"
    hint "PES 2019: launcher starts pes2019-cores.py (E-core start-up)" "restore common/play-pes2019.sh" grep -q 'pes2019-cores.py' "$COMMON/play-pes2019.sh"
    hint "PES 2019: Arabic commentary files in Data/" "the game's Arabic language pack" bash -c "ls '$GAMES/PES-2019/Data/' | grep -qi 'dt41_ara_all.cpk'"
fi

part "E. Controllers"
hint "button map ~/.config/game-pads/mappings.txt" "./install.sh" test -s "$HOME/.config/game-pads/mappings.txt"
hint "session pad database" "./install.sh" test -s "$HOME/.config/game-pads/gamecontrollerdb.txt"
hint "~/.config/environment.d/60-game-pads.conf" "./install.sh" test -f "$HOME/.config/environment.d/60-game-pads.conf"
hint "game-env.sh (PES 2019, Blur, WWE) sources pads.sh" "restore common/game-env.sh" grep -q 'source "$COMMON/pads.sh"' "$COMMON/game-env.sh"
[[ -d $P21 ]] && hint "play-pes2021.sh sources pads.sh" "restore pes-2021/play-pes2021.sh" grep -q 'pads.sh' "$P21/play-pes2021.sh"
pads=$(python3 -I "$COMMON/pad_maps.py" --json 2>/dev/null | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null)
if [[ ${pads:-0} -gt 0 ]]; then yes_ "$pads pad(s) connected and mapped"; else warn "no pads connected right now (plug them in to test)"; fi
python3 -I -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); from gi.repository import Adw" 2>/dev/null \
    && yes_ "Controller Settings can start (GTK4 + libadwaita)" || no_ "Controller Settings cannot start: GTK4/libadwaita for Python missing → sudo dnf install python3-gobject gtk4 libadwaita"

part "Game settings"
for line in "${GAME_TABLE[@]}"; do
    game_fields "$line"
    [[ -z $KONAMI_DIR ]] && continue
    F="$KONAMI/$KONAMI_DIR/settings.dat"
    if [[ ! -f $F ]]; then no_ "$NAME: no settings.dat → ./install.sh"; continue; fi
    size=$(stat -c %s "$F"); want=${DAT_SIZE[$REPO_DIR]}
    if [[ $size != "$want" ]]; then no_ "$NAME: settings.dat is $size bytes, the game needs $want → ./install.sh"; continue; fi
    desc=$(python3 -I "$SETTINGS_TOOL" show "$F" | sed -n 's/^resolution: *//p;s/^flags:.*full screen: \(.*\))/full screen \1/p' | paste -sd' ')
    yes_ "$NAME: settings.dat $desc"
    save=$(find "$KONAMI/$KONAMI_DIR" -mindepth 2 -maxdepth 2 -type d -name save 2>/dev/null | head -1)
    if [[ -n $save && -f $save/SYSTEM00000000 ]]; then yes_ "$NAME: in-game settings save exists"
    else warn "$NAME: no in-game settings yet (start the game once, then ./install.sh --restore-settings)"; fi
done

WIN_USER="$HOME/.wine-games/drive_c/users/$USER/AppData"
for pair in "Blur|$WIN_USER/Roaming/bizarre creations/blur/settings.xml" \
            "WWE 2K Battlegrounds|$WIN_USER/Local/WWEPlaygrounds/Saved/Config/WindowsNoEditor/GameUserSettings.ini"; do
    IFS='|' read -r label f <<<"$pair"
    if [[ -f $f ]]; then yes_ "$label: settings file $(grep -o -E '(width="[0-9]+" height="[0-9]+"|ResolutionSizeX=[0-9]+)' "$f" | head -1)"
    else warn "$label: no settings file yet (the game writes one on first start; ./install.sh --restore-settings puts the owner's)"; fi
done

part "F. Steam library"
if python3 -I "$STEAM_TOOL" check >/dev/null 2>&1; then
    SHOW=$(python3 -I "$STEAM_TOOL" show 2>/dev/null)
    for line in "${GAME_TABLE[@]}" "|Controller Settings|||$COMMON/controller-settings.sh|||local.games.PadSettings|local.games.PadSettings|"; do
        game_fields "$line"
        if msg=$(shortcut_state "$NAME" "$LAUNCHER" <<<"$SHOW"); then yes_ "Steam: $NAME $msg"
        else no_ "Steam: $NAME: $msg → ./install.sh (Steam closed)"; fi
        hint "dock icon entry $DESKTOP_ID.desktop" "./install.sh (Steam closed)" test -f "$APPS/$DESKTOP_ID.desktop"
        hint "icon $ICON_NAME.png" "./install.sh (Steam closed)" test -f "$ICON_DIR/$ICON_NAME.png"
        if [[ -n $WMCLASS && -f $APPS/$DESKTOP_ID.desktop ]]; then
            hint "$DESKTOP_ID.desktop matches window class $WMCLASS" "./install.sh" grep -qix "StartupWMClass=$WMCLASS" "$APPS/$DESKTOP_ID.desktop"
        fi
    done
fi

echo
if [[ $FAILS == 0 ]]; then
    echo "${B}${G}All checks passed.${N} Not checkable from here: how each game plays. Press Play in Steam."
else
    echo "${B}${R}$FAILS problem(s).${N} Fix them (./install.sh fixes most), or see AI-PROMPT.md section 9."
fi
exit $((FAILS > 0))
