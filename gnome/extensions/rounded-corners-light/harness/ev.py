#!/usr/bin/env python3
"""Eval JS in a private shell: ev.py NAME (-e CODE | FILE) [key=value ...]"""
import ast, json, os, pathlib, subprocess, sys

SP = pathlib.Path(__file__).resolve().parent


def nest_env(name):
    env = os.environ.copy()
    for line in (SP / f'nest-{name}' / 'env.sh').read_text().splitlines():
        k, v = line.replace('export ', '', 1).split('=', 1)
        env[k] = v.strip("'")
    return env


def ev(name, code, timeout=600):
    env = nest_env(name)
    r = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell', '--object-path',
                        '/org/gnome/Shell', '--method', 'org.gnome.Shell.Eval', '--timeout', str(timeout),
                        code], env=env, capture_output=True, text=True)
    out = r.stdout.strip()
    if not out.startswith('('):
        raise RuntimeError(f'Eval failed: {r.stdout} {r.stderr}')
    ok = out.startswith('(true')
    s = ast.literal_eval('(' + ('True' if ok else 'False') + out[out.index(','):])[1]
    if not ok:
        raise RuntimeError('JS: ' + s)
    try:
        v = json.loads(s)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                pass
        return v
    except Exception:
        return s


def load(path, **args):
    return pathlib.Path(path).read_text().replace('__ARGS__', json.dumps(args))


if __name__ == '__main__':
    name = sys.argv[1]
    if sys.argv[2] == '-e':
        code = sys.argv[3].replace('__ARGS__', json.dumps(dict(a.split('=', 1) for a in sys.argv[4:])))
    else:
        code = load(sys.argv[2], **dict(a.split('=', 1) for a in sys.argv[3:]))
    v = ev(name, code)
    print(json.dumps(v, indent=1, ensure_ascii=False) if not isinstance(v, str) else v)
