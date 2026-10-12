#!/usr/bin/env python3
"""leak.py NAME KIND:N ... : GPU memory held only until a JS garbage collection, per action."""
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
from ovbench import gem
SP = pathlib.Path(__file__).resolve().parent
name = sys.argv[1]
pid = int(nest_env(name)['SHELL_PID'])
def gc():
    ev(name, load(SP / 'gc.js')); time.sleep(1.0)
gc()
for spec in sys.argv[2:]:
    kind, _, n = spec.partition(':'); n = int(n or 10)
    g0 = gem(pid)['total']
    ev(name, load(SP / 'actions.js', kind=kind, n=n))
    g1 = gem(pid)['total']; gc(); g2 = gem(pid)['total']
    print(f"{kind:10s} x{n:<3d} GPU {g0} -> {g1} MB (+{g1 - g0}) -> after GC {g2}  | waiting for GC {(g1 - g2) / n:5.1f} MB per action, kept {(g2 - g0) / n:+5.1f}", flush=True)
