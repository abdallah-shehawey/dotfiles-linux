#!/usr/bin/env bash
# Steam entry point for the game launchers.
# Usage: ./steam-launch.sh /path/to/launcher [args]
# Steam adds its runtime libraries, overlay and pad variables to everything it
# starts. System Wine and the pad setup need the plain session the app menu gives.
launcher=$1
shift

session=()
for name in HOME USER LOGNAME SHELL LANG DISPLAY WAYLAND_DISPLAY XAUTHORITY \
    XDG_RUNTIME_DIR XDG_SESSION_TYPE XDG_SESSION_DESKTOP XDG_CURRENT_DESKTOP \
    XDG_DATA_DIRS DBUS_SESSION_BUS_ADDRESS; do
    [[ -n ${!name} ]] && session+=("$name=${!name}")
done

# Steam's pad list goes along under another name; pads.sh adds it to the map
[[ -n $SDL_GAMECONTROLLERCONFIG ]] && session+=("STEAM_PAD_MAPPINGS=$SDL_GAMECONTROLLERCONFIG")

exec env -i "${session[@]}" PATH="${SYSTEM_PATH:-/usr/local/bin:/usr/bin}" "$launcher" "$@"
