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

State on the laptop: run on 12 Oct (both backups exist, both files changed);
zram still showed `lzo-rle` until the next reboot.
