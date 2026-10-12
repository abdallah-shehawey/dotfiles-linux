#!/usr/bin/env python3
"""Private headless GNOME Shell with the owner's extensions and settings.

usage:
  nest.py start NAME EXTS [WxH@R]   EXTS: all | none | a,b,c | all-minus:a,b
  nest.py stop NAME
env NEST_EXT_OVERRIDE='uuid=/src/dir,...' replaces an extension's source.
gnome-shell runs in its own systemd user scope (nest-NAME.scope)."""
import os, pathlib, shutil, subprocess, sys, time, signal

SP = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path.home()
USER_EXT = HOME / '.local/share/gnome-shell/extensions'
OWNER = [
    'tiling-assistant@leleat-on-github', 'runcat@kolesnikov.se', 'blur-my-shell@aunetx',
    'clipboard-indicator@tudmotu.com', 'dash-to-panel@jderose9.github.com',
    'chakra-switch@narkagni', 'just-perfection-desktop@just-perfection',
    'unlockDialogBackground@sun.wxg@gmail.com', 'Vitals@CoreCoding.com',
    'system-monitor@gnome-shell-extensions.gcampax.github.com', 'app-grid-tuner@m-lab',
    'rounded-corners-light@local', 'touchpad-gesture-customization@coooolapps.com',
    'gnome-fuzzy-app-search@gnome-shell-extensions.Czarlie.gitlab.com',
    'status-area-horizontal-spacing@mathematical.coffee.gmail.com',
    'appindicatorsupport@rgcjonas.gmail.com', 'background-logo@fedorahosted.org',
]
PROBE = 'zz-probe@local'
PROBE_JS = """import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
export default class Probe extends Extension {
    enable() {
        global.context.unsafe_mode = true;
        const hide = () => Main.overview.hide();
        if (Main.layoutManager._startingUp)
            Main.layoutManager.connect('startup-complete', hide);
        else
            hide();
    }
    disable() {}
}
"""


def resolve(spec):
    if spec == 'all':
        return list(OWNER)
    if spec == 'none':
        return []
    if spec.startswith('all-minus:'):
        drop = spec.split(':', 1)[1].split(',')
        return [e for e in OWNER if e not in drop]
    return spec.split(',')


def start(name, spec, mode):
    root = SP / f'nest-{name}'
    stop(name, quiet=True)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir()
    env = os.environ.copy()
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'GSETTINGS_BACKEND', 'DBUS_SESSION_BUS_ADDRESS', 'XAUTHORITY'):
        env.pop(key, None)
    for key, sub in (('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache')):
        p = root / sub
        p.mkdir()
        p.chmod(0o700)
        env[key] = str(p)
    rt = pathlib.Path(f'/tmp/claude-1000/n-{name}')
    shutil.rmtree(rt, ignore_errors=True)
    rt.mkdir(mode=0o700)
    env['XDG_RUNTIME_DIR'] = str(rt)
    env.update(XDG_SESSION_TYPE='wayland', XDG_CURRENT_DESKTOP='GNOME', XDG_SESSION_CLASS='user')
    exts = resolve(spec)
    over = dict(x.split('=', 1) for x in os.environ.get('NEST_EXT_OVERRIDE', '').split(',') if x)
    ext_dir = root / 'data/gnome-shell/extensions'
    ext_dir.mkdir(parents=True)
    for e in exts:
        src = pathlib.Path(over[e]) if e in over else USER_EXT / e
        if src.exists():
            shutil.copytree(src, ext_dir / e, symlinks=True)
    (ext_dir / PROBE).mkdir()
    (ext_dir / PROBE / 'extension.js').write_text(PROBE_JS)
    (ext_dir / PROBE / 'metadata.json').write_text(
        '{"uuid": "%s", "name": "probe", "description": "test", "shell-version": ["50"]}' % PROBE)
    (root / 'exts.txt').write_text('\n'.join(exts) + '\n')
    log = open(root / 'runner.log', 'w')
    subprocess.Popen(['dbus-run-session', '--', sys.executable, '-I', __file__, '--private', name, mode],
                     env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(600):
        if (root / 'env.sh').exists():
            print((root / 'env.sh').read_text().strip())
            return
        time.sleep(0.1)
    raise SystemExit('no env.sh; see ' + str(root / 'runner.log'))


def private(name, mode):
    root = SP / f'nest-{name}'
    env = os.environ.copy()
    exts = [e for e in (root / 'exts.txt').read_text().split() if e]

    def gs(*a):
        subprocess.run(['gsettings', 'set', *a], env=env, check=True)

    for path, f in (('/org/gnome/shell/', 'shell'), ('/org/gnome/desktop/interface/', 'interface'),
                    ('/org/gnome/desktop/background/', 'background'), ('/org/gnome/desktop/wm/', 'wm'),
                    ('/org/gnome/mutter/', 'mutter'), ('/org/gnome/desktop/peripherals/', 'peripherals')):
        subprocess.run(['dconf', 'load', path], input=(SP / 'dconf' / f'{f}.dconf').read_bytes(),
                       env=env, check=True)
    gs('org.gnome.shell', 'enabled-extensions', str(exts + [PROBE]))
    gs('org.gnome.shell', 'disable-user-extensions', 'false')
    gs('org.gnome.shell', 'welcome-dialog-last-shown-version', "'50.5'")
    gs('org.gnome.desktop.interface', 'enable-animations', 'true')
    gs('org.gnome.desktop.session', 'idle-delay', 'uint32 0')
    gs('org.gnome.desktop.screensaver', 'lock-enabled', 'false')
    gs('org.gnome.desktop.notifications', 'show-banners', 'false')
    if os.environ.get('NEST_WALLPAPER'):
        for k in ('picture-uri', 'picture-uri-dark'):
            gs('org.gnome.desktop.background', k, "'file://%s'" % os.environ['NEST_WALLPAPER'])
    disp = f'n-{name}'
    shell_env = {k: env[k] for k in ('XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS', 'XDG_CONFIG_HOME',
                                     'XDG_DATA_HOME', 'XDG_CACHE_HOME')}
    cmd = ['env', 'XDG_RUNTIME_DIR=/run/user/%d' % os.getuid(),
           'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%d/bus' % os.getuid(),
           'systemd-run', '--user', '--scope', '--quiet', '--collect', f'--unit=nest-{name}',
           '-p', 'MemoryAccounting=yes', '--',
           'env'] + [f'{k}={v}' for k, v in shell_env.items()] + [
           e for e in os.environ.get('NEST_SHELL_ENV', '').split() if e] + [
           'gnome-shell', '--headless', f'--virtual-monitor={mode}', f'--wayland-display={disp}',
           '--force-animations']
    log = open(root / 'shell.log', 'w')
    shell = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(300):
        r = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.gnome.Shell', '--object-path',
                            '/org/gnome/Shell', '--method', 'org.gnome.Shell.Eval', '1'],
                           env=env, capture_output=True, text=True)
        if r.stdout.startswith('(true'):
            break
        if shell.poll() is not None:
            raise SystemExit('shell exited')
        time.sleep(0.2)
    else:
        raise SystemExit('Eval never came up')
    time.sleep(2)
    xdisp = ''
    for line in (root / 'shell.log').read_text().splitlines():
        if 'Using public X11 display' in line:
            xdisp = line.split('display ')[1].split(',')[0]
    pid = shell.pid
    cg = pathlib.Path('/sys/fs/cgroup') / open(f'/proc/{pid}/cgroup').read().strip().split('::')[1].lstrip('/')
    xa = next(iter(sorted(pathlib.Path(env['XDG_RUNTIME_DIR']).glob('.mutter-Xwaylandauth.*'))), '')
    (root / 'env.sh').write_text(
        f"export DBUS_SESSION_BUS_ADDRESS='{env['DBUS_SESSION_BUS_ADDRESS']}'\n"
        f"export XDG_RUNTIME_DIR='{env['XDG_RUNTIME_DIR']}'\n"
        f"export XDG_CONFIG_HOME='{env['XDG_CONFIG_HOME']}'\n"
        f"export XDG_DATA_HOME='{env['XDG_DATA_HOME']}'\n"
        f"export XDG_CACHE_HOME='{env['XDG_CACHE_HOME']}'\n"
        f"export WAYLAND_DISPLAY='{disp}'\nexport NESTED_X11_DISPLAY='{xdisp}'\n"
        f"export NESTED_XAUTHORITY='{xa}'\nexport SHELL_PID={pid}\nexport SHELL_CGROUP='{cg}'\n")
    try:
        while not (root / 'stop').exists() and shell.poll() is None:
            time.sleep(0.3)
    finally:
        (root / 'stop').unlink(missing_ok=True)
        try:
            os.killpg(shell.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            shell.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(shell.pid, signal.SIGKILL)
        (root / 'env.sh').unlink(missing_ok=True)


def stop(name, quiet=False):
    root = SP / f'nest-{name}'
    if not (root / 'env.sh').exists():
        if not quiet:
            print('not running')
        return
    pid = None
    for line in (root / 'env.sh').read_text().splitlines():
        if line.startswith('export SHELL_PID='):
            pid = int(line.split('=')[1])
    subprocess.run(['pkill', '-f', f'[f]ixture.py .*@{name}$'])
    (root / 'stop').touch()
    for _ in range(80):
        if not (root / 'env.sh').exists():
            break
        time.sleep(0.25)
    try:
        os.kill(pid, 0)
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, TypeError):
        pass
    if not quiet:
        print('stopped', name)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == '--private':
        private(a[1], a[2])
    elif a[0] == 'start':
        start(a[1], a[2], a[3] if len(a) > 3 else '2560x1440@165')
    elif a[0] == 'stop':
        stop(a[1])
