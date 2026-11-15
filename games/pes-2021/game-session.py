#!/usr/bin/env python3
"""Run a command with the performance power profile and the panel at 60 Hz.

The game is locked to 60 fps, which judders on a 165 Hz panel (2.75 refreshes
per frame). Both changes last only as long as the command and are undone when
it exits. If either one is unavailable the command still runs.
"""
import signal
import subprocess
import sys

from gi.repository import Gio, GLib

PROFILE_NAME = "org.freedesktop.UPower.PowerProfiles"
PROFILE_PATH = "/org/freedesktop/UPower/PowerProfiles"
MUTTER_NAME = "org.gnome.Mutter.DisplayConfig"
MUTTER_PATH = "/org/gnome/Mutter/DisplayConfig"
METHOD_TEMPORARY = 1
TARGET_HZ = 60.0


def hold_performance(bus):
    # The hold is released by the daemon when this process disconnects
    return bus.call_sync(
        PROFILE_NAME, PROFILE_PATH, PROFILE_NAME, "HoldProfile",
        GLib.Variant("(sss)", ("performance", "Playing PES 2021", "pes2021")),
        GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, -1, None,
    )


def get_state(bus):
    return bus.call_sync(
        MUTTER_NAME, MUTTER_PATH, MUTTER_NAME, "GetCurrentState", None,
        None, Gio.DBusCallFlags.NONE, -1, None,
    ).unpack()


def apply_modes(bus, choose_mode):
    """Re-apply the current layout, asking choose_mode() for each monitor's mode."""
    serial, monitors, logical, _ = get_state(bus)
    modes_by_connector = {spec[0]: modes for spec, modes, _ in monitors}
    layout = []
    for x, y, scale, transform, primary, specs, _ in logical:
        outputs = []
        for spec in specs:
            mode = choose_mode(spec[0], modes_by_connector[spec[0]])
            outputs.append((spec[0], mode, {}))
        layout.append((x, y, scale, transform, primary, outputs))
    bus.call_sync(
        MUTTER_NAME, MUTTER_PATH, MUTTER_NAME, "ApplyMonitorsConfig",
        GLib.Variant("(uua(iiduba(ssa{sv}))a{sv})", (serial, METHOD_TEMPORARY, layout, {})),
        None, Gio.DBusCallFlags.NONE, -1, None,
    )


def set_60hz(bus):
    """Switch every active monitor to 60 Hz; return the modes to restore."""
    original = {}

    def choose(connector, modes):
        current = next(m for m in modes if m[6].get("is-current"))
        original[connector] = current[0]
        same_size = [m for m in modes if m[1:3] == current[1:3]]
        return min(same_size, key=lambda m: abs(m[3] - TARGET_HZ))[0]

    apply_modes(bus, choose)
    return original


def main():
    # A SIGTERM must still run the restore in the finally block
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    try:
        system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        hold_performance(system_bus)
    except GLib.Error as err:
        print(f"game-session: no performance profile: {err.message}", file=sys.stderr)

    session_bus = None
    original = None
    try:
        session_bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        original = set_60hz(session_bus)
    except (GLib.Error, StopIteration, KeyError) as err:
        print(f"game-session: panel stays at its current rate: {err}", file=sys.stderr)

    try:
        return subprocess.call(sys.argv[1:])
    finally:
        if original:
            apply_modes(session_bus, lambda connector, _: original[connector])


if __name__ == "__main__":
    sys.exit(main())
