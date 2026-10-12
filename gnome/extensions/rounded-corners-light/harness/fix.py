#!/usr/bin/env python3
"""Launch the standard window set into a private shell: fix.py NAME
9 windows: 4 maximized (2 of them X11), 4 floating, 1 redrawing continuously."""
import pathlib, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ev import nest_env, ev
SP = pathlib.Path(__file__).resolve().parent
SET = [('gtk4', 'browser', 2560, 1400), ('gtk4', 'editor', 2560, 1400), ('gtk3-x11', 'chat-x11', 1700, 1100),
       ('gtk4', 'files', 1500, 950), ('gtk4', 'terminal', 1200, 800), ('gtk3-x11', 'cad-x11', 2560, 1400),
       ('gtk4', 'notes', 1100, 760), ('gtk4-dynamic', 'video', 1280, 760), ('gtk4', 'settings', 1000, 700)]
MAXIMIZE = ['browser', 'editor', 'cad-x11', 'chat-x11']
name = sys.argv[1]
env = nest_env(name)
for kind, title, w, h in SET:
    e = dict(env)
    if kind == 'gtk3-x11':
        e.pop('WAYLAND_DISPLAY', None)
        e.update(GDK_BACKEND='x11', DISPLAY=env['NESTED_X11_DISPLAY'], XAUTHORITY=env['NESTED_XAUTHORITY'])
    else:
        e['GDK_BACKEND'] = 'wayland'; e.pop('DISPLAY', None)
    subprocess.Popen([sys.executable, str(SP / 'fixture.py'), kind, title, str(w), str(h), f'@{name}'],
                     env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(0.4)
for _ in range(100):
    if int(ev(name, "global.get_window_actors().filter(a => a.meta_window.get_window_type() === 0).length")) >= len(SET):
        break
    time.sleep(0.3)
time.sleep(1.5)
print(ev(name, """(() => { const max = %s; let i = 0;
  const wins = global.get_window_actors().map(a => a.meta_window).filter(w => w.get_window_type() === 0);
  for (const w of wins) { if (max.includes(w.get_title())) w.maximize(); else { w.move_frame(true, 120 + 180 * i, 90 + 90 * i); i++; } }
  return JSON.stringify(wins.map(w => w.get_title())); })()""" % str(MAXIMIZE).replace("'", '"')))
time.sleep(1.5)
