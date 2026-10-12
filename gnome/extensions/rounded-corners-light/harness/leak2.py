#!/usr/bin/env python3
"""leak2.py NAME KIND N : GPU memory timeline around N actions (before GC, after GC, settled)."""
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
from ovbench import gem
SP = pathlib.Path(__file__).resolve().parent
name, kind, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
pid = int(nest_env(name)['SHELL_PID'])
g = lambda: gem(pid)['total']
ev(name, load(SP / 'actions.js', kind=kind, n=2)); ev(name, load(SP / 'gc.js')); time.sleep(4)
t = [('start', g())]
ev(name, load(SP / 'actions.js', kind=kind, n=n)); t.append(('after', g()))
time.sleep(4); t.append(('+4s', g()))
ev(name, load(SP / 'gc.js')); time.sleep(1); t.append(('gc+1s', g()))
time.sleep(5); t.append(('gc+6s', g()))
print(f"{name} {kind} x{n}: " + '  '.join(f'{k}={v}' for k, v in t) + f"  | held until GC per action: {(t[2][1] - t[3][1]) / n:.1f} MB, net {(t[4][1] - t[0][1]) / n:+.1f}")
