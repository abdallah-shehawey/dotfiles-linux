# PES 2019

> For the AI: do Phases A-F of [../AI-PROMPT.md](../AI-PROMPT.md) first, and
> follow its rules. This file is only what is special about PES 2019.

## Facts

| Item | Value |
|---|---|
| Game folder | `/media/Games/PES-2019` (about 24 GB), game version 1.02.00, Data Pack 2.00 |
| Exe | `PES2019.exe` (64-bit, DirectX 11) |
| Wine prefix | `~/.wine-games` |
| Launcher | `/media/Games/common/play-pes2019.sh` (copy in [../common/](../common/play-pes2019.sh)) |
| Launcher options | `hud` = FPS overlay, `settings` = the game's Settings.exe, `pads` = Wine's controller test window |
| Helpers | `common/dxvk-pes2019.conf`, `common/pes2019-cores.py` (started by the launcher), `common/pes2019-stack-fix.py` (run once) |
| Steam | "PES 2019", appid `3193774979` on this laptop |
| Window class (dock icon) | `pes2019.exe`; hidden entry `game-pes-2019.desktop`, icon `pes-2019` in `~/.local/share/icons/hicolor/256x256/apps/` |
| Saves + settings | `~/Documents/KONAMI/PRO EVOLUTION SOCCER 2019/` (`settings.dat` = 352 bytes; game saves in `<number>/save/`) |
| Logs | `~/.cache/wine-games/pes2019.log`, `~/.cache/wine-games/pes2019-cores.log` |
| Owner's settings | Full screen 2560x1440, 60 fps, Commentary Language = العربية (Arabic), Image Quality = High |

Launch it from a terminal through the same path Steam uses:
`/media/Games/common/steam-launch.sh /media/Games/common/play-pes2019.sh`
or through Steam itself:
`steam steam://rungameid/$(( (3193774979<<32) | 0x02000000 ))` (ask the owner first).

## Install / repair (in order)

Fast path: `cd "$REPO/games" && ./install.sh && ./check.sh` does every step
below (it also applies the exe patch when the exe is the original). The steps
are here to understand and to do by hand.

1. Launcher and helpers are in `/media/Games/common` (Phase C of AI-PROMPT).
2. Check the start-up patch on the exe and apply it if needed (ask the owner):
   ```bash
   python3 /media/Games/common/pes2019-stack-fix.py status
   ```
   - `patched (stack shift 48)` → nothing to do.
   - `original` → `python3 /media/Games/common/pes2019-stack-fix.py apply 48`
   - `...neither original nor a known patch...` → a different exe build. Do
     **not** force it. The E-core helper alone still brings the first frame
     to ~15.5 s (from 47 s).
   The script finds the exe as `<games folder>/PES-2019/PES2019.exe` (next to
   its `common/` folder); for another place: `PES2019_EXE=/path/PES2019.exe`.
3. Screen settings: [Resolution and full screen](#resolution-and-full-screen).
4. Arabic commentary and graphics: [Settings files](#settings-files-in-this-repo),
   or by hand: [Commentary language](#commentary-language-arabic).
5. Steam shortcut with its pictures: [Steam pictures and dock icon](#steam-pictures-and-dock-icon).

**Check:** start it, then:
```bash
cat ~/.cache/wine-games/pes2019-cores.log
```
Expected: `PES2019.exe is pid ...: start-up on E-cores [12, ..., 19]`, then
`FilePostProcess idle after ~19 s`, `game threads back on the P-cores`, and
`game exited` after the owner quits. The title screen should come at about
30 s after Play.

## Steam pictures and dock icon

| File in [art/](art/) | Steam slot | Size |
|---|---|---|
| `cover.png` | Library cover (grid `<appid>p.png`) | 600x900 |
| `wide.png` | Wide capsule (grid `<appid>.png`) | 920x430 |
| `hero.png` | Banner on the game page (grid `<appid>_hero.png`) | 1920x620 |
| `logo.png` | Logo over the banner (grid `<appid>_logo.png`) | 859x229 |
| `icon.png` | Shortcut icon + dock icon `pes-2019` | 256x256 |

These were drawn for this setup (night stadium + Montserrat wordmark), not
taken from the game. Install (Steam closed):
```bash
T="$REPO/games/tools/steam/steam-shortcut.py"; A="$REPO/games/pes-2019/art"
python3 -I "$T" add --name "PES 2019" --launcher /media/Games/common/play-pes2019.sh \
    --exe /media/Games/PES-2019/PES2019.exe --wmclass pes2019.exe \
    --desktop-id game-pes-2019 --icon-name pes-2019 \
    --cover "$A/cover.png" --wide "$A/wide.png" --hero "$A/hero.png" --logo "$A/logo.png" --icon "$A/icon.png"
```
By hand: AI-PROMPT section 8.2. Dock entry: [../config/applications/game-pes-2019.desktop](../config/applications/game-pes-2019.desktop)
(window class `pes2019.exe`).

## Settings files in this repo

[settings/](settings/) holds the owner's files, to put back after a reinstall:

| File | Goes to | Holds |
|---|---|---|
| `settings.dat` (352 bytes) | `~/Documents/KONAMI/PRO EVOLUTION SOCCER 2019/settings.dat` | Full screen, 2560x1440, 60 fps (flags `0x3f`), keyboard map |
| `SYSTEM00000000` | `~/Documents/KONAMI/PRO EVOLUTION SOCCER 2019/<number>/save/` | In-game system settings: **Commentary Language = العربية** |
| `GRAPHICS000000` | same `save/` folder | Render Settings: Image Quality **High** |

- `./install.sh` puts `settings.dat` back when it is missing or the wrong size
  (for example the 104-byte file the game rejects), and the two save files when
  the `save/` folder has none.
- `<number>` is a folder the game creates on its first start. Start the game
  once, quit, then `./install.sh --restore-settings` to put the owner's
  settings over the defaults (old ones are backed up).
- The Arabic commentary also needs the `dt41_ara_all.cpk` / `dt43_ara_all.cpk`
  files in `Data/` (see below). The save files are encrypted by the game; copy
  them whole, never edit them.

## Known problems and their fixes

### White window forever (game never shows)
- **Cause:** by default DXVK reports the NVIDIA card as an AMD card
  (`dxgi.hideNvidiaGpu`). PES 2019 then never creates its swapchain.
- **Fix:** `common/dxvk-pes2019.conf` has `dxgi.hideNvidiaGpu = False`
  (plus the shared dxvk.conf lines). `play-pes2019.sh` sets
  `DXVK_CONFIG_FILE` to it. Check that line is there if the white screen comes back.
- Wine's own D3D11 (wined3d) also worked. Note for testing it on Fedora:
  `alternatives` points Wine's builtin d3d11/dxgi at DXVK, and copies of
  `wine-d3d11.dll` placed in the game folder are swapped for the builtin
  unless the "Wine builtin DLL" marker at offset 0x40 is overwritten. Test
  copies are kept in `/media/Games/PES-2019/.wined3d/`. Normally not needed.

### Very slow start (white window ~42 s, title screen at ~78 s)
- **Cause: split locks**, not UMIP and not a timer. The game's start-up
  protection code runs a small VM (section `.xtls`) that keeps its context on
  the main thread's stack and updates two fields with locked `xchg`. Under
  Wine's stack layout those fields sit on byte 63 of a cache line, so every
  `xchg` is a split lock: ~40,000 per second, IPC 0.01, ~41 s of CPU. The
  `FilePostProcess` thread does the same during the black loading phase. None
  at the title screen. Windows does not hit this because its stack lands elsewhere.
- **Key hardware fact (i7-12700H):** one split lock costs ~25 µs on a P-core
  (0-11) but ~3.7 µs on an E-core (12-19), capped near 40k/s, all user time.
  The kernel is not involved (`split_lock_mitigate` is already 0 under GameMode).
- **Fix 1 — `common/pes2019-cores.py`** (started in the background by the
  launcher): every game thread runs on the E-cores from start until
  `FilePostProcess` has been idle 3 s (~19 s), then everything goes back to
  0-11, except `FilePostProcess`, which stays on the E-cores for later loading
  screens. GameMode re-pins every thread to 0-11 every ~4 s, so the script
  re-applies in a loop until the game exits.
- **Fix 2 — `common/pes2019-stack-fix.py`**: rewrites the exe's 0x44-byte entry
  stub (section `.trace`, file offset `0x1173A220`) to call the real entry with
  the stack 48 bytes lower, so the hot fields no longer straddle a cache line.
  It checks the original bytes first, and `revert` puts them back
  (`status` / `apply 16|32|48` / `revert`).
- **Measured:** first frame at 47 s on P-cores (original), 15.5 s with start-up
  on E-cores, 12.7 s with both fixes; title screen at ~30 s instead of 78 s.
- **Do NOT** add `clearcpuid=umip` to the kernel command line. It was tried on
  15 Nov 2026: the white screen still lasted 47 s. It was removed again
  (`common/undo-pes2019-umip.sh` was run; it is not in this repo because it is
  not needed). After that reboot the start was the same with UMIP on.
- **How it was found** (if a similar problem appears in another game):
  `perf stat -e cpu_core/sq_misc.bus_lock/u -p <pid> -- sleep 5` counts bus
  (split) locks; PEBS `perf record -e mem_inst_retired.lock_loads -d` gives the
  addresses. A SIGSTOP test showed the delay is fixed CPU work, not a timer.

### Resolution and full screen
- `settings.dat` must be **352 bytes**. A 104-byte file is read but rejected
  (the game falls back to 1920x1080 windowed).
- If there is no good file: run `/media/Games/common/play-pes2019.sh settings`.
  Settings.exe (needs `iconv.dll` in the game folder, which is there) shows the
  file wrongly and its resolution list is empty under Wine Mono, but pressing
  OK with **Full Screen** and **60/60 fps** writes a correct 352-byte file
  (flags `0x3f`). Then set the resolution:
  ```bash
  F="$HOME/Documents/KONAMI/PRO EVOLUTION SOCCER 2019/settings.dat"
  python3 "$REPO/games/tools/pes-settings-dat.py" set "$F" --width 2560 --height 1440 --fullscreen on
  ```
  Confirmed in game: full screen 2560x1440. A copy of Settings.exe's own
  1080p file is next to it: `settings.dat.from-settings-exe-1080p`.

### Commentary language (Arabic)
- The Arabic commentary files must be in `Data/`: `dt41_ara_all.cpk` and
  `dt43_ara_all.cpk` (they came with the game's Arabic language pack). Check:
  `ls /media/Games/PES-2019/Data/ | grep -i ara`.
- In the game, with the pad: Press Any Button → network error dialog → OK →
  **EXTRAS** (R1 four times) → **SYSTEM SETTINGS** (down, right ×3) →
  **Language Settings** (last item) → **Commentary Language** → **العربية**.
  Menus stay in English. Render Settings (graphics) is in the same System
  Settings list: Image Quality **High** is the top preset (one more step
  wraps to Low); it turns Dynamic Resolution off and every item High/On.
- Saved to `.../<number>/save/SYSTEM00000000` and `GRAPHICS000000`.
- To drive the menus without the owner (only with their OK): inject pad presses
  into the real pad node, see [../controllers/README.md](../controllers/README.md#testing-tools-for-the-ai).
  The game window must have focus.

### Network error "CODE:FDDN580" after Press Any Button
Konami removed the servers: `pes19-x64-gate.cs.konami.net` /
`stun.cs.konami.net` have no DNS (checked 15 Nov 2026). Press OK. Internet
inside Wine works (DNS and HTTPS tested in both prefixes).

### No vibration
Same engine and same weak pulses as PES 2021, so the launcher uses the same
`rumble-boost` with 75 / 1 / 400. See [../pes-2021/README.md](../pes-2021/README.md#no-vibration).

## Not verified
- Starting it with Play inside Steam itself after the start-up fixes (it was
  timed through `steam-launch.sh`, the same path).
- A full match / gameplay frame rate after the fixes.

## Undo
- Exe patch: `python3 /media/Games/common/pes2019-stack-fix.py revert`.
- Core helper: remove the `pes2019-cores.py` line from `play-pes2019.sh`.
- Settings: every `pes-settings-dat.py set` leaves `settings.dat.bak-<date>`.
