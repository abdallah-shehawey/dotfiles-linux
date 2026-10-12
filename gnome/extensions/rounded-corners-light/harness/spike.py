#!/usr/bin/env python3
"""spike.py NAME KIND N [REPS] [--no-gc] : the transient GPU memory an action
costs, not what it leaves behind. Samples the shell's GEM every 20 ms while
KIND runs N times, then 20 s more. Run REPS times (default 3) after one
warm-up run, each after a forced GC unless --no-gc.

"live" is GEM total minus purgeable: Mesa keeps freed buffers in its cache
marked purgeable (the kernel takes them back under pressure, without swap)
and recycles them for the next allocations, so the total alone hides both
what was freed and what was pinned."""
import pathlib, statistics, sys, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
SP = pathlib.Path(__file__).resolve().parent
UNITS = {'': 1, 'KiB': 1 << 10, 'MiB': 1 << 20}
name, kind, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
args = [a for a in sys.argv[1:] if not a.startswith('--')]
reps = int(args[3]) if len(args) > 3 else 3
env = nest_env(name)
pid = int(env['SHELL_PID'])
cg = pathlib.Path(env['SHELL_CGROUP'])


def total(f):
    for line in f.read_text().splitlines():
        if line.startswith('drm-total-system0:'):
            num, *unit = line.split(':', 1)[1].split()
            return int(num) * UNITS[unit[0] if unit else '']
    return -1


# A shell can hold several DRM clients; the one that renders owns the most.
fd = max(pathlib.Path(f'/proc/{pid}/fdinfo').iterdir(), key=total)


def sample():
    v = {}
    for line in fd.read_text().splitlines():
        k, _, val = line.partition(':')
        # Exact keys: drm-total-stolen-system0 also ends in -system0.
        if k in ('drm-total-system0', 'drm-shared-system0', 'drm-purgeable-system0'):
            num, *unit = val.split()
            v[k.split('-')[1]] = int(num) * UNITS[unit[0] if unit else ''] >> 20
    for line in open(cg / 'memory.stat'):
        k, val = line.split()
        if k == 'shmem':
            v['shmem'] = int(val) >> 20
            break
    return v


def run_once():
    if '--no-gc' not in sys.argv:
        ev(name, load(SP / 'gc.js'))
    time.sleep(3)
    rows, done = [], threading.Event()

    def sampler():
        while not done.is_set():
            rows.append((time.monotonic(), sample()))
            time.sleep(0.02)

    th = threading.Thread(target=sampler)
    th.start()
    time.sleep(1)
    t0 = time.monotonic()
    if kind.startswith('drag:'):
        _, title, *steps = kind.split(':')
        for _ in range(n):
            ev(name, load(SP / 'drag2.js', title=title, steps=int(steps[0]) if steps else 120))
    else:
        ev(name, load(SP / 'actions.js', kind=kind, n=n))
    t1 = time.monotonic()
    time.sleep(20)
    done.set()
    th.join()
    live = lambda s: s['total'] - s['purgeable']
    base = statistics.median(live(s) for t, s in rows if t < t0)
    during = [(t, s) for t, s in rows if t >= t0]
    tp, peak = max(during, key=lambda r: live(r[1]))
    after = lambda dt: live(min((r for r in rows if r[0] >= t1 + dt), key=lambda r: r[0])[1])
    back = next((t - t1 for t, s in rows if t >= t1 and live(s) <= base + 30), None)
    return (f"live base {base:.0f}  peak {live(peak)} (+{live(peak) - base:.0f}) at {tp - t0:.1f}s "
            f"of {t1 - t0:.1f}s | after end +1s {after(1)}, +3s {after(3)}, +8s {after(8)}, "
            f"+19s {after(19)} | back within 30 MB "
            f"{'never' if back is None else f'{back:.1f}s after end'}")


run_once()
for i in range(reps):
    print(f'{name} {kind} x{n} #{i + 1}: {run_once()}', flush=True)
