#!/usr/bin/env python3
"""stepwise.py NAME [--no-fixtures] [--no-gc] : GPU memory at each step of a session, to see which
step leaves memory behind: start, two windows, GC, drags of each window (with a GC after)."""
import pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
SP = pathlib.Path(__file__).resolve().parent
UNITS = {'': 1, 'KiB': 1 << 10, 'MiB': 1 << 20}
name = sys.argv[1]


def gem():
    env = nest_env(name)
    pid, cg = int(env['SHELL_PID']), pathlib.Path(env['SHELL_CGROUP'])
    best = {}
    for f in pathlib.Path(f'/proc/{pid}/fdinfo').iterdir():
        try:
            txt = f.read_text()
        except OSError:
            continue
        v = {}
        for line in txt.splitlines():
            k, _, val = line.partition(':')
            if k in ('drm-total-system0', 'drm-shared-system0', 'drm-purgeable-system0'):
                num, *unit = val.split()
                v[k.split('-')[1]] = int(num) * UNITS[unit[0] if unit else ''] >> 20
        if v.get('total', -1) > best.get('total', -1):
            best = v
    shm = next(int(l.split()[1]) >> 20 for l in open(cg / 'memory.stat') if l.startswith('shmem '))
    return f"GEM {best.get('total')} (shared {best.get('shared')}, purgeable {best.get('purgeable')}), cg shmem {shm}"


def step(label, wait=2):
    time.sleep(wait)
    print(f'{label:<34} {gem()}', flush=True)


def gc():
    ev(name, load(SP / 'gc.js'))


step('started')
gc(); step('GC')
if '--no-fixtures' not in sys.argv:
    subprocess.run([sys.executable, str(SP / 'fix_min.py'), name], check=True)
    step('two windows')
    gc(); step('GC')
    for title in ('files', 'files', 'cad-x11', 'cad-x11'):
        ev(name, load(SP / 'drag2.js', title=title, steps=120))
        step(f'drag {title}: just after', 0)
        step(f'drag {title}: +3 s', 3)
        if '--no-gc' in sys.argv:
            step(f'drag {title}: +6 s', 3)
        else:
            gc(); step(f'drag {title}: GC', 2)
