#!/usr/bin/env python3
"""leak3.py NAME KIND N : is memory after N actions held by JS (needs a GC) or by Mesa's
buffer cache (released by any later buffer free)? Sequence: actions, wait 6 s,
one tiny resize (frees a buffer in C), wait 2 s, then a GC."""
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import ev, load, nest_env
from ovbench import gem
SP = pathlib.Path(__file__).resolve().parent
name, kind, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
pid = int(nest_env(name)['SHELL_PID'])
g = lambda: gem(pid)['total']
NUDGE = """(async () => { const {GLib} = imports.gi; const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
  const w = global.get_window_actors().map(a => a.meta_window).find(w => w.get_title() === 'settings');
  const r = w.get_frame_rect(); w.move_resize_frame(true, r.x, r.y, r.width - 7, r.height); await wait(150);
  w.move_resize_frame(true, r.x, r.y, r.width, r.height); await wait(150); return 'ok'; })()"""
ev(name, load(SP / 'gc.js')); time.sleep(3)
t = [('start', g())]
ev(name, load(SP / 'actions.js', kind=kind, n=n)); t.append(('after', g()))
time.sleep(6); t.append(('+6s', g()))
ev(name, NUDGE); time.sleep(2); t.append(('Cfree', g()))
ev(name, load(SP / 'gc.js')); time.sleep(2); t.append(('GC', g()))
print(f"{name} {kind} x{n}: " + '  '.join(f'{k}={v}' for k, v in t) +
      f" | Mesa cache {t[2][1] - t[3][1]} MB, JS-held {t[3][1] - t[4][1]} MB, kept {t[4][1] - t[0][1]:+d}", flush=True)
