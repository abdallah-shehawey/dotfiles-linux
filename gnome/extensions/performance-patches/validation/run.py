import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
VARIANT = sys.argv[1]
SOURCE = BASE / VARIANT
ROOT = BASE / ('session-' + VARIANT)
UUIDS = [
    'tiling-assistant@leleat-on-github', 'runcat@kolesnikov.se',
    'blur-my-shell@aunetx', 'clipboard-indicator@tudmotu.com',
    'CoverflowAltTab@palatis.blogspot.com', 'dash-to-panel@jderose9.github.com',
    'chakra-switch@narkagni', 'just-perfection-desktop@just-perfection',
    'unlockDialogBackground@sun.wxg@gmail.com', 'Vitals@CoreCoding.com',
    'system-monitor@gnome-shell-extensions.gcampax.github.com', 'app-grid-tuner@m-lab',
    'rounded-corners-light@local', 'touchpad-gesture-customization@coooolapps.com',
    'gnome-fuzzy-app-search@gnome-shell-extensions.Czarlie.gitlab.com',
    'status-area-horizontal-spacing@mathematical.coffee.gmail.com',
    'appindicatorsupport@rgcjonas.gmail.com', 'background-logo@fedorahosted.org',
]
if VARIANT == 'none':
    UUIDS = []
env = os.environ.copy()
if '--private' not in sys.argv:
    settings = {}
    for uuid in UUIDS:
        # Do not snapshot clipboard history or connected-device identities.
        if uuid == 'clipboard-indicator@tudmotu.com':
            continue
        for schema in (SOURCE / uuid / 'schemas').glob('*.xml'):
            for element in ET.parse(schema).getroot().iter('schema'):
                path = element.get('path')
                if path:
                    settings[path] = subprocess.check_output(['dconf', 'dump', path])
    for path in ['/org/gnome/desktop/app-folders/', '/org/gnome/desktop/background/']:
        settings[path] = subprocess.check_output(['dconf', 'dump', path])
    snapshot = {k: v.decode() for k, v in settings.items()}
    # Native animation timing is a separate behavior fix, not a speedup metric.
    if '/org/gnome/shell/extensions/just-perfection/' in snapshot:
        import re
        key = '/org/gnome/shell/extensions/just-perfection/'
        snapshot[key] = re.sub(r'^animation=.*$', 'animation=1', snapshot[key], flags=re.M)
    (BASE / ('settings-' + VARIANT + '.json')).write_text(json.dumps(snapshot, indent=2))
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'GSETTINGS_BACKEND', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    for key, name in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                      ('XDG_CACHE_HOME', 'cache'), ('XDG_RUNTIME_DIR', 'runtime')]:
        path = ROOT / name
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)
        env[key] = str(path)
    env.update(XDG_SESSION_TYPE='wayland', XDG_CURRENT_DESKTOP='GNOME', XDG_SESSION_CLASS='user')
    env['GNOME_PERF_ROOT'] = str(BASE)
    env['GNOME_PERF_VARIANT'] = VARIANT
    sys.exit(subprocess.run(['dbus-run-session', '--', sys.executable, __file__, VARIANT, '--private'], env=env).returncode)

target = ROOT / 'data/gnome-shell/extensions'
target.mkdir(parents=True, exist_ok=True)
for uuid in UUIDS:
    shutil.copytree(SOURCE / uuid, target / uuid, dirs_exist_ok=True)
driver = target / 'performance-test@local'
driver.mkdir(exist_ok=True)
(driver / 'metadata.json').write_text(json.dumps({'uuid': driver.name, 'name': 'Private performance test',
    'description': 'Isolated test only', 'shell-version': ['50']}))
shutil.copy2(BASE / 'driver.js', driver / 'extension.js')
for path, content in json.loads((BASE / ('settings-' + VARIANT + '.json')).read_text()).items():
    subprocess.run(['dconf', 'load', path], input=content.encode(), env=env, check=True)
subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', repr(UUIDS + [driver.name])], env=env, check=True)
subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'welcome-dialog-last-shown-version', "'50.5'"], env=env, check=True)
with (ROOT / 'shell.log').open('w') as log:
    shell = subprocess.Popen(['gnome-shell', '--headless', '--virtual-monitor=2560x1440@165',
        '--wayland-display=gnome-performance-test', '--debug-control', '--force-animations'],
        env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(150):
            check = subprocess.run(['gdbus', 'introspect', '--session', '--dest', 'org.gnome.Mutter.DebugControl',
                '--object-path', '/org/gnome/Mutter/DebugControl'], env=env, capture_output=True)
            if check.returncode == 0:
                break
            if shell.poll() is not None:
                raise RuntimeError('Private compositor exited')
            time.sleep(.1)
        else:
            raise RuntimeError('Private compositor startup timed out')
        time.sleep(4)
        script = (BASE / 'tests.js').read_text()
        result = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell',
            '--object-path', '/org/gnome/Shell', '--method', 'org.gnome.Shell.Eval', '--timeout', '120', script],
            env=env, capture_output=True, text=True, timeout=125)
        (BASE / (VARIANT + '-eval.txt')).write_text(result.stdout + result.stderr)
        print(result.stdout[:7000], result.stderr, flush=True)
        if result.returncode or result.stdout.startswith('(false,'):
            raise RuntimeError('Private tests failed')
    finally:
        shell.terminate()
        try:
            shell.wait(timeout=8)
        except subprocess.TimeoutExpired:
            shell.kill()
            shell.wait()
