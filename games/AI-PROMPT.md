# AI instructions: set up and repair the Windows games on this Linux laptop

> **For the human.** Open any AI assistant that can run commands on this laptop
> (Claude Code, Cursor, Copilot agent, Gemini CLI, ...) and paste this:
>
> ```text
> Read games/AI-PROMPT.md in my dotfiles-linux repository and follow it exactly.
> Then read the README.md of every game folder under games/.
> Goal: every game in my Steam library starts with Play, runs smoothly, and
> all my controllers work. Fix anything that is broken. Ask me before
> anything that needs my password, downloads something, or deletes something.
> ```
>
> To fix just one game, paste the same thing and add: `Only fix <game name>.`

---

## 0. Read this first (for the AI)

You are setting up, checking and repairing four Windows games that run under
Wine on a Fedora laptop. They start from the **Steam library** as non-Steam
shortcuts. Everything below was built and debugged on this exact laptop in
November 2026. The fixes are real and measured. Follow them; do not invent
new ones unless a step tells you to investigate.

Work in this order. Do not skip a phase. After every phase, run its **Check**
and compare the output with what is written. If a check fails, use the
**If it fails** list of that phase, then
[section 9 (Troubleshooting)](#9-troubleshooting-symptom--cause--fix).

| Phase | What | Section |
|---|---|---|
| A | Programs | [3](#3-phase-a--programs) |
| B | Performance fix (split locks, GameMode) | [4](#4-phase-b--performance-fix) |
| C | Games folder and shared launchers | [5](#5-phase-c--games-folder-and-shared-launchers) |
| D | Wine prefixes and DXVK | [6](#6-phase-d--wine-prefixes-and-dxvk) |
| E | Controllers | [7](#7-phase-e--controllers) and [controllers/README.md](controllers/README.md) |
| F | Steam shortcuts | [8](#8-phase-f--steam-shortcuts) |
| G | Each game | the game's own README (table in [section 2](#2-the-games)) |

### 0.1 Rules you must follow

1. **Never run anything as root yourself.** `sudo` needs the owner's password.
   When a step needs `sudo`, show the owner the exact command in a code block,
   say what it does in one line, and wait until they say it is done. Then check
   the result yourself.
2. **Never delete.** Move things to the Trash with `gio trash <path>`. The owner
   empties the Trash.
3. **Back up a file before you edit it**: `cp -a FILE FILE.bak-$(date +%Y%m%d-%H%M%S)`.
4. **Steam must be fully closed** before you edit any Steam file
   (`shortcuts.vdf`, `localconfig.vdf`). Steam rewrites them when it exits and
   your change is lost. Check with `pgrep -x steam || pgrep -x steamwebhelper`
   (no output = closed). To close it: `steam -shutdown`, then wait until the
   check prints nothing.
5. **Ask before** downloading anything, changing boot or kernel options,
   installing packages, or touching game saves.
6. **Do not download games, cracks or game files.** The owner provides the game
   folders. Do not run a game's installer unless the owner asks.
7. **Starting a game to test it:** ask the owner first, or ask them to press
   Play in Steam and tell you when it is running. Then read the logs
   ([section 10](#10-logs-and-where-things-are)).
8. **Killing a game:** use `WINEPREFIX=<its prefix> wineserver -k`.
   Never use `pkill -f <name>` or `pgrep -f <name>`: when your own command line
   contains that name, it matches and kills your own shell. To find a process,
   use `ps -eo pid,comm | grep -i pes2019` (comm only, not args).
9. In the owner's zsh, `install` is an alias for `sudo dnf install`. To copy
   files use `cp` / `mkdir -p` or `/usr/bin/install`, never plain `install`.
10. **Never claim something works without checking it.** Say what you checked
    and what you could not check.
11. Do not add app-menu entries for the games. The owner starts games from
    Steam only. Hidden `.desktop` files with `NoDisplay=true` (they only give
    the game window its dock icon) are fine.
12. Reply to the owner in **Egyptian Arabic** (casual). Any app or tool you
    build gets an **English** UI in Steam's dark blue style, with PlayStation
    button symbols (△ ○ ✕ □).

### 0.2 Words used here

| Word | Meaning |
|---|---|
| `REPO` | This repository, e.g. `~/Projects/dotfiles-linux`. Run `REPO=~/Projects/dotfiles-linux` (or wherever it is) at the start of each shell. |
| `GAMES` | The games folder: `/media/Games`. |
| prefix | A Wine "fake Windows" folder. Two are used: `~/.wine` (PES 2021) and `~/.wine-games` (the other three). |
| launcher | The `play-*.sh` script that starts one game. Steam runs it. |
| split lock | A CPU memory access across two cache lines. The kernel slows down programs that do it. These games do it constantly. |
| P-cores / E-cores | The i7-12700H has fast cores 0-11 (P) and small cores 12-19 (E). |

---

## 1. The machine

| Part | Value |
|---|---|
| Laptop | Lenovo Legion 5 15IAH7 |
| OS | Fedora 45, GNOME on Wayland (only OS on the disk; Windows was removed) |
| CPU | Intel i7-12700H: P-cores `0-11`, E-cores `12-19` |
| GPU | NVIDIA RTX 3050 Ti Mobile (games run here) + Intel iGPU (drives the screen) |
| Screen | 2560x1440, 165 Hz |
| RAM | 15 GB |
| Wine | Fedora's `wine` 11.20 (Staging, WoW64). Uses `/dev/ntsync` by itself: no sync tuning needed. |
| DXVK | Fedora's `wine-dxvk` 2.7.1 (64-bit only) + a 32-bit `d3d9.dll` from Proton for Blur |
| Games disk | ext4 partition labelled `Games`, mounted at `/media/Games` |

**If the machine is different:**
- Other CPU: get the fast-core list with `cat /sys/devices/cpu_core/cpus`. Put
  that list instead of `0-11` in `common/game-env.sh` and
  `pes-2021/play-pes2021.sh` (`taskset -c 0-11`). If the file does not exist
  (AMD, or Intel before 12th gen), delete `taskset -c 0-11` from both.
  `pes2019-cores.py` does nothing without E-cores (it says so in its log).
- No NVIDIA card: delete the three lines `__NV_PRIME_RENDER_OFFLOAD`,
  `__VK_LAYER_NV_optimus`, `__GLX_VENDOR_LIBRARY_NAME` from `common/game-env.sh`
  and `pes-2021/play-pes2021.sh`, and skip `dxgi.hideNvidiaGpu` notes.
- Screen not 165 Hz, or not GNOME: `game-session.py` switches the screen to
  60 Hz through GNOME's Mutter D-Bus API. On other desktops it prints
  `panel stays at its current rate` in the log and the game still runs.
- Not Fedora: use the generic package
  <https://github.com/abdallah-shehawey/Gaming-on-Linux> (step 1 installs the
  programs on Debian/Ubuntu/Mint and Arch). Then continue here from Phase B.

---

## 2. The games

| Game | Folder in `/media/Games` | Real exe | Prefix | Launcher | Its README |
|---|---|---|---|---|---|
| eFootball PES 2021 | `eFootball-PES-2021` | `PES2021.exe` (64-bit, DX11) | `~/.wine` | `eFootball-PES-2021/play-pes2021.sh` | [pes-2021/README.md](pes-2021/README.md) |
| PES 2019 | `PES-2019` | `PES2019.exe` (64-bit, DX11) | `~/.wine-games` | `common/play-pes2019.sh` | [pes-2019/README.md](pes-2019/README.md) |
| Blur | `Blur` | `Blur.exe` (32-bit, DX9) | `~/.wine-games` | `common/play-blur.sh` | [blur/README.md](blur/README.md) |
| WWE 2K Battlegrounds | `WWE-2K-Battlegrounds` | `WWEPlaygrounds/Binaries/Win64/WWEPlaygrounds-Win64-Shipping.exe` (started by `WWEBattlegrounds.exe`) | `~/.wine-games` | `common/play-wwe2k-battlegrounds.sh` | [wwe-2k-battlegrounds/README.md](wwe-2k-battlegrounds/README.md) |
| Controller Settings (our app) | — | `common/pad-settings.py` | — | `common/controller-settings.sh` | [controllers/README.md](controllers/README.md) |

How a game starts (same for all):

```text
Steam "Play"
  └─ /media/Games/common/steam-launch.sh <launcher>     wipes Steam's environment (env -i)
       └─ play-<game>.sh                                 prefix, GPU, DXVK config, pads, rumble
            └─ game-session.py                           power profile "performance" + screen 60 Hz, undone on exit
                 └─ taskset -c 0-11 gamemoderun wine <Game>.exe     P-cores + GameMode
```

Why `steam-launch.sh` exists: Steam adds `LD_PRELOAD` (overlay), its own
runtime paths, `SDL_GAMECONTROLLER_IGNORE_DEVICES` and shader-cache variables
to everything it starts. System Wine and the pad setup break with them. The
wrapper keeps only the desktop session variables and passes Steam's pad list on
as `STEAM_PAD_MAPPINGS`.

---

## 3. Phase A — Programs

1. RPM Fusion must be on (Steam and the NVIDIA driver come from it). Check:
   `rpm -q rpmfusion-free-release rpmfusion-nonfree-release`.
   If missing, give the owner:
   ```bash
   sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
   ```
2. Packages. Check which are missing:
   ```bash
   for p in steam wine wine-mono wine-dxvk winetricks gamemode gamemode.i686 sdl2-compat SDL3 python3-gobject python3-cairo gtk4 libadwaita gcc zstd; do rpm -q $p >/dev/null || echo "MISSING $p"; done
   ```
   Give the owner one `sudo dnf install <missing ones>` command.
   - `sdl2-compat` gives `/usr/lib64/libSDL2-2.0.so.0`. Wine's `winebus` reads
     the pads through it, and `rumble-boost` wraps it.
   - `gcc` is only needed to build `rumble-boost`.
3. NVIDIA driver. Check: `cat /proc/driver/nvidia/version`. If missing, give the
   owner `sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda`, tell them to
   wait 5 minutes (the module builds) and restart.
4. Steam must have been opened once and signed in. Check:
   `python3 -I "$REPO/games/tools/steam/steam-shortcut.py" check` → `STEAM-READY ...`.
   If it says `STEAM-NOT-READY`: ask the owner to open Steam, sign in, wait
   until it is fully open, then close it with Steam → Exit.

**Check:** `wine --version` prints `wine-11.x` or newer; `gamemoderun true` exits
with no error; `ls /usr/lib64/libSDL2-2.0.so.0` exists.

---

## 4. Phase B — Performance fix

**Why.** The games' worker threads (PES 2021's `JobGraph` threads, PES 2019's
start-up code) do split locks all the time. With
`kernel.split_lock_mitigate=1` (Fedora's default) the kernel punishes each one
and the game hitches. GameMode sets it to `0` while a game runs and back to `1`
after, **but only for users in the `gamemode` group**.

1. Check: `getent group gamemode | grep -qw "$USER" && echo IN-GROUP`.
   If not, give the owner `sudo usermod -aG gamemode $USER`, then they must
   **restart the laptop** (log out is not always enough).
2. Copy GameMode's config:
   ```bash
   mkdir -p ~/.config && cp -a "$REPO/games/config/gamemode.ini" ~/.config/gamemode.ini
   ```
   It contains `defaultgov=powersave`. Without it the CPU governor stays on
   `performance` after a game, because `game-session.py` raises the power
   profile before GameMode records the "original" governor.

**Check (needs a running game):** `cat /proc/sys/kernel/split_lock_mitigate`
→ `1` with no game, `0` while a game runs, `1` again after it closes. This was
verified on this laptop after a real reboot.

**Do NOT** add `clearcpuid=umip` or `split_lock_detect=off` to the kernel
command line. UMIP was tested for PES 2019 and made no difference; it was
removed again. GameMode's switch is the whole fix. (Boot note for this laptop:
`GRUB_ENABLE_BLSCFG=false`, so kernel options only change after editing
`/etc/default/grub` and running `sudo grub2-mkconfig -o /boot/grub2/grub.cfg`;
`grubby --args` alone does nothing here.)

---

## 5. Phase C — Games folder and shared launchers

1. The games disk. Check: `findmnt /media/Games`. If nothing: find the
   partition with `lsblk -f` (ext4, label `Games`) and give the owner a line
   for `/etc/fstab`:
   ```text
   UUID=<uuid from lsblk -f>  /media/Games  ext4  defaults,noatime,nofail,x-gvfs-show  0 2
   ```
   then `sudo systemctl daemon-reload && sudo mount /media/Games && sudo chown $USER: /media/Games`.
   Keep games on ext4. Do not run them from an NTFS drive.
2. Check that the four game folders exist with their exe (table in section 2):
   ```bash
   ls /media/Games/eFootball-PES-2021/PES2021.exe /media/Games/PES-2019/PES2019.exe /media/Games/Blur/Blur.exe /media/Games/WWE-2K-Battlegrounds/WWEBattlegrounds.exe
   ```
   A missing one: ask the owner where that game is. Do not look for it online.
3. Copy the shared launchers:
   ```bash
   mkdir -p /media/Games/common
   cp -a "$REPO/games/common/." /media/Games/common/
   chmod +x /media/Games/common/*.sh /media/Games/common/*.py /media/Games/common/rumble-boost/build.sh
   chmod -x /media/Games/common/pad_maps.py
   ```
4. Copy PES 2021's own launcher files into its game folder (that launcher
   lives next to the exe, not in `common`):
   ```bash
   cp -a "$REPO/games/pes-2021/play-pes2021.sh" "$REPO/games/pes-2021/dxvk.conf" "$REPO/games/pes-2021/game-session.py" /media/Games/eFootball-PES-2021/
   chmod +x /media/Games/eFootball-PES-2021/play-pes2021.sh /media/Games/eFootball-PES-2021/game-session.py
   ```
5. Build the rumble booster (it must match the installed SDL2 file):
   ```bash
   /media/Games/common/rumble-boost/build.sh
   ```
   Expected: `built against /usr/lib64/libSDL2-2.0.so.0.<version>`.
   **Run it again after every SDL2 / sdl2-compat update** that changes that
   file name (see [pes-2021/README.md](pes-2021/README.md), "No vibration").

**Check:**
```bash
ls -l /media/Games/common/{steam-launch.sh,game-env.sh,game-session.py,pads.sh,pad_maps.py,pad-settings.py,play-pes2019.sh,play-blur.sh,play-wwe2k-battlegrounds.sh,controller-settings.sh,dxvk.conf,dxvk-pes2019.conf,pes2019-cores.py,pes2019-stack-fix.py,rumble-boost/libSDL2-2.0.so.0}
for f in /media/Games/common/*.sh /media/Games/eFootball-PES-2021/play-pes2021.sh; do bash -n "$f" || echo "SYNTAX ERROR in $f"; done
```

---

## 6. Phase D — Wine prefixes and DXVK

Two prefixes, on purpose:
- `~/.wine` — PES 2021 (it was installed first; other Windows programs such as
  Proteus and LTspice also live here).
- `~/.wine-games` — PES 2019, Blur, WWE 2K Battlegrounds. Kept apart so the
  game installs stay away from the owner's other Windows programs, and because
  Wine reads the pad map only when a prefix starts.

1. Create a missing prefix (both are 64-bit WoW64, 32-bit games run in them too):
   ```bash
   [ -f ~/.wine-games/system.reg ] || WINEPREFIX=~/.wine-games WINEARCH=win64 wineboot -i
   [ -f ~/.wine/system.reg ]       || WINEPREFIX=~/.wine       WINEARCH=win64 wineboot -i
   ```
   **Never** trash an existing `~/.wine`: the owner has other programs in it.
2. Stop Wine from making app-menu entries and file links:
   ```bash
   for P in ~/.wine ~/.wine-games; do WINEPREFIX=$P wine reg add 'HKCU\Software\Wine\DllOverrides' /v winemenubuilder.exe /d '' /f; done
   ```
3. DXVK for 64-bit games comes from Fedora's `wine-dxvk` package: it switches
   Wine's own 64-bit `d3d9`, `d3d10core`, `d3d11`, `dxgi` to DXVK through
   `alternatives`. Nothing to copy. Check:
   ```bash
   alternatives --list | grep -E 'wine-(d3d11|dxgi)\(x86-64\)'
   ```
   Both lines must point to `.../dxvk-d3d11.dll` and `.../dxvk-dxgi.dll`.
   32-bit stays Wine's own (wined3d), which is why Blur carries its own DXVK
   `d3d9.dll` (see [blur/README.md](blur/README.md)).
4. Each launcher points `DXVK_CONFIG_FILE` at a config:
   `common/dxvk.conf` (shared), `common/dxvk-pes2019.conf` (PES 2019),
   `eFootball-PES-2021/dxvk.conf` (PES 2021). They set
   `maxFrameLatency = 1` (pads feel direct), `syncInterval = 1` and no frame
   limiter (the screen is at 60 Hz during the game, so vsync alone paces the
   frames; a second limiter on top made frame times uneven).

**Check that DXVK is really used** (owner starts the game, or you start it with
their OK): run the launcher with `hud` as argument, e.g.
`/media/Games/common/play-pes2019.sh hud` → an FPS / frame-time / GPU-load
overlay appears. No overlay = DXVK is not loaded (see section 9).

---

## 7. Phase E — Controllers

Full details: [controllers/README.md](controllers/README.md). Short version:

1. Copy the owner's saved button map (only if none exists yet):
   ```bash
   mkdir -p ~/.config/game-pads
   [ -s ~/.config/game-pads/mappings.txt ] || cp -a "$REPO/games/config/game-pads/mappings.txt" ~/.config/game-pads/
   ```
2. Write the session-wide pad database and its environment file:
   ```bash
   python3 -I -c "import importlib.util as u; s=u.spec_from_file_location('p','/media/Games/common/pad_maps.py'); m=u.module_from_spec(s); s.loader.exec_module(m); m.write_session_db()"
   systemctl --user set-environment SDL_GAMECONTROLLERCONFIG_FILE=$HOME/.config/game-pads/gamecontrollerdb.txt
   ```
   This creates `~/.config/game-pads/gamecontrollerdb.txt` and
   `~/.config/environment.d/60-game-pads.conf` (used from the next login by
   every SDL program, Steam included).
3. Every launcher sources `common/pads.sh`, which runs `pad_maps.py` and
   exports the pad map, the player order and `SDL_JOYSTICK_DEVICE` before Wine
   starts.

**Check:**
```bash
python3 -I /media/Games/common/pad_maps.py --json
```
prints one entry per connected pad, each with a mapping. Then
`tail -20 ~/.cache/wine-games/pads.log` after a game start shows what each pad got.

---

## 8. Phase F — Steam shortcuts

Each game is a non-Steam shortcut: target `"/media/Games/common/steam-launch.sh"`,
start-in `"/media/Games/common/"`, launch options = the game's launcher.
Overlay off, Steam Input off. The tool below writes all of that, the Steam
Input setting and a hidden dock-icon `.desktop` file. Steam must be closed
(rule 4).

**On this laptop the shortcuts already exist** (made by hand on 1-15 Nov 2026:
PES 2021 appid `2170374278`, PES 2019 `3193774979`, Blur `2974620932`, WWE
`2191877059`, Controller Settings `3501849340`). If they are in the Library and
start, **skip this phase**. Use it on a fresh install, or to rebuild one broken
shortcut.

```bash
T="$REPO/games/tools/steam/steam-shortcut.py"
G=/media/Games
python3 -I "$T" add --name "eFootball PES 2021"   --launcher "$G/eFootball-PES-2021/play-pes2021.sh"   --exe "$G/eFootball-PES-2021/PES2021.exe"
python3 -I "$T" add --name "PES 2019"             --launcher "$G/common/play-pes2019.sh"               --exe "$G/PES-2019/PES2019.exe"
python3 -I "$T" add --name "Blur"                 --launcher "$G/common/play-blur.sh"                  --exe "$G/Blur/Blur.exe"
python3 -I "$T" add --name "WWE 2K Battlegrounds" --launcher "$G/common/play-wwe2k-battlegrounds.sh"   --exe "$G/WWE-2K-Battlegrounds/WWEBattlegrounds.exe" --wmclass WWEPlaygrounds-Win64-Shipping.exe
python3 -I "$T" controller-settings
python3 -I "$T" list
```

- Expected for each: `ADDED <name> (<appid>)`. It backs up the Steam files to
  `~/.cache/wine-games/steam-backup-<date>/` first.
- A shortcut with the same name is **replaced** (it gets a new appid). Its old
  artwork stays in `grid/` under the old appid, so pass the pictures again.
  The hand-made dock entries `~/.local/share/applications/game-pes-2021.desktop`,
  `game-pes-2019.desktop`, `game-blur.desktop`, `game-wwe-2k-battlegrounds.desktop`
  point at the old appids: after a replace, move the matching one to the Trash
  (`gio trash`), because the tool writes a new `steam-game-<name>.desktop`.
- Pictures are optional: `--cover F` (600x900), `--hero F` (1920x620),
  `--logo F` (transparent PNG), `--icon F` (square PNG), `--wide F` (920x430).
  The owner's pictures are not in this repo. Ask the owner for them or for
  permission to download from steamgriddb.com. An icon can also be pulled from
  the game's exe: `wrestool -x -t 14 Game.exe -o icon.ico && icotool -x icon.ico`
  (package `icoutils`).
- After adding icons to `~/.local/share/icons/hicolor`, run
  `gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor`.

**Check:** open Steam. All four games and Controller Settings are in the
Library. Right-click one → Properties: launch options = the launcher path,
Controller → "Disable Steam Input". To start one from a terminal (with the
owner's OK): `steam steam://rungameid/$(( (APPID<<32) | 0x02000000 ))` with
`APPID` from `list`.

---

## 9. Troubleshooting (symptom → cause → fix)

First read the game's log: `~/.cache/wine-games/<id>.log`
(`pes2019`, `blur`, `wwe2k-battlegrounds`; PES 2021 has no log file, run its
launcher from a terminal to see the output). Then the game's README. Then this
table.

| Symptom | Likely cause | Fix |
|---|---|---|
| Play does nothing / closes at once | Launcher not executable, wrong path in Steam, or Steam's environment leaked | `ls -l <launcher>`; check Properties → launch options; run `/media/Games/common/steam-launch.sh <launcher>` in a terminal and read the output. |
| `wine: could not load kernel32.dll` / prefix errors | Broken prefix | Make a fresh prefix (Phase D) **after** asking the owner: `gio trash ~/.wine-games` (never `~/.wine` without asking: other programs live there). The game folders and saves (`~/Documents/KONAMI`) stay. |
| Game exits right away, log mentions `MSVCP140`, `VCRUNTIME140`, `concrt140` | Missing Visual C++ runtime | `WINEPREFIX=<prefix> winetricks -q vcrun2022` (downloads from Microsoft: ask first). |
| `d3dx9_43.dll`, `d3dcompiler_47.dll` missing | DirectX extras | `WINEPREFIX=<prefix> winetricks -q d3dx9 d3dcompiler_47` (ask first). |
| Crash inside a Wine DLL (e.g. `msvcr90`) | Wine's builtin copy has a bug the game hits | Per-game override to Microsoft's copy: `WINEPREFIX=<prefix> wine reg add 'HKCU\Software\Wine\AppDefaults\<Game>.exe\DllOverrides' /v <dll> /d native,builtin /f`. Example: Blur. |
| Hitching / stutter every few seconds during play | `split_lock_mitigate` still 1 (not in `gamemode` group, or not restarted) | Phase B. Check `cat /proc/sys/kernel/split_lock_mitigate` during play → must be `0`. Kernel log lines `took a split_lock trap` show which threads do it: `journalctl -k -b \| grep split_lock`. |
| Uneven frame pacing at 60 fps | Screen stayed at 165 Hz, or a frame limiter on top of vsync | Log must not say `panel stays at its current rate`; dxvk.conf keeps `dxgi.maxFrameRate = -1`. |
| Game runs on the Intel GPU (slow) | NVIDIA variables missing or driver not loaded | `cat /proc/driver/nvidia/version`; the launcher exports `__NV_PRIME_RENDER_OFFLOAD=1` etc. With `hud` the overlay shows the GPU name. |
| No DXVK overlay with `hud` | DXVK not loaded | 64-bit: `alternatives --list \| grep dxvk` (Phase D). Blur: `d3d9.dll` missing from its folder or the `d3d9=n,b` override not set. |
| White window forever (PES 2019) | DXVK reports the RTX as AMD by default | `dxvk-pes2019.conf` has `dxgi.hideNvidiaGpu = False`. See [pes-2019/README.md](pes-2019/README.md). |
| Very slow start (40+ s white/black screen) | Split locks on P-cores at start | PES 2019 only: `pes2019-cores.py` + `pes2019-stack-fix.py`. |
| Pads do nothing in game | Steam Input on, pads not seen, or a pad holding buttons | [controllers/README.md](controllers/README.md). |
| Player 1 / 2 swapped | Player order | Controller Settings → drag in the PLAYERS strip → Apply. |
| No vibration (PES) | Game pulses too weak for the Twin USB pads | `rumble-boost` (built in Phase C). [pes-2021/README.md](pes-2021/README.md). |
| Settings.exe opens empty / no resolutions | Mixed-mode .NET tool under Wine Mono | Set resolution with `tools/pes-settings-dat.py`, graphics inside the game. |
| Online mode: network error `FDDN580` | Konami turned the PES 2019/2021 servers off (no DNS for `pes19-x64-gate` / `pes21-x64-gate` .konami.net, checked 15 Nov 2026) | Nothing to fix. Press OK; offline modes work. Internet itself works in both prefixes. |
| CPU stays hot / fast after the game | GameMode restored `performance` | `~/.config/gamemode.ini` with `defaultgov=powersave` (Phase B). |
| Game window has a gear icon in the dock | Missing dock `.desktop` or icon cache | Window classes: `pes2021.exe`, `pes2019.exe`, `blur.exe`, `wweplaygrounds-win64-shipping.exe`. `steam-shortcut.py add` writes the file; run `gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor`. |

If none fits, investigate, then **write what you found into the game's README**
(symptom, cause, fix, how you checked it), so the next AI does not start over.

---

## 10. Logs and where things are

| Path | What |
|---|---|
| `~/.cache/wine-games/<id>.log` | Game output (Wine + DXVK). `<id>` = `pes2019`, `blur`, `wwe2k-battlegrounds`. |
| `~/.cache/wine-games/pads.log` | What each pad got at every game start |
| `~/.cache/wine-games/pes2019-cores.log` | PES 2019 core switching (start-up on E-cores, then back) |
| `~/.cache/wine-games/pad-settings.log` | Controller Settings app output |
| `~/.cache/wine-games/steam-backup-*` | Steam files before each `steam-shortcut.py` change |
| `~/.config/game-pads/` | `mappings.txt` (saved maps), `auto-mappings.txt`, `player-order.json`, `gamecontrollerdb.txt` |
| `~/.config/environment.d/60-game-pads.conf` | Session-wide pad map for every SDL program |
| `~/.config/gamemode.ini` | `defaultgov=powersave` |
| `~/Documents/KONAMI/` | PES saves and `settings.dat` (Wine links the prefix's Documents here) |
| `~/.local/share/Steam/userdata/<id>/config/` | `shortcuts.vdf`, `localconfig.vdf`, `grid/` (artwork) |
| `~/.local/share/applications/*.desktop` | Hidden dock-icon entries (`NoDisplay=true`) |

---

## 11. Final check and report

When you are done, run all of these and paste the results to the owner:

```bash
rpm -q wine wine-dxvk gamemode steam sdl2-compat
getent group gamemode | grep -qw "$USER" && echo "gamemode group: yes"
cat /proc/sys/kernel/split_lock_mitigate
ls /media/Games/common/rumble-boost/libSDL2-2.0.so.0
python3 /media/Games/common/pes2019-stack-fix.py status
python3 -I /media/Games/common/pad_maps.py --json | head -40
python3 -I "$REPO/games/tools/steam/steam-shortcut.py" list
```

Then tell the owner, per game: what you changed, what you checked, and what is
still **not** checked (for example "did not play a full match"). Ask them to
press Play on each game once and tell you what happens.
