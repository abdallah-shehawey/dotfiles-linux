#!/usr/bin/env python3
"""usage.py NAME ROUNDS : everyday use with no forced GC; GPU memory after each round."""
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
from ovbench import gem
SP = pathlib.Path(__file__).resolve().parent
name, rounds = sys.argv[1], int(sys.argv[2])
pid = int(nest_env(name)['SHELL_PID'])
row = [gem(pid)['total']]
for i in range(rounds):
    for kind, n in (('overview', 8), ('dragresize', 2), ('maximize', 3), ('overview', 6)):
        ev(name, load(SP / 'actions.js', kind=kind, n=n))
    time.sleep(5)
    row.append(gem(pid)['total'])
print(f"{name}: GPU MB after each round (no forced GC): {row}", flush=True)
