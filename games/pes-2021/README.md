# eFootball PES 2021

> For the AI: do Phases A-F of [../AI-PROMPT.md](../AI-PROMPT.md) first, and
> follow its rules. This file is only what is special about PES 2021.

## Facts

| Item | Value |
|---|---|
| Game folder | `/media/Games/eFootball-PES-2021` |
| Exe | `PES2021.exe` (64-bit, DirectX 11) |
| Wine prefix | `~/.wine` (the default prefix, shared with the owner's other Windows programs) |
| Launcher | `/media/Games/eFootball-PES-2021/play-pes2021.sh`, next to the exe, with its own `dxvk.conf` and `game-session.py` (all three are in this folder of the repo) |
| Launcher options | `hud` = FPS overlay, `settings` = the game's Settings.exe, `pads` = Wine's controller test window |
| Steam | "eFootball PES 2021", appid `2170374278` on this laptop |
| Window class (dock icon) | `pes2021.exe`; hidden entry `~/.local/share/applications/game-pes-2021.desktop`, icon `3FAA_PES2021.0` |
| Saves + settings | `~/Documents/KONAMI/eFootball PES 2021 SEASON UPDATE/` (`settings.dat` = 612 bytes) |
| Log | none: the launcher does not redirect output. To see it, run the launcher in a terminal. |
| Owner's settings | Full screen 2560x1440, 60 fps, Controller Vibration On |

## What the launcher does, line by line

1. `WINEPREFIX=~/.wine`, `WINEDEBUG=-all`.
2. Runs on the NVIDIA GPU (`__NV_PRIME_RENDER_OFFLOAD=1`, `__VK_LAYER_NV_optimus=NVIDIA_only`, `__GLX_VENDOR_LIBRARY_NAME=nvidia`).
3. `DXVK_CONFIG_FILE=./dxvk.conf`: 1 queued frame, vsync on, no frame limiter.
4. Keeps NVIDIA's shader cache between runs (stutter from shader compiles happens once).
5. Sources `/media/Games/common/pads.sh` (same pads as every game).
6. Rumble boost: `RUMBLE_BOOST_FLOOR=75`, `RUMBLE_BOOST_MIX=1`, `RUMBLE_BOOST_MIN_MS=400`, and `/media/Games/common/rumble-boost` first in `LD_LIBRARY_PATH`.
7. `python3 game-session.py taskset -c 0-11 gamemoderun wine PES2021.exe`:
   power profile "performance" and screen 60 Hz while it runs, P-cores only,
   GameMode on.

## Install / repair (in order)

1. Copy the launcher files (also in Phase C of AI-PROMPT):
   ```bash
   cp -a "$REPO/games/pes-2021/"{play-pes2021.sh,dxvk.conf,game-session.py} /media/Games/eFootball-PES-2021/
   chmod +x /media/Games/eFootball-PES-2021/{play-pes2021.sh,game-session.py}
   ```
2. If the games folder is not `/media/Games`, change the two `/media/Games/common`
   paths inside `play-pes2021.sh`.
3. Make sure `rumble-boost` is built: `ls /media/Games/common/rumble-boost/libSDL2-2.0.so.0`
   (if missing: `/media/Games/common/rumble-boost/build.sh`).
4. Steam shortcut (only if missing): Phase F of AI-PROMPT.
5. Screen settings: see [Resolution and full screen](#resolution-and-full-screen).

**Check:** ask the owner to press Play. While it runs:
```bash
ps -eo pid,comm | grep -i pes2021          # the game runs
cat /proc/sys/kernel/split_lock_mitigate   # must be 0
taskset -pc $(ps -eo pid,comm | awk '$2 ~ /PES2021/ {print $1; exit}')   # 0-11
```
Screen must switch to 60 Hz during the game and back to 165 Hz after.

## Known problems and their fixes

### Stutter / hitching during matches
- **Cause:** the game's `JobGraph` worker threads do split locks all the time.
  With `kernel.split_lock_mitigate=1` each one is punished and the match hitches.
- **Fix:** GameMode sets it to 0 during the game; the owner must be in the
  `gamemode` group (Phase B of AI-PROMPT). Joined on 1 Nov 2026 and verified
  after a real reboot: 1 at idle, 0 while the game runs, 1 again after.
- Also: the game is pinned to the P-cores `0-11`. On the E-cores the worker
  threads fall behind and the match stutters.
- Also: 60 fps on a 165 Hz screen judders (2.75 refreshes per frame), so
  `game-session.py` sets 60 Hz while the game runs.
- **Measured baseline after the fix** (1 Nov 2026, live match at 1440p):
  59.6 to 59.8 fps, 99.4 to 99.6 % of frames on time, one missed vsync every
  2.7 to 5 s, nothing over 50 ms during play.
- **How to measure honestly:** screen captures and `nvidia-smi` during play add
  their own hitches, and X window captures go stale in full screen. Use the
  `hud` launcher option (DXVK frame-time graph), or a small Vulkan layer that
  logs a timestamp in `vkQueuePresentKHR`.
- Not measured: whether PES 2021's split locks also cost more on P-cores than
  E-cores, as they do in PES 2019 (see [../pes-2019/README.md](../pes-2019/README.md)).

### CPU stays on "performance" after the game
- **Cause:** `game-session.py` raises the power profile before GameMode starts,
  so GameMode records "performance" as the governor to restore.
- **Fix:** `~/.config/gamemode.ini` with `defaultgov=powersave`
  ([../config/gamemode.ini](../config/gamemode.ini)).

### No vibration
- **Symptom:** pads vibrate in Blur but not in PES (in-game Controller
  Vibration was already On).
- **Cause (found with gdb on `SDL_JoystickRumble` inside winedevice):** PES
  does send rumble, but as ~217 ms pulses at 10 / 40 / 60 % (`0x1999` /
  `0x6666` / `0x9999`), often on the small motor only. The Twin USB pads use
  the `hid-pl` (pantherlord) driver, which scales full strength to about half
  of the motor range, so those pulses never spin the motors. Wine's XInput
  path is fine (identical in both prefixes).
- **Fix:** `common/rumble-boost/libSDL2-2.0.so.0`. `winebus` loads SDL2 by
  name; with that folder first in `LD_LIBRARY_PATH` it loads this small
  library, which changes only the two rumble calls and forwards everything else
  to the real SDL2 by full path:
  - `RUMBLE_BOOST_FLOOR` (%): any non-zero strength `m` becomes
    `floor + m × (100 % − floor)`. 0 = off.
  - `RUMBLE_BOOST_MIX=1`: both motors get the stronger value.
  - `RUMBLE_BOOST_MIN_MS`: an early stop is held back so each pulse lasts at least this long.
  - Owner's values: **75 / 1 / 400**. The owner said they feel "just right"
    (10 Nov 2026). Do not change them unless asked.
- **After an SDL2 / sdl2-compat update** that changes the real file name
  (`readlink -f /usr/lib64/libSDL2-2.0.so.0`), run
  `/media/Games/common/rumble-boost/build.sh` again. Symptom of a stale build:
  no pads at all, or no vibration, after a system update.
- Wine reads the variables only when the prefix starts: after a change,
  `WINEPREFIX=~/.wine wineserver -k` and start again.

### Settings.exe: empty pad list and empty resolution box
- **Cause:** `Settings_b.dll` is mixed-mode C++/CLI, which Wine Mono cannot
  run fully. `Settings.exe` needs `iconv.dll` in the game folder even to open
  (it is there; on Fedora `mingw64-win-iconv` ships a 64-bit one at
  `/usr/x86_64-w64-mingw32/sys-root/mingw/bin/iconv.dll`, untested here).
- **Fix:** do not use Settings.exe for pads (pads come from Controller
  Settings). For the screen, see the next section.

### Resolution and full screen
Edit `settings.dat` directly (start the game once first so the file exists,
and close the game before editing):
```bash
F="$HOME/Documents/KONAMI/eFootball PES 2021 SEASON UPDATE/settings.dat"
python3 "$REPO/games/tools/pes-settings-dat.py" show "$F"
python3 "$REPO/games/tools/pes-settings-dat.py" set "$F" --width 2560 --height 1440 --fullscreen on
```
Flag bit 0 at offset `0x08` = full screen; width at `0x0c`, height at `0x10`.
The tool makes a backup first. Graphics quality is set inside the game.

### Online: network error
Konami turned the servers off: `pes21-x64-gate.cs.konami.net` /
`stun.cs.konami.net` have no DNS (checked 15 Nov 2026). Press OK and play
offline. Internet inside Wine works.

### Exits right away
`~/.wine` already has a winetricks Visual C++ runtime (the `*concrt140`
override in `~/.wine/user.reg` comes from it). If it was lost (new prefix):
`WINEPREFIX=~/.wine winetricks -q vcrun2022` (download from Microsoft: ask the
owner first).

## Not verified
- Frame pacing through the Steam shortcut was never measured separately from
  starting the launcher directly (same launcher, so it should match).
- The dock icon `Exec=` line (`steam://rungameid/...`) was never clicked.

## Undo
- Rumble boost off for one run: start the launcher with `RUMBLE_BOOST_FLOOR=0`.
- Launcher backup before the rumble change: `~/.cache/wine-games/play-pes2021.sh.before-rumble-boost`.
- Steam shortcut: Steam → right-click → Manage → Remove non-Steam game.
