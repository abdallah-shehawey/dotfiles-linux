# Controllers (shared by every game)

> For the AI: read [../AI-PROMPT.md](../AI-PROMPT.md) first (rules, phases).
> This file is everything about the pads: how the map is built, the
> Controller Settings app, and how to fix pad problems.

## Facts

| Item | Value |
|---|---|
| Pads | Generic PS2-style pads on **Twin USB** adapters, USB ID `0810:0001`, name `Twin USB Gamepad`. One adapter = one HID device with two pads (two `/dev/input/event*` nodes). Two adapters are used (4 ports). |
| Kernel driver | `hid-pl` (pantherlord). It supports rumble but scales full strength down to about half of the motor range. |
| Map files | `~/.config/game-pads/mappings.txt` (saved by the owner, copy in [../config/game-pads/mappings.txt](../config/game-pads/mappings.txt)), `auto-mappings.txt` (guesses for unknown pads), `player-order.json`, `gamecontrollerdb.txt` (session file) |
| Code | `common/pads.sh` (sourced by every launcher) → `common/pad_maps.py`; app `common/pad-settings.py` started by `common/controller-settings.sh` |
| Steam shortcut | "Controller Settings", appid `3501849340`, Steam Input off |
| Log | `~/.cache/wine-games/pads.log`, `~/.cache/wine-games/pad-settings.log` |
| On screen in games | Xbox letters: **A = ✕ Cross, B = ○ Circle, X = □ Square, Y = △ Triangle** |

## How it works

1. A launcher sets `WINEPREFIX`, then sources `common/pads.sh`.
2. `pads.sh` runs `pad_maps.py`, which prints shell `export` lines:
   - `SDL_GAMECONTROLLERCONFIG` = one map line per pad type. Sources, later
     wins: SDL's built-in list → Steam's list (`STEAM_PAD_MAPPINGS`, passed on
     by `steam-launch.sh`, plus pads set in Steam's controller settings) → the
     built-in Twin USB line → PlayStation-style guesses for unknown pads (kept
     in `auto-mappings.txt` once seen) → the owner's maps from Controller
     Settings (`mappings.txt`).
   - `SDL_JOYSTICK_DEVICE` = the pads' event nodes in **player order**.
3. Wine's `winebus` reads the pads through SDL2 and gives them to the game as
   XInput pads. **Wine reads these variables only when the prefix starts.**
   If a Wine program of that prefix is already running, a new map is ignored:
   `WINEPREFIX=<prefix> wineserver -k`, then start the game again.

Every game gets the **same** map. (An old PES-only L1/L2 swap was removed on
3 Nov 2026: the pads themselves report L1/L2 reversed, and the owner now sets
every button by hand in Controller Settings.)

### Player order (non-obvious)

- Default = plug-in order (oldest first); a broken pad goes last.
- The PLAYERS strip in Controller Settings is drag-and-drop (or Alt+←/→ on
  the selected pad). Apply/OK writes `player-order.json`, keyed by the pad's
  socket: `ID_PATH` (or Bluetooth address) + `#<input index on the HID device>`,
  with `vid:pid#index` as a fallback when an adapter moves to another USB port.
- Under Wine, XInput fills its 4 slots in the **sorted order of a device
  name** like `HID#VID_0810&PID_0001&XI_00#3&<hash>&0&0000`. The `<hash>` is
  FNV-1 32-bit (`h = h*16777619 ^ c`, start `0x811c9dc5`) of the parent
  instance path, and winebus names pads `1&f33442ae&0&<open index in hex>`.
  So slot order is **not** simply the open order. `pad_maps.py`
  (`open_order()`, `plan_slots()`) orders `SDL_JOYSTICK_DEVICE` so the slots
  come out in player order. Verified: slot 0-3 = the four pads in order.
  Different pad **models** always sort by VID/PID first; the app warns about
  that. Pads SDL drives through HIDAPI (DualShock 4 / DualSense) are untested.

### ANALOG button on the PS2 pads

- ANALOG **off**: the pad sends the left stick as the d-pad (X/Y axes at
  0/127/255) and the right stick as buttons 1-4. Software cannot separate
  them. Tell the owner to press ANALOG (red LED on).
- ANALOG **on**: d-pad = hat, left stick = X/Y, right stick = Rz (right X) /
  Z (right Y).

### A broken pad

A pad on adapter 1, port 2 is broken: it holds buttons 1, 4 and 9 down with
X/Y at 0. `pad_maps.py` moves any pad holding 2+ buttons at start to the
**last** slot, and the app flags it. If a game "presses buttons by itself",
unplug that adapter port or check `pads.log`.

## Controller Settings app

GTK4 / libadwaita, Steam dark colours, English, PlayStation symbols on a
drawn Xbox-One-shaped pad (layout copied from PES 2021's Settings → Controller
tab: picture in the middle, button lists left and right, Revert under the
picture, OK / Cancel). Maps are per pad **type** (SDL GUID), so both Twin USB
adapters share one map.

How the owner uses it: Steam → Controller Settings → Play. Click a function's
box, press the pad button. Apply saves, OK saves and closes, Revert = default
for this pad. The owner confirmed on 3 Nov 2026 that the app and the pads in
games work ("All good").

Needs: `python3-gobject`, `gtk4`, `libadwaita`, `python3-cairo`, SDL3 (`SDL3`).
It does **not** start? Read `~/.cache/wine-games/pad-settings.log`. Test it
without Steam: `/media/Games/common/controller-settings.sh`.

## Checks

```bash
# every connected pad and the map it gets
python3 -I /media/Games/common/pad_maps.py --json
# the exports a launcher will use (long output)
python3 -I /media/Games/common/pad_maps.py | tail -3
# which event nodes are Twin USB pads
grep -l -i 'twin usb' /sys/class/input/event*/device/name
# Windows' own controller test window, inside the right prefix, with the map
/media/Games/common/play-blur.sh pads          # ~/.wine-games
/media/Games/eFootball-PES-2021/play-pes2021.sh pads   # ~/.wine
```

In the `pads` window (Wine's joy.cpl), the XInput tab must list the pads, and
each button press must light the right button.

## Problems → fixes

| Symptom | Cause | Fix |
|---|---|---|
| No pad in game | Steam Input on (Steam grabs the pad), or the game was started without the launcher | Steam → game → Properties → Controller → Disable Steam Input. Launch options must be the launcher. |
| Pad works in joy.cpl but not in game | Game only reads XInput slot 0, and slot 0 is the broken/other pad | Fix player order in Controller Settings. |
| Buttons wrong in every game | Saved map | Controller Settings → set the buttons → Apply. Or restore `../config/game-pads/mappings.txt`. |
| Change in Controller Settings ignored | Prefix still running with the old map | `WINEPREFIX=<prefix> wineserver -k`, start the game again. |
| Sticks act like the d-pad | ANALOG off | Press ANALOG on the pad. |
| Pad plugged in mid-game not seen | `SDL_JOYSTICK_DEVICE` was fixed at start | Restart the game with the pad plugged in. |
| Player 1 / 2 swapped | Order | Drag in the PLAYERS strip → Apply. "Default Order" = plug order. |
| Weak or no vibration in PES | Game pulses are too short/weak for `hid-pl` | `rumble-boost`, see [../pes-2021/README.md](../pes-2021/README.md#no-vibration). |

## Testing tools (for the AI)

**Inject a real button press** into a pad (works in a running game; the game
window must have focus). Twin USB codes: Cross `0x122`, Circle `0x121`,
R1 `0x127`, Start `0x129`. A new virtual (`uinput`) pad is **not** seen by
the games, because `pads.sh` pins `SDL_JOYSTICK_DEVICE` to the real pads, so
inject into the real node:

```python
# python3 press.py /dev/input/event16 0x122
import struct, sys, time
dev, code = sys.argv[1], int(sys.argv[2], 16)
EV_KEY, EV_SYN = 1, 0
def ev(f, t, c, v):
    s = time.time()
    f.write(struct.pack('llHHi', int(s), int((s % 1) * 1e6), t, c, v))
with open(dev, 'wb', buffering=0) as f:
    for value in (1, 0):            # press, release
        ev(f, EV_KEY, code, value); ev(f, EV_SYN, 0, 0)
        time.sleep(0.08)
```

D-pad: send **both** the hat (`ABS_HAT0X`/`ABS_HAT0Y`, type 3) and the X/Y
axes. That drove PES 2019's menus on 15 Nov 2026. A hat-only press is lost,
because the adapter's next report re-centres it.
`/dev/uinput` is writable by the user, so virtual pads can be made for tests
of `pad_maps.py` itself.
