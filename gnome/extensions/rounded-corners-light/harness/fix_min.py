#!/usr/bin/env python3
"""Two test windows only, to keep a nested shell small: fix_min.py NAME
'files' (GTK4, Wayland) and 'cad-x11' (GTK3, X11), both floating 1500x950."""
import pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import nest_env, ev
SP = pathlib.Path(__file__).resolve().parent
name = sys.argv[1]
env = nest_env(name)
for kind, title in (('gtk4', 'files'), ('gtk3-x11', 'cad-x11')):
    e = dict(env)
    if kind == 'gtk3-x11':
        e.pop('WAYLAND_DISPLAY', None)
        e.update(GDK_BACKEND='x11', DISPLAY=env['NESTED_X11_DISPLAY'], XAUTHORITY=env['NESTED_XAUTHORITY'])
    else:
        e['GDK_BACKEND'] = 'wayland'; e.pop('DISPLAY', None)
    subprocess.Popen([sys.executable, str(SP / 'fixture.py'), kind, title, '1500', '950', f'@{name}'],
                     env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
for _ in range(100):
    if int(ev(name, "global.get_window_actors().filter(a => a.meta_window.get_window_type() === 0).length")) >= 2:
        break
    time.sleep(0.3)
time.sleep(1.5)
