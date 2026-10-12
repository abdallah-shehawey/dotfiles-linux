#!/usr/bin/env python3
"""Private headless GNOME Shell for extension experiments.

usage: run.py <ext-src-dir> [WxH@Hz] [extra enabled uuids...]
Writes env.sh (bus/display) next to this file; stops when ./stop exists.
"""
import os, pathlib, shutil, subprocess, sys, time

base = pathlib.Path(__file__).resolve().parent
root = base / 'session'
if '--private' not in sys.argv:
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'GSETTINGS_BACKEND', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    for key, name in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                      ('XDG_CACHE_HOME', 'cache')]:
        p = root / name; p.mkdir(); p.chmod(0o700); env[key] = str(p)
    # Wayland socket paths are limited to 108 bytes; keep the runtime dir short.
    rt = pathlib.Path('/tmp/claude-1000/rcrt')
    shutil.rmtree(rt, ignore_errors=True); rt.mkdir(mode=0o700); env['XDG_RUNTIME_DIR'] = str(rt)
    env.update(XDG_SESSION_TYPE='wayland', XDG_CURRENT_DESKTOP='GNOME', XDG_SESSION_CLASS='user')
    sys.exit(subprocess.run(['dbus-run-session', '--', sys.executable, __file__, '--private'] + sys.argv[1:], env=env).returncode)

args = [a for a in sys.argv[1:] if a != '--private']
src = pathlib.Path(args[0])
mode = args[1] if len(args) > 1 else '2560x1440@165'
extra = args[2:]
env = os.environ.copy()
uuid = 'rounded-corners-light@local'
target = root / 'data/gnome-shell/extensions' / uuid
target.mkdir(parents=True)
for f in src.iterdir():
    if f.is_file():
        shutil.copy2(f, target / f.name)
# Test-only wrapper: unsafe mode on the private bus so Eval works.
shutil.move(target / 'extension.js', target / 'implementation.js')
(target / 'extension.js').write_text(
    "import Implementation from './implementation.js';\n"
    "export default class TestExtension extends Implementation {\n"
    "    enable() { global.context.unsafe_mode = true; super.enable(); }\n"
    "}\n")
for e in extra:
    shutil.copytree(pathlib.Path.home() / '.local/share/gnome-shell/extensions' / e,
                    root / 'data/gnome-shell/extensions' / e, symlinks=True)
uuids = [uuid] + extra
def gs(*a):
    subprocess.run(['gsettings', 'set', *a], env=env, check=True)
gs('org.gnome.shell', 'enabled-extensions', str(uuids))
gs('org.gnome.shell', 'welcome-dialog-last-shown-version', "'50.5'")
gs('org.gnome.desktop.interface', 'enable-animations', 'true')
gs('org.gnome.desktop.background', 'picture-uri', "''")
gs('org.gnome.desktop.background', 'picture-uri-dark', "''")
gs('org.gnome.desktop.background', 'primary-color', "'#c8d0d8'")
gs('org.gnome.desktop.background', 'color-shading-type', "'solid'")
gs('org.gnome.mutter', 'center-new-windows', 'true')
bms = base / 'bms.dconf'
if 'blur-my-shell@aunetx' in extra and bms.exists():
    subprocess.run(['dconf', 'load', '/org/gnome/shell/extensions/blur-my-shell/'],
                   input=bms.read_bytes(), env=env, check=True)
log = open(root / 'shell.log', 'w')
shell = subprocess.Popen(['gnome-shell', '--headless', f'--virtual-monitor={mode}',
                          '--wayland-display=rc-test', '--debug-control', '--force-animations'],
                         env=env, stdout=log, stderr=subprocess.STDOUT)
for _ in range(200):
    if subprocess.run(['gdbus', 'introspect', '--session', '--dest', 'org.gnome.Shell',
                       '--object-path', '/org/gnome/Shell'], env=env, capture_output=True).returncode == 0:
        break
    if shell.poll() is not None:
        raise SystemExit('shell exited')
    time.sleep(0.1)
time.sleep(2)
xdisp = ''
for line in (root / 'shell.log').read_text().splitlines():
    if 'Using public X11 display' in line:
        xdisp = line.split('display ')[1].split(',')[0]
(base / 'env.sh').write_text(
    f"export DBUS_SESSION_BUS_ADDRESS='{env['DBUS_SESSION_BUS_ADDRESS']}'\n"
    f"export XDG_RUNTIME_DIR='{env['XDG_RUNTIME_DIR']}'\n"
    f"export XDG_CONFIG_HOME='{env['XDG_CONFIG_HOME']}'\n"
    f"export XDG_DATA_HOME='{env['XDG_DATA_HOME']}'\n"
    f"export XDG_CACHE_HOME='{env['XDG_CACHE_HOME']}'\n"
    f"export WAYLAND_DISPLAY=rc-test\nexport NESTED_X11_DISPLAY='{xdisp}'\nexport SHELL_PID={shell.pid}\n")
print('READY', shell.pid, xdisp, flush=True)
try:
    while not (base / 'stop').exists() and shell.poll() is None:
        time.sleep(0.3)
finally:
    (base / 'stop').unlink(missing_ok=True)
    shell.terminate()
    try: shell.wait(timeout=8)
    except subprocess.TimeoutExpired: shell.kill()
    (base / 'env.sh').unlink(missing_ok=True)
