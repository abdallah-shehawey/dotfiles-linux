#!/usr/bin/env python3
"""Eval JS in the private shell; print the decoded result (JSON pretty if possible)."""
import ast, json, os, subprocess, sys, pathlib
base = pathlib.Path(__file__).resolve().parent
env = os.environ.copy()
for line in (base / 'env.sh').read_text().splitlines():
    k, v = line.replace('export ', '', 1).split('=', 1)
    env[k] = v.strip("'")
code = sys.argv[2] if sys.argv[1] == '-e' else open(sys.argv[1]).read()
r = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell', '--object-path', '/org/gnome/Shell',
                    '--method', 'org.gnome.Shell.Eval', '--timeout', '300', code], env=env, capture_output=True, text=True)
out = r.stdout.strip()
if not out.startswith('('):
    print('ERR', r.stdout, r.stderr); sys.exit(1)
ok = out.startswith('(true')
s = ast.literal_eval('(' + ('True' if ok else 'False') + out[out.index(','):])[1]
try:
    v = json.loads(s)
    if isinstance(v, str):
        v = json.loads(v)
    print(('' if ok else 'FAILED ') + json.dumps(v, indent=1, ensure_ascii=False))
except Exception:
    print(('' if ok else 'FAILED ') + s)
