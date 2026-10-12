#!/usr/bin/env python3
"""ovcycle.py NAME ROUNDS : live GPU memory (total - purgeable) after each round of
10 Overview visits, 6 s later, with no forced GC: what everyday use leaves pinned."""
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
SP = pathlib.Path(__file__).resolve().parent
UNITS = {'': 1, 'KiB': 1 << 10, 'MiB': 1 << 20}
name, rounds = sys.argv[1], int(sys.argv[2])
pid = int(nest_env(name)['SHELL_PID'])


def live():
    best = {}
    for f in pathlib.Path(f'/proc/{pid}/fdinfo').iterdir():
        try:
            txt = f.read_text()
        except OSError:
            continue
        v = {}
        for line in txt.splitlines():
            k, _, val = line.partition(':')
            if k in ('drm-total-system0', 'drm-purgeable-system0'):
                num, *unit = val.split()
                v[k.split('-')[1]] = int(num) * UNITS[unit[0] if unit else ''] >> 20
        if v.get('total', -1) > best.get('total', -1):
            best = v
    return best['total'] - best['purgeable']


row = [live()]
for _ in range(rounds):
    ev(name, load(SP / 'actions.js', kind='overview', n=10))
    time.sleep(6)
    row.append(live())
print(f'{name}: live GPU MB after each 10 Overview visits: {row}', flush=True)
