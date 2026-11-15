# WWE 2K Battlegrounds

> For the AI: do Phases A-F of [../AI-PROMPT.md](../AI-PROMPT.md) first, and
> follow its rules. This file is only what is special about this game.

## Facts

| Item | Value |
|---|---|
| Game folder | `/media/Games/WWE-2K-Battlegrounds` |
| Exe started | `WWEBattlegrounds.exe` (a small bootstrap that starts the real game and exits) |
| Real game exe | `WWEPlaygrounds/Binaries/Win64/WWEPlaygrounds-Win64-Shipping.exe` (64-bit, Unreal Engine 4, DirectX 11) |
| Wine prefix | `~/.wine-games` |
| Launcher | `/media/Games/common/play-wwe2k-battlegrounds.sh` (copy in [../common/](../common/play-wwe2k-battlegrounds.sh)) |
| Launcher options | `hud` = FPS overlay, `pads` = Wine's controller test window |
| Steam | "WWE 2K Battlegrounds", appid `2191877059` on this laptop |
| Window class (dock icon) | `wweplaygrounds-win64-shipping.exe` (the real exe, not the bootstrap); hidden entry `game-wwe-2k-battlegrounds.desktop`, icon `wwe-2k-battlegrounds` (taken from the Shipping exe) |
| Log | `~/.cache/wine-games/wwe2k-battlegrounds.log` |
| Status | Owner played it on 1 Nov 2026: saves written, clean exit, screen back to 165 Hz. |

## Install / repair (in order)

1. The launcher is in `/media/Games/common` (Phase C of AI-PROMPT). Nothing
   extra goes into the game folder.
2. DXVK comes from Fedora's `wine-dxvk` (64-bit), nothing to copy (Phase D).
3. Steam shortcut (only if missing): Phase F of AI-PROMPT. Pass
   `--wmclass WWEPlaygrounds-Win64-Shipping.exe` so the dock icon matches the
   real game window.

**Check:** start it (or ask the owner), then:
```bash
ps -eo pid,comm | grep -i -E 'wwe|shipping'
tail -50 ~/.cache/wine-games/wwe2k-battlegrounds.log
```
The Shipping exe must be running; the bootstrap may already be gone (normal).

## Known problems and their fixes

### Steam says the game stopped right after Play / the screen goes back to 165 Hz at once
- **Cause:** `WWEBattlegrounds.exe` only starts the real game and exits.
- **Fix (already in place):** `run_game` in `common/game-env.sh` runs
  `wine "$@"; wineserver -w`, so the session (60 Hz, power profile, Steam's
  "playing" state) stays until every Wine process of the prefix has exited.
  If this comes back, check that `game-env.sh` still has `wineserver -w`.
- Side effect: if any other Wine program of `~/.wine-games` is still running,
  the session waits for it too. `WINEPREFIX=~/.wine-games wineserver -k` ends it.

### In-game videos stay black
- **What was seen:** the first run logged CEF, GStreamer and `msvdsp.dll`
  video-decode errors (H.264 decoder and video-processor classes missing).
- **Check first** when a video is black: `grep -i -E 'gstreamer|h264|msvdsp|mfplat' ~/.cache/wine-games/wwe2k-battlegrounds.log`.
- **Possible fix (not tested here):** Wine decodes video through the
  system's GStreamer. This Wine is a WoW64 build, so only 64-bit Linux
  libraries matter. Install an H.264 decoder for GStreamer, e.g.
  `gstreamer1-plugin-openh264` (Fedora) or `gstreamer1-libav` (RPM Fusion).
  Ask the owner before installing. Then write the result here.

### Online features
2K's online services were never tested. Treat online errors as "not supported"
unless the owner asks to investigate.

## Not verified
- Pad buttons inside the game were not explicitly confirmed (pads work in
  Wine's controller window and in the other games with the same map).
- Whether in-game videos actually play.

## Undo
- Steam shortcut: Steam → right-click → Manage → Remove non-Steam game.
- Nothing else is changed in the game folder or the prefix for this game.
