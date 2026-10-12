#!/usr/bin/env python3
"""Super-tap latency of the Overview in a private shell: ovbench.py NAME [--runs N] [--cold max] [--rewarm S]"""
import argparse, errno, json, os, pathlib, statistics, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
SP = pathlib.Path(__file__).resolve().parent


def memstat(cg):
    d = {}
    for line in open(f'{cg}/memory.stat'):
        k, v = line.split()
        if k in ('anon', 'file', 'shmem'):
            d[k] = int(v) >> 20
    return d


def reclaim(cg, amount):
    try:
        with open(f'{cg}/memory.reclaim', 'w') as f:
            f.write('4G' if amount == 'max' else amount)
    except OSError as e:
        if e.errno != errno.EAGAIN:
            raise


def gem(pid):
    for fd in os.listdir(f'/proc/{pid}/fdinfo'):
        try:
            txt = open(f'/proc/{pid}/fdinfo/{fd}').read()
        except OSError:
            continue
        if 'drm-total-system0' in txt:
            v = {}
            for line in txt.splitlines():
                k, _, val = line.partition(':')
                if k in ('drm-total-system0', 'drm-shared-system0', 'drm-resident-system0'):
                    # The kernel prints the largest unit that divides the size.
                    n, *unit = val.split()
                    v[k.split('-')[1]] = int(n) * {'': 1, 'KiB': 1 << 10, 'MiB': 1 << 20}[unit[0] if unit else ''] >> 20
            return v
    return {}


def stats(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return {'n': len(xs), 'min': xs[0], 'med': round(statistics.median(xs), 1),
            'p90': xs[min(len(xs) - 1, int(len(xs) * 0.9))], 'max': xs[-1]}


def bench(name, runs=10, gap=1.0, cold=None, rewarm=0.0, quiet=True):
    env = nest_env(name)
    cg = env['SHELL_CGROUP']
    rows = []
    for i in range(runs):
        time.sleep(gap)
        delay = int(1500 + rewarm * 1000) if cold else 150
        ev(name, load(SP / 'ov_arm.js', delay=delay))
        t = time.monotonic()
        if cold:
            reclaim(cg, cold)
        time.sleep(max(0.0, delay / 1000 - (time.monotonic() - t)) + 0.15)
        r = ev(name, load(SP / 'ov_collect.js'))
        rows.append(r)
        if not quiet:
            print(f"  #{i}: {r}", flush=True)
    return {'runs': rows, 'summary': {k: stats([r[k] for r in rows]) for k in
                                      ('showing', 'firstPaint', 'shown', 'maxGap', 'majflt', 'cpu')}}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('name'); p.add_argument('--runs', type=int, default=10)
    p.add_argument('--cold'); p.add_argument('--rewarm', type=float, default=0.0)
    a = p.parse_args()
    print(json.dumps(bench(a.name, a.runs, cold=a.cold, rewarm=a.rewarm, quiet=False)['summary']))
