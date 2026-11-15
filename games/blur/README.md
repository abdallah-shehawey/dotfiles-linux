# Blur

> For the AI: do Phases A-F of [../AI-PROMPT.md](../AI-PROMPT.md) first, and
> follow its rules. This file is only what is special about Blur.

## Facts

| Item | Value |
|---|---|
| Game folder | `/media/Games/Blur` |
| Exe | `Blur.exe` (**32-bit**, DirectX 9) |
| Wine prefix | `~/.wine-games` |
| Launcher | `/media/Games/common/play-blur.sh` (copy in [../common/](../common/play-blur.sh)) |
| Launcher options | `pads` = Wine's controller test window, `wined3d` = run on Wine's own D3D9 instead of DXVK |
| Extra file in the game folder | `d3d9.dll` = 32-bit DXVK |
| Steam | "Blur", appid `2974620932` on this laptop |
| Window class (dock icon) | `blur.exe`; hidden entry `game-blur.desktop`, icon `blur-game` (cropped from `Blur/Bonus/Wallpapers/Blur.Wallpapers.01.jpg`, because the exe only has a 32x32 icon) |
| Log | `~/.cache/wine-games/blur.log` |
| Status | Owner played it on 1 Nov 2026: saves written, clean exit, screen back to 165 Hz. Rumble works in Blur. |

## Install / repair (in order)

Fast path: `cd "$REPO/games" && ./install.sh && ./check.sh` does every step
below. The steps are here to understand and to do by hand.

1. **32-bit DXVK into the game folder.** Fedora's `wine-dxvk` is 64-bit only,
   so a 32-bit DX9 game would get Wine's slower own D3D9. Take the 32-bit
   `d3d9.dll` from Steam's **Proton Experimental** (no download from the web;
   if it is missing, ask the owner to install Proton Experimental in Steam:
   Library → Tools):
   ```bash
   P="$HOME/.local/share/Steam/steamapps/common/Proton - Experimental/files/lib/wine/dxvk/i386-windows/d3d9.dll"
   ls -l "$P"                       # must exist; if not, Proton Experimental is not installed
   [ -f /media/Games/Blur/d3d9.dll ] && cp -a /media/Games/Blur/d3d9.dll /media/Games/Blur/d3d9.dll.bak-$(date +%F)
   cp "$P" /media/Games/Blur/d3d9.dll
   ```
   The launcher sets `WINEDLLOVERRIDES="d3d9=n,b"` so Wine uses that file.
   The copy on this laptop is DXVK v3.1.1 (Proton Experimental, 27 Oct 2026).
2. **The crash fix** (see below):
   ```bash
   WINEPREFIX=~/.wine-games wine reg add 'HKCU\Software\Wine\AppDefaults\Blur.exe\DllOverrides' /v msvcr90 /d native,builtin /f
   ```
3. Steam shortcut with its pictures: [Steam pictures and dock icon](#steam-pictures-and-dock-icon).

**Check:**
```bash
WINEPREFIX=~/.wine-games wine reg query 'HKCU\Software\Wine\AppDefaults\Blur.exe\DllOverrides'   # msvcr90 = native,builtin
ls -l /media/Games/Blur/d3d9.dll
grep -c 'err:d3d' ~/.cache/wine-games/blur.log    # after a run: 0
```

## Steam pictures and dock icon

| File in [art/](art/) | Steam slot | Size |
|---|---|---|
| `cover.png` | Library cover (grid `<appid>p.png`) | 600x900 |
| `wide.png` | Wide capsule (grid `<appid>.png`) | 920x430 |
| `hero.png` | Banner on the game page (grid `<appid>_hero.png`) | 1920x620 |
| `logo.png` | Logo over the banner (grid `<appid>_logo.png`) | 1160x480 |
| `icon.png` | Shortcut icon + dock icon `blur-game` | 256x256 |

Made from the wallpapers that ship with the game (`Blur/Bonus/Wallpapers/`).
The owner likes these; keep them. Install (Steam closed):
```bash
T="$REPO/games/tools/steam/steam-shortcut.py"; A="$REPO/games/blur/art"
python3 -I "$T" add --name "Blur" --launcher /media/Games/common/play-blur.sh \
    --exe /media/Games/Blur/Blur.exe --wmclass blur.exe \
    --desktop-id game-blur --icon-name blur-game \
    --cover "$A/cover.png" --wide "$A/wide.png" --hero "$A/hero.png" --logo "$A/logo.png" --icon "$A/icon.png"
```
By hand: AI-PROMPT section 8.2. Dock entry: [../config/applications/game-blur.desktop](../config/applications/game-blur.desktop)
(window class `blur.exe`; do not use the old ids `blur.desktop`).

## Game settings

| File in [settings/](settings/) | Goes to | Holds |
|---|---|---|
| `settings.xml` | `~/.wine-games/drive_c/users/$USER/AppData/Roaming/bizarre creations/blur/settings.xml` | 2560x1440, full screen (`windowed="0"`), vsync on, graphical detail 4 |

`./install.sh` puts it back when it is missing; `./install.sh --restore-settings`
also over an existing one (backup first). The race saves are next to it in
`save/blursave` and are not in this repo. The only per-game Wine setting is
the `msvcr90` override below.

## Known problems and their fixes

### Crash in the middle of a race
- **Symptom:** page fault in Wine's `msvcr90!__rem_pio2` (1 Nov 2026).
- **Cause:** the game passes a huge angle (about 2.4e27) to `sin`/`cos` while
  the x87 FPU is at 24-bit precision (the crash values prove the precision;
  d3d9 setting it is likely, and Blur also calls `_controlfp_s`). Wine's
  `__rem_pio2_large` then overruns its `double q[20]` and overwrites saved
  registers.
- **Fix:** Blur uses Microsoft's real `msvcr90.dll` instead of Wine's:
  per-app override `HKCU\Software\Wine\AppDefaults\Blur.exe\DllOverrides`
  `msvcr90 = native,builtin` in `~/.wine-games` (command above). Blur's
  manifest loads Microsoft 9.0.21022.8 from the prefix's `winsxs`.
- **The real DLL must be there:**
  ```bash
  ls ~/.wine-games/drive_c/windows/winsxs | grep -i 'x86_microsoft.vc90.crt_.*9.0.21022.8'
  ```
  The files there are genuine Microsoft DLLs installed by the game's
  installer. Their manifests hold each file's SHA1 in `dsig:DigestValue`; a
  genuine copy matches. If the folder is missing (new prefix), install the
  runtime: `WINEPREFIX=~/.wine-games winetricks -q vcrun2008` (download from
  Microsoft: ask the owner first). **If a SHA1 check fails, stop before
  overwriting anything there.**
- A scratch test exe with the exact crash value crashed before the fix and
  exits cleanly after it.

### Slow / low FPS
- `d3d9.dll` missing from the game folder, or the override not active: the
  log then shows Wine's own d3d9 (`err:d3d:` lines are a sign). Redo step 1.
- To compare, `play-blur.sh wined3d` runs Wine's own D3D9.

### Log full of `FIRST : Potentially bad data`
The game's own harmless spam. Ignore it.

### Re-installing the game
- The first setup run stalled with no window right after installing fonts;
  the second run worked. Cause never found: just run it again.
- To see where a Wine program hangs, do **not** attach `winedbg` (under WoW64
  it killed the setup). Use a limited `+relay` through
  `HKCU\Software\Wine\Debug\RelayInclude` instead.
- The setup's icon is not Blur's own icon. Do not use it for the shortcut.

## Not verified
- A full race played by an AI (the owner raced; after the msvcr90 fix only a
  scratch test exe was run by the AI).
- Pad buttons inside Blur were not explicitly confirmed (rumble was).

## Undo
- DXVK: remove `/media/Games/Blur/d3d9.dll` (to the Trash) or use `play-blur.sh wined3d`.
- Crash fix: `WINEPREFIX=~/.wine-games wine reg delete 'HKCU\Software\Wine\AppDefaults\Blur.exe\DllOverrides' /v msvcr90 /f`.
