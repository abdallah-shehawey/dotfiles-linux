#!/usr/bin/env bash
# Installs everything in this folder onto the laptop. Safe to run again: it only
# fixes what is missing or wrong, backs up what it replaces, and never deletes.
#
#   ./install.sh                         everything (Steam must be closed for the Steam part)
#   ./install.sh --no-steam              everything except the Steam library
#   ./install.sh --restore-settings      also put the owner's in-game settings back over
#                                        the current ones (PES: Arabic commentary, graphics;
#                                        Blur and WWE: screen and graphics)
#
# It never runs sudo. Anything that needs the password is printed at the end
# under "THE OWNER MUST DO", with the exact command. Then run ./check.sh.
# GAMES_DIR=/path ./install.sh uses another games folder (default /media/Games).
set -u
source "$(dirname "$(readlink -f "$0")")/lib.sh"

DO_STEAM=1 RESTORE=0
for a in "$@"; do
    case $a in
        --no-steam) DO_STEAM=0 ;;
        --restore-settings|--restore-pes-settings) RESTORE=1 ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "unknown option: $a (see --help)"; exit 2 ;;
    esac
done
[[ $EUID -eq 0 ]] && { echo "Run it as yourself, not with sudo."; exit 2; }

TODO=()
need() { TODO+=("$1"); bad "$2"; }
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$LOG_DIR/install-backup-$STAMP"
mkdir -p "$LOG_DIR"
# copy src to dst; a different existing dst is backed up first
put() {
    local src=$1 dst=$2
    if [[ -e $dst ]]; then
        cmp -s "$src" "$dst" && return 1
        mkdir -p "$BACKUP"
        cp -a "$dst" "$BACKUP/$(basename "$dst").$(echo "$dst" | md5sum | cut -c1-6)"
    fi
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
}
# wine reg add, then wait until wineserver has written the registry to disk
wreg() { WINEPREFIX=$1 WINEDEBUG=-all WINEDLLOVERRIDES="winemenubuilder.exe=d" wine reg add "${@:2}" /f >/dev/null 2>&1; WINEPREFIX=$1 timeout 60 wineserver -w 2>/dev/null; }

if [[ -n $(running_games) ]]; then
    echo "A game is running ($(running_games | tr '\n' ' ')). Close it first, then run this again."
    exit 2
fi

# ---------------------------------------------------------------- programs
part "A. Programs"
missing=()
if command -v rpm >/dev/null; then
    for p in "${PACKAGES[@]}"; do rpm -q "$p" >/dev/null 2>&1 || missing+=("$p"); done
    if rpm -q rpmfusion-nonfree-release >/dev/null 2>&1; then ok "RPM Fusion"; else
        need "sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-\$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-\$(rpm -E %fedora).noarch.rpm" "RPM Fusion is off (Steam comes from it)"
    fi
    if ((${#missing[@]})); then
        need "sudo dnf install ${missing[*]}" "missing packages: ${missing[*]}"
    else
        ok "all packages: ${PACKAGES[*]}"
    fi
else
    warn "not Fedora: install Steam, Wine (+mono), winetricks, GameMode, SDL2, SDL3, GTK4, libadwaita, python3-gobject/cairo, gcc by hand"
fi
HAVE_WINE=0; command -v wine >/dev/null && HAVE_WINE=1
if lspci -d 10de: 2>/dev/null | grep -qE 'VGA|3D|Display'; then
    if [[ -e /proc/driver/nvidia/version ]]; then ok "NVIDIA driver loaded"; else
        need "sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda   # then wait 5 minutes and restart" "NVIDIA card but no driver loaded"
    fi
fi

# ---------------------------------------------------------------- performance
part "B. Performance fix (split locks)"
if in_gamemode_group; then
    ok "in the gamemode group"
    id -nG | tr ' ' '\n' | grep -qx gamemode || need "restart the laptop (the gamemode group is not active in this session yet)" "gamemode group not active yet"
else
    need "sudo usermod -aG gamemode $USER   # then restart the laptop" "not in the gamemode group: games will stutter"
fi
if [[ ! -f $HOME/.config/gamemode.ini ]]; then
    put "$HERE/config/gamemode.ini" "$HOME/.config/gamemode.ini"; ok "~/.config/gamemode.ini installed"
elif grep -q '^defaultgov=powersave' "$HOME/.config/gamemode.ini"; then
    ok "~/.config/gamemode.ini has defaultgov=powersave"
else
    mkdir -p "$BACKUP"; cp -a "$HOME/.config/gamemode.ini" "$BACKUP/"
    printf '\n[general]\ndefaultgov=powersave\n' >>"$HOME/.config/gamemode.ini"
    ok "added defaultgov=powersave to ~/.config/gamemode.ini"
fi

# ---------------------------------------------------------------- files
part "C. Games folder and launchers"
if [[ ! -d $GAMES ]]; then
    need "mount the Games partition at $GAMES (AI-PROMPT section 5, step 1), then run ./install.sh again" "$GAMES does not exist"
    echo; echo "Stopping: nothing else can be installed without the games folder."; exit 1
fi
[[ -w $GAMES ]] || need "sudo chown $USER: $GAMES" "$GAMES is not writable"
ok "$GAMES ($(findmnt -no FSTYPE --target "$GAMES" 2>/dev/null || echo '?'))"
for line in "${GAME_TABLE[@]}"; do
    game_fields "$line"
    if [[ -f $GAMES/$FOLDER/$EXE ]]; then ok "$NAME: $GAMES/$FOLDER/$EXE"; else
        need "put $NAME's game folder at $GAMES/$FOLDER (the owner has the game files)" "$NAME: $GAMES/$FOLDER/$EXE not found"
    fi
done
changed=0
while IFS= read -r -d '' f; do
    rel=${f#"$HERE/common/"}
    put "$f" "$COMMON/$rel" && { info "updated common/$rel"; changed=1; }
done < <(find "$HERE/common" -type f -print0)
chmod +x "$COMMON"/*.sh "$COMMON"/rumble-boost/build.sh "$COMMON"/{game-session,pad-settings,pes2019-cores,pes2019-stack-fix}.py 2>/dev/null
ok "launchers in $COMMON $([[ $changed == 1 ]] && echo '(updated)' || echo '(already up to date)')"
P21="$GAMES/eFootball-PES-2021"
if [[ -d $P21 ]]; then
    for f in play-pes2021.sh dxvk.conf game-session.py; do
        put "$HERE/pes-2021/$f" "$P21/$f" && info "updated $P21/$f"
    done
    chmod +x "$P21/play-pes2021.sh" "$P21/game-session.py"
    ok "PES 2021 launcher files in $P21"
fi
if rumble_fresh; then
    ok "rumble-boost built against $(real_sdl2)"
elif command -v gcc >/dev/null && [[ -n $(real_sdl2) ]]; then
    if "$COMMON/rumble-boost/build.sh" >/dev/null 2>&1 && rumble_fresh; then ok "rumble-boost built against $(real_sdl2)"; else
        bad "rumble-boost did not build: run $COMMON/rumble-boost/build.sh and read the error"; TODO+=("ask the AI to fix the rumble-boost build"); fi
else
    need "sudo dnf install gcc sdl2-compat   # then run ./install.sh again" "cannot build rumble-boost (gcc or SDL2 missing)"
fi

# ---------------------------------------------------------------- wine
part "D. Wine prefixes and DXVK"
if [[ $HAVE_WINE == 0 ]]; then
    bad "Wine is not installed: skipping this part"
else
    for P in "$HOME/.wine-games" "$HOME/.wine"; do
        if [[ ! -f $P/system.reg ]]; then
            info "creating $P (about a minute)..."
            WINEPREFIX=$P WINEARCH=win64 WINEDEBUG=-all WINEDLLOVERRIDES="mscoree=;mshtml=;winemenubuilder.exe=d" timeout 600 wineboot -i >/dev/null 2>&1
            WINEPREFIX=$P timeout 120 wineserver -w 2>/dev/null
        fi
        if [[ ! -f $P/system.reg ]]; then
            :
        elif [[ $P == "$HOME/.wine-games" ]]; then
            # games only start from Steam: no menu entries or file links from Wine.
            # ~/.wine is left alone: the owner's other Windows programs live there.
            grep -q '"winemenubuilder.exe"=""' "$P/user.reg" 2>/dev/null || wreg "$P" 'HKCU\Software\Wine\DllOverrides' /v winemenubuilder.exe /d ''
            ok "$P (no app-menu entries from Wine)"
        else
            ok "$P"
        fi
        if [[ ! -f $P/system.reg ]]; then
            bad "could not create $P: run  WINEPREFIX=$P wineboot -i  and read the error"; TODO+=("ask the AI to look at the Wine prefix $P")
        fi
    done
    if command -v alternatives >/dev/null && alternatives --list 2>/dev/null | grep -qE 'wine-d3d11\(x86-64\).*dxvk-d3d11'; then
        ok "64-bit DXVK through wine-dxvk"
    else
        need "sudo dnf install wine-dxvk" "64-bit DXVK (wine-dxvk) not active"
    fi
    # Blur: 32-bit DXVK d3d9.dll in its folder, Microsoft's msvcr90 for its crash
    BLUR="$GAMES/Blur"
    if [[ -d $BLUR ]]; then
        PROTON_D3D9="$HOME/.local/share/Steam/steamapps/common/Proton - Experimental/files/lib/wine/dxvk/i386-windows/d3d9.dll"
        if [[ -f $BLUR/d3d9.dll ]]; then ok "Blur: 32-bit DXVK d3d9.dll in its folder"
        elif [[ -f $PROTON_D3D9 ]]; then cp "$PROTON_D3D9" "$BLUR/d3d9.dll"; ok "Blur: d3d9.dll copied from Proton Experimental"
        else need "install Proton Experimental in Steam (Library > Tools), then run ./install.sh again" "Blur: no 32-bit DXVK d3d9.dll"; fi
        grep -qi 'AppDefaults\\\\Blur.exe\\\\DllOverrides' "$HOME/.wine-games/user.reg" 2>/dev/null \
            || wreg "$HOME/.wine-games" 'HKCU\Software\Wine\AppDefaults\Blur.exe\DllOverrides' /v msvcr90 /d native,builtin
        ok "Blur: msvcr90 = native,builtin (mid-race crash fix)"
        if ls "$HOME/.wine-games/drive_c/windows/winsxs" 2>/dev/null | grep -qi 'x86_microsoft.vc90.crt_.*9.0.21022.8'; then
            ok "Blur: Microsoft's msvcr90 9.0.21022.8 is in the prefix"
        else
            need "WINEPREFIX=~/.wine-games winetricks -q vcrun2008   # downloads from Microsoft" "Blur: Microsoft's msvcr90 is missing from ~/.wine-games"
        fi
    fi
fi

# ---------------------------------------------------------------- PES 2019 exe
EXE19="$GAMES/PES-2019/PES2019.exe"
if [[ -f $EXE19 ]]; then
    state=$(PES2019_EXE=$EXE19 python3 -I "$COMMON/pes2019-stack-fix.py" status 2>&1)
    case $state in
        patched*) ok "PES 2019: start-up stack fix $state" ;;
        original) PES2019_EXE=$EXE19 python3 -I "$COMMON/pes2019-stack-fix.py" apply 48 >/dev/null && ok "PES 2019: start-up stack fix applied (revert: pes2019-stack-fix.py revert)" ;;
        *) warn "PES 2019: $state — a different exe build, the stack fix was not applied (the E-core helper still works)" ;;
    esac
fi

# ---------------------------------------------------------------- pads
part "E. Controllers"
mkdir -p "$HOME/.config/game-pads"
if [[ -s $HOME/.config/game-pads/mappings.txt ]]; then ok "button map ~/.config/game-pads/mappings.txt (kept)"; else
    cp "$HERE/config/game-pads/mappings.txt" "$HOME/.config/game-pads/mappings.txt"; ok "owner's button map installed"; fi
if python3 -I -c "import importlib.util as u; s=u.spec_from_file_location('p','$COMMON/pad_maps.py'); m=u.module_from_spec(s); s.loader.exec_module(m); m.write_session_db()" 2>/dev/null; then
    systemctl --user set-environment "SDL_GAMECONTROLLERCONFIG_FILE=$HOME/.config/game-pads/gamecontrollerdb.txt" 2>/dev/null
    ok "session pad database + ~/.config/environment.d/60-game-pads.conf"
else
    bad "pad_maps.py failed: run  python3 -I $COMMON/pad_maps.py --json  and read the error"; TODO+=("ask the AI to look at pad_maps.py")
fi

# ---------------------------------------------------------------- PES settings
part "Game settings (screen, commentary, graphics)"
for line in "${GAME_TABLE[@]}"; do
    game_fields "$line"
    [[ -z $KONAMI_DIR ]] && continue
    K="$KONAMI/$KONAMI_DIR"; mkdir -p "$K"
    want=${DAT_SIZE[$REPO_DIR]}
    have=$(stat -c %s "$K/settings.dat" 2>/dev/null || echo 0)
    if [[ $have == "$want" ]]; then
        ok "$NAME: settings.dat ($(python3 -I "$SETTINGS_TOOL" show "$K/settings.dat" | sed -n 's/^resolution: *//p'), kept)"
    else
        put "$HERE/$REPO_DIR/settings/settings.dat" "$K/settings.dat"
        ok "$NAME: owner's settings.dat installed (2560x1440 full screen; was ${have} bytes)"
    fi
    save=$(find "$K" -mindepth 2 -maxdepth 2 -type d -name save 2>/dev/null | head -1)
    if [[ -z $save ]]; then
        warn "$NAME: no save folder yet. Start the game once and quit, then run ./install.sh --restore-settings"
    elif [[ ! -f $save/SYSTEM00000000 || $RESTORE == 1 ]]; then
        for f in SYSTEM00000000 GRAPHICS000000; do put "$HERE/$REPO_DIR/settings/$f" "$save/$f"; done
        ok "$NAME: owner's in-game settings put back (backup of the old ones in $BACKUP)"
    else
        ok "$NAME: in-game settings kept (--restore-settings puts the owner's back)"
    fi
done

# Blur and WWE keep screen/graphics settings in the games prefix
WIN_USER="$HOME/.wine-games/drive_c/users/$USER/AppData"
for pair in "blur/settings/settings.xml|$WIN_USER/Roaming/bizarre creations/blur/settings.xml|Blur" \
            "wwe-2k-battlegrounds/settings/GameUserSettings.ini|$WIN_USER/Local/WWEPlaygrounds/Saved/Config/WindowsNoEditor/GameUserSettings.ini|WWE 2K Battlegrounds"; do
    IFS='|' read -r src dst label <<<"$pair"
    [[ -d $HOME/.wine-games/drive_c ]] || continue
    if [[ ! -f $dst || $RESTORE == 1 ]]; then
        put "$HERE/$src" "$dst" && ok "$label: owner's settings put back (2560x1440 full screen)" || ok "$label: settings already the owner's"
    else
        ok "$label: settings kept (--restore-settings puts the owner's back)"
    fi
done

# ---------------------------------------------------------------- Steam
part "F. Steam library"
if [[ $DO_STEAM == 0 ]]; then
    info "skipped (--no-steam)"
elif ! python3 -I "$STEAM_TOOL" check >/dev/null 2>&1; then
    need "open Steam, sign in, wait until it is fully open, then Steam > Exit; then run ./install.sh again" "Steam has not been opened and signed in yet"
else
    SHOW=$(python3 -I "$STEAM_TOOL" show 2>/dev/null)
    todo_games=()
    for line in "${GAME_TABLE[@]}"; do
        game_fields "$line"
        [[ -f $GAMES/$FOLDER/$EXE ]] || continue
        if msg=$(shortcut_state "$NAME" "$LAUNCHER" <<<"$SHOW"); then
            if [[ -f $APPS/$DESKTOP_ID.desktop && -f $ICON_DIR/$ICON_NAME.png ]]; then
                ok "$NAME: in Steam with its artwork $msg"
                continue
            fi
            msg="dock entry or icon missing"
        fi
        info "$NAME: $msg, fixing"
        todo_games+=("$line")
    done
    pad_ok=0
    shortcut_state "Controller Settings" "$COMMON/controller-settings.sh" <<<"$SHOW" >/dev/null \
        && [[ -f $APPS/local.games.PadSettings.desktop ]] && pad_ok=1
    [[ $pad_ok == 1 ]] && ok "Controller Settings: in Steam with its artwork"
    if ((${#todo_games[@]})) || [[ $pad_ok == 0 ]]; then
        if steam_running; then
            need "close Steam (Steam > Exit, not just the window), then run ./install.sh again" "Steam is open: cannot add or fix the shortcuts now"
        else
            for line in "${todo_games[@]}"; do
                game_fields "$line"
                A="$HERE/$REPO_DIR/art"
                out=$(python3 -I "$STEAM_TOOL" add --name "$NAME" --launcher "$LAUNCHER" --exe "$GAMES/$FOLDER/$EXE" \
                      --wmclass "$WMCLASS" --desktop-id "$DESKTOP_ID" --icon-name "$ICON_NAME" \
                      --cover "$A/cover.png" --wide "$A/wide.png" --hero "$A/hero.png" --logo "$A/logo.png" --icon "$A/icon.png" 2>&1)
                if [[ $out == ADDED* || $out == UPDATED* ]]; then ok "$NAME: ${out%%$'\n'*}"; else
                    bad "$NAME: $out"; TODO+=("ask the AI to look at the Steam shortcut for $NAME"); fi
            done
            if [[ $pad_ok == 0 ]]; then
                out=$(python3 -I "$STEAM_TOOL" controller-settings 2>&1)
                [[ $out == ADDED* ]] && ok "Controller Settings: $out" || { bad "Controller Settings: $out"; TODO+=("ask the AI to look at the Controller Settings shortcut"); }
            fi
        fi
    fi
fi
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1

# ---------------------------------------------------------------- summary
echo
[[ -d $BACKUP ]] && info "replaced files were backed up to $BACKUP"
if ((${#TODO[@]})); then
    echo "${B}${Y}THE OWNER MUST DO (then run ./install.sh again):${N}"
    for t in "${TODO[@]}"; do echo "  - $t"; done
    exit 1
fi
echo "${B}${G}Done.${N} Now run ./check.sh, then press Play on each game in Steam."
