# Keep GNOME Shell in RAM

Why (12 Oct 2026): the Overview opened late after the laptop sat idle. In a
private shell with the same 17 extensions, the first Overview frame came
~18 ms after Super with every extension off and ~30 ms with all on, but
~125-180 ms once the shell's memory had been pushed to swap. Most of that
pressure came from rounded-corners revision 6 pinning GPU buffers (fixed in
revision 7, see `gnome/extensions/rounded-corners-light`); this script makes
the shell the last thing to be swapped out either way.

`sudo ./protect-shell-memory.sh`, then reboot. It changes exactly:

| File | Change |
|---|---|
| `/etc/uresourced.conf` | `[ActiveUser] MemoryLow=2G`, `[SessionSlice] MemoryLow=1536M`, `[Global] MaxMemoryLow=20%` - a best-effort reservation for the logged-in session, where gnome-shell lives |
| `/etc/systemd/zram-generator.conf` | `compression-algorithm = zstd` (was lzo-rle): about a third more fits in the same zram, so less spills to the swap file on disk |

Backups go to `/etc/*.bak-20261012`; copy them back to undo.

State on the laptop: run 12 Oct 11:32, rebooted 11:44. After the reboot zram
reports `zstd`, and the cgroups carry the reservation: `memory.low` is 2G on
`user-1000.slice` and `user@1000.service`, 1.5G on `session.slice`
(cgroup2 is mounted with `memory_recursiveprot`, so the shell inside it shares
that protection).

## Checking it: `watch-shell-memory.py`

Read-only. Logs the live gnome-shell every few seconds to
`~/.local/state/gnome-performance/shell-memory-<boot>.csv`: GPU buffers from
the i915 fdinfo, RSS and swap, its cgroup, system swap and zram, its CPU, and
how many times the Overview opened (the shell's `OverviewActive` D-Bus
property). Run it as a user unit so it outlives the terminal:

    systemd-run --user --unit=shell-memory-watch -p RuntimeMaxSec=31000 \
        /usr/bin/python3 "$PWD/watch-shell-memory.py" 8 5
    ./watch-shell-memory.py summary       # trend of the newest log
    systemctl --user stop shell-memory-watch

GPU memory that only climbs with Overview visits and window resizes, and never
comes back down after a few idle seconds, is the leak revision 6 had.
