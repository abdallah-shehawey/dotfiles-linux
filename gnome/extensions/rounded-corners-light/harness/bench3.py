#!/usr/bin/env python3
"""bench3.py OUT.jsonl : fresh private shells, one at a time: none / all with rev 6 / all with rev 7.
Hot: 30 Super taps. Cold: 10 taps, each after paging the shell out and 6 s of re-warm."""
import json, os, pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ovbench import bench, gem
from ev import nest_env
SP = pathlib.Path(__file__).resolve().parent
R7 = str(SP.parent / 'rounded-corners-light@local')
CONFIGS = [('none', 'none', {}), ('rev6', 'all', {}), ('rev7', 'all', {'NEST_EXT_OVERRIDE': f'rounded-corners-light@local={R7}'})]
out = sys.argv[1]
for label, spec, extra in CONFIGS * 2:
    env = dict(os.environ, **extra)
    subprocess.run([sys.executable, str(SP / 'nest.py'), 'start', 'b3', spec], env=env, check=True, stdout=subprocess.DEVNULL)
    try:
        subprocess.run([sys.executable, str(SP / 'fix.py'), 'b3'], check=True, stdout=subprocess.DEVNULL)
        time.sleep(3)
        first = bench('b3', runs=1, gap=0.5)['runs'][0]
        bench('b3', runs=3, gap=0.8)
        hot = bench('b3', runs=30, gap=1.0)
        cold = bench('b3', runs=10, gap=1.0, cold='max', rewarm=6.0)
        rec = {'label': label, 'first': first, 'hot': hot, 'cold': cold}
        with open(out, 'a') as f:
            f.write(json.dumps(rec) + '\n')
        h, c = hot['summary'], cold['summary']
        print(f"{label:5s} first={first['firstPaint']:>6} | hot show={h['showing']['med']:>5} paint={h['firstPaint']['med']:>5} "
              f"p90={h['firstPaint']['p90']:>5} max={h['firstPaint']['max']:>6} cpu={h['cpu']['med']:>4} | cold show={c['showing']['med']:>6} "
              f"paint={c['firstPaint']['med']:>6} p90={c['firstPaint']['p90']:>6} majflt={c['majflt']['med']:>6}", flush=True)
    finally:
        subprocess.run([sys.executable, str(SP / 'nest.py'), 'stop', 'b3'], stdout=subprocess.DEVNULL)
        time.sleep(3)
