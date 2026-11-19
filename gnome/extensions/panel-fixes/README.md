# Panel Fixes (`panel-fixes@local`)

Two repairs to the top bar, GNOME Shell 51 with Dash to Panel. Added 19 Nov 2026.

## Workspace dots

The inactive workspace dot next to the Fedora logo came up tiny after every
boot, and only switching the extensions off, logging out and back in, and
switching them on again fixed it.

Cause: a new dot grows in over 500 ms (`WorkspaceDot.scaleIn` in
`ui/panel.js`). At login Dash to Panel moves the Activities button out of the
panel's left box into its own panel (`remove_child` + `add_child`). If that
lands inside those 500 ms, Clutter drops the dot's transition and the dot keeps
the scale it had reached. Measured on the live session over AT-SPI: the second
dot's actor showed 5x20 px for a 7x30 px allocation (scale ~0.67). In a nested
shell, moving the button 60 ms into a `scaleIn` left the dot at 0.29 for good,
and the same during `scaleOutAndDestroy` left a dot that never goes away. With
the extensions switched on after login the dots already exist, nothing
animates, so the bug never shows: that is why the workaround worked.

Fix: `scaleIn` and `scaleOutAndDestroy` are wrapped; if the animation stops
without finishing, the dot is set to where it was going (scale 1, or
destroyed). Dots already frozen when the extension starts are repaired too.

## Tray order

AppIndicator inserts every new tray icon at index 1 of the right box. When the
extensions are switched on after the autostarted apps, those icons end up
further right, so an app opened later lands next to the net-speed indicator,
away from the other tray icons. A new tray icon now goes just before the first
tray icon already there; when the extensions start at login that is index 1
anyway, so normal boots look the same as before.

## Install

    ./install.sh

GNOME only finds a new extension when the shell starts, so it runs after the
next log out or reboot. The nested-shell tests used the harness in
`../rounded-corners-light/harness/` (`nest.py`, `ev.py`).
