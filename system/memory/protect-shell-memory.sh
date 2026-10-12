#!/bin/bash
# Keep GNOME Shell's memory in RAM under pressure, and let zram hold more.
# Run once with sudo, then reboot. Backups: /etc/*.bak-20261012.
#
# uresourced (Fedora) already reserves 250M for the active session; this adds
# a best-effort MemoryLow: 2G for the active user, 1.5G of it for session.slice,
# where gnome-shell lives, so its pages are not swapped out while apps still
# have reclaimable memory. zram switches lzo-rle -> zstd (about a third more
# data in the same RAM, so less spills to the disk swap file).
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo"; exit 1; }
cp -n /etc/uresourced.conf /etc/uresourced.conf.bak-20261012
cp -n /etc/systemd/zram-generator.conf /etc/systemd/zram-generator.conf.bak-20261012
python3 - <<'PY'
import re
p = '/etc/uresourced.conf'
want = {'Global': {'MaxMemoryLow': '20%'}, 'ActiveUser': {'MemoryLow': '2G'},
        'SessionSlice': {'MemoryLow': '1536M'}}
out, sec, done = [], None, set()
def flush():
    for k, v in want.get(sec, {}).items():
        if (sec, k) not in done:
            out.append(f'{k}={v}')
            done.add((sec, k))
for line in open(p).read().splitlines():
    m = re.match(r'\s*\[(\w+)\]', line)
    if m:
        flush()
        sec = m.group(1)
        out.append(line)
        continue
    m = re.match(r'\s*#?\s*(\w+)\s*=', line)
    if m and m.group(1) in want.get(sec, {}):
        if (sec, m.group(1)) not in done:
            out.append(f'{m.group(1)}={want[sec][m.group(1)]}')
            done.add((sec, m.group(1)))
        continue
    out.append(line)
flush()
open(p, 'w').write('\n'.join(out) + '\n')
PY
grep -q '^compression-algorithm' /etc/systemd/zram-generator.conf ||
    sed -i '/^\[zram0\]/a compression-algorithm = zstd' /etc/systemd/zram-generator.conf
echo '--- /etc/uresourced.conf (active lines)'; grep -vE '^\s*(#|$)' /etc/uresourced.conf
echo '--- /etc/systemd/zram-generator.conf'; cat /etc/systemd/zram-generator.conf
echo 'Done. Reboot to apply.'
