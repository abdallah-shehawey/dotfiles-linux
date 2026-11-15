#!/usr/bin/env python3
"""Put a Windows game (or the Controller Settings app) in the Steam library.

From the games/ folder of dotfiles-linux (based on add-game.py of the
Gaming-on-Linux package, plus --launcher and --wmclass for the per-game launchers).

    steam-shortcut.py add --name "eFootball PES 2021" \
        --launcher "/media/Games/eFootball-PES-2021/play-pes2021.sh" \
        --exe "/media/Games/eFootball-PES-2021/PES2021.exe" \
        [--wmclass pes2021.exe] [--cover F] [--wide F] [--hero F] [--logo F] [--icon F]
    steam-shortcut.py controller-settings     the Controller Settings app, with its pictures
    steam-shortcut.py remove --name "eFootball PES 2021"
    steam-shortcut.py list                    the shortcuts this tool added
    steam-shortcut.py check                   is Steam ready (installed, signed in)?

Each game becomes a "non-Steam game" whose target is $GAMES_DIR/common/steam-launch.sh
(GAMES_DIR defaults to /media/Games) and whose launch options are the game's own
launcher (--launcher). Without --launcher it falls back to "common/play.sh <exe>"
from the Gaming-on-Linux package. Steam's overlay and Steam Input are turned
off (the launchers give every game the same controller setup).
--exe is the game's real .exe: its lowercase name is the window class that gets
the dock icon; --wmclass overrides it when the window belongs to another exe.
Pictures: cover = the tall library picture (600x900), wide = the wide one
(920x430), hero = the banner on the game's page (1920x620), logo = the game's
name over the banner, icon = the small square one.
Steam must be closed: it rewrites these files when it exits.
"""
import json
import os
import re
import shutil
import struct
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
STEAM = os.path.expanduser('~/.local/share/Steam')
COMMON = os.path.expanduser(os.environ.get('GAMES_DIR', '/media/Games')) + '/common'
APPS = os.path.expanduser('~/.local/share/applications')
BACKUP = os.path.expanduser('~/.cache/wine-games/steam-backup-' + time.strftime('%Y%m%d-%H%M%S'))
TAG = 'Windows games'          # Steam collection the games go into
PAD_APP = (3501849340, 'Controller Settings')


# ---------- binary VDF (shortcuts.vdf) ----------
def bin_load(data):
    def read_map(i):
        out = {}
        while True:
            t = data[i]; i += 1
            if t == 8:
                return out, i
            j = data.index(b'\0', i); key = data[i:j].decode('utf-8', 'replace'); i = j + 1
            if t == 0:
                val, i = read_map(i)
            elif t == 1:
                j = data.index(b'\0', i); val = data[i:j].decode('utf-8', 'replace'); i = j + 1
            elif t == 2:
                val = ('i32', struct.unpack('<I', data[i:i + 4])[0]); i += 4
            elif t == 3:
                val = ('f32', struct.unpack('<f', data[i:i + 4])[0]); i += 4
            elif t == 7:
                val = ('u64', struct.unpack('<Q', data[i:i + 8])[0]); i += 8
            else:
                raise ValueError(f'unknown type {t} in shortcuts.vdf')
            out[key] = val
    if not data:
        return {'shortcuts': {}}
    out, _ = read_map(0)
    return out


def bin_dump(tree):
    out = bytearray()

    def write_map(m):
        for key, val in m.items():
            k = key.encode() + b'\0'
            if isinstance(val, dict):
                out.extend(b'\0' + k); write_map(val); out.append(8)
            elif isinstance(val, tuple):
                kind, num = val
                if kind == 'i32':
                    out.extend(b'\2' + k + struct.pack('<I', num & 0xFFFFFFFF))
                elif kind == 'f32':
                    out.extend(b'\3' + k + struct.pack('<f', num))
                else:
                    out.extend(b'\7' + k + struct.pack('<Q', num))
            else:
                out.extend(b'\1' + k + str(val).encode() + b'\0')
    write_map(tree)
    out.append(8)
    return bytes(out)


# ---------- text VDF (localconfig.vdf, loginusers.vdf) ----------
TOKEN = re.compile(r'\s*(?:(//[^\n]*)|"((?:[^"\\]|\\.)*)"|(\{)|(\})|(\[[^\]]*\]))', re.S)


def txt_load(text):
    pos, stack = 0, [[]]
    pending = None
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip():
                raise ValueError(f'cannot read VDF at {pos}')
            break
        pos = m.end()
        comment, string, opening, closing, cond = m.groups()
        if comment is not None or cond is not None:
            continue
        if string is not None:
            s = string.replace('\\"', '"').replace('\\\\', '\\')
            if pending is None:
                pending = s
            else:
                stack[-1].append([pending, s]); pending = None
        elif opening:
            node = []
            stack[-1].append([pending, node]); pending = None
            stack.append(node)
        elif closing:
            stack.pop()
    return stack[0]


def txt_dump(node, depth=0):
    out = []
    tab = '\t' * depth
    for key, val in node:
        k = key.replace('\\', '\\\\').replace('"', '\\"')
        if isinstance(val, list):
            out.append(f'{tab}"{k}"\n{tab}{{\n{txt_dump(val, depth + 1)}{tab}}}\n')
        else:
            v = val.replace('\\', '\\\\').replace('"', '\\"')
            out.append(f'{tab}"{k}"\t\t"{v}"\n')
    return ''.join(out)


def child(node, key, create=True):
    for k, v in node:
        if k.lower() == key.lower() and isinstance(v, list):
            return v
    if not create:
        return None
    new = []
    node.append([key, new])
    return new


def set_value(node, key, value):
    for item in node:
        if item[0].lower() == key.lower() and not isinstance(item[1], list):
            item[1] = value
            return
    node.append([key, value])


# ---------- Steam ----------
def steam_running():
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            with open(f'/proc/{pid}/comm') as f:
                comm = f.read().strip()
            if comm in ('steam', 'steamwebhelper'):
                return True
        except OSError:
            pass
    return False


def steam_user():
    """The account last signed in, as its userdata folder."""
    userdata = os.path.join(STEAM, 'userdata')
    try:
        with open(os.path.join(STEAM, 'config', 'loginusers.vdf'), encoding='utf-8', errors='replace') as f:
            users = child(txt_load(f.read()), 'users', create=False) or []
        recent = [k for k, v in users if isinstance(v, list)
                  and any(a.lower() == 'mostrecent' and b == '1' for a, b in v)]
        for sid in recent + [k for k, _ in users]:
            folder = os.path.join(userdata, str(int(sid) - 76561197960265728))
            if os.path.isfile(os.path.join(folder, 'config', 'localconfig.vdf')):
                return folder
    except (OSError, ValueError):
        pass
    folders = [os.path.join(userdata, d) for d in os.listdir(userdata) if d.isdigit() and d != '0'] \
        if os.path.isdir(userdata) else []
    folders = [d for d in folders if os.path.isfile(os.path.join(d, 'config', 'localconfig.vdf'))]
    return max(folders, key=lambda d: os.path.getmtime(os.path.join(d, 'config', 'localconfig.vdf'))) \
        if folders else None


def backup(path):
    if os.path.exists(path):
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy2(path, os.path.join(BACKUP, os.path.basename(path)))


def quoted(path):
    return '"' + path + '"'


def shortcut_id(exe, name):
    # what Steam itself computes for a non-Steam game
    return (zlib.crc32((exe + name).encode()) & 0xFFFFFFFF) | 0x80000000


class Library:
    def __init__(self):
        self.user = steam_user()
        if not self.user:
            raise SystemExit('STEAM-NOT-READY: open Steam once, sign in, then close it (Steam menu > Exit)')
        cfg = os.path.join(self.user, 'config')
        self.shortcuts_path = os.path.join(cfg, 'shortcuts.vdf')
        self.local_path = os.path.join(cfg, 'localconfig.vdf')
        self.grid = os.path.join(cfg, 'grid')
        try:
            with open(self.shortcuts_path, 'rb') as f:
                self.tree = bin_load(f.read())
        except FileNotFoundError:
            self.tree = {'shortcuts': {}}
        self.items = [v for v in self.tree.setdefault('shortcuts', {}).values() if isinstance(v, dict)]

    def find(self, name):
        return [v for v in self.items if v.get('AppName', '').lower() == name.lower()]

    def ours(self):
        return [v for v in self.items if TAG in v.get('tags', {}).values() or v.get('AppName') == PAD_APP[1]]

    def save(self, steam_input_off=()):
        if steam_running():
            raise SystemExit('STEAM-RUNNING: close Steam first (Steam menu > Exit)')
        backup(self.shortcuts_path)
        self.tree['shortcuts'] = {str(i): v for i, v in enumerate(self.items)}
        os.makedirs(os.path.dirname(self.shortcuts_path), exist_ok=True)
        with open(self.shortcuts_path + '.new', 'wb') as f:
            f.write(bin_dump(self.tree))
        os.replace(self.shortcuts_path + '.new', self.shortcuts_path)
        if steam_input_off:
            # Library > game > Properties > Controller > Disable Steam Input
            with open(self.local_path, encoding='utf-8', errors='surrogateescape') as f:
                local = txt_load(f.read())
            store = child(local, 'UserLocalConfigStore')
            # where Steam itself writes "Disable Steam Input" (seen 8 Nov 2026), and the older place
            for apps in (child(store, 'apps'),
                         child(child(child(child(store, 'Software'), 'Valve'), 'Steam'), 'apps')):
                for appid in steam_input_off:
                    set_value(child(apps, str(appid)), 'UseSteamControllerConfig', '0')
            backup(self.local_path)
            with open(self.local_path + '.new', 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(txt_dump(local))
            os.replace(self.local_path + '.new', self.local_path)


def put_art(lib, appid, pics):
    """pics: {kind: file}; Steam reads grid/<appid><suffix>.<png|jpg>."""
    os.makedirs(lib.grid, exist_ok=True)
    suffix = {'cover': 'p', 'wide': '', 'hero': '_hero', 'logo': '_logo'}
    for kind, src in pics.items():
        if kind not in suffix or not src:
            continue
        ext = os.path.splitext(src)[1].lower()
        ext = ext if ext in ('.png', '.jpg', '.jpeg') else '.png'
        for old in ('.png', '.jpg', '.jpeg'):
            p = os.path.join(lib.grid, f'{appid}{suffix[kind]}{old}')
            if os.path.exists(p):
                os.remove(p)
        shutil.copy2(src, os.path.join(lib.grid, f'{appid}{suffix[kind]}{ext}'))


def dock_entry(appid, name, icon, wmclass):
    """A hidden menu entry that only gives the game's window its icon in the dock."""
    os.makedirs(APPS, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or str(appid)
    with open(os.path.join(APPS, f'steam-game-{slug}.desktop'), 'w') as f:
        f.write('[Desktop Entry]\nType=Application\n'
                f'Name={name}\nComment=Started from Steam; this entry only gives the window its dock icon\n'
                f'Icon={icon or "input-gaming"}\nExec=steam steam://rungameid/{(appid << 32) | 0x02000000}\n'
                f'StartupWMClass={wmclass}\nStartupNotify=false\nNoDisplay=true\n')
    return slug


def entry(appid, name, launch, icon, tags):
    return {
        'appid': ('i32', appid), 'AppName': name,
        'Exe': quoted(os.path.join(COMMON, 'steam-launch.sh')),
        'StartDir': quoted(COMMON + '/'), 'icon': icon or '', 'ShortcutPath': '',
        'LaunchOptions': launch,
        'IsHidden': ('i32', 0), 'AllowDesktopConfig': ('i32', 0), 'AllowOverlay': ('i32', 0),
        'OpenVR': ('i32', 0), 'Devkit': ('i32', 0), 'DevkitGameID': '',
        'DevkitOverrideAppID': ('i32', 0), 'LastPlayTime': ('i32', 0), 'FlatpakAppID': '',
        'sortas': '', 'tags': tags,
    }


def keep_icon(appid, src):
    if not src:
        return ''
    folder = os.path.join(COMMON, 'icons')
    os.makedirs(folder, exist_ok=True)
    dst = os.path.join(folder, f'{appid}{os.path.splitext(src)[1].lower() or ".png"}')
    shutil.copy2(src, dst)
    return dst


def arg(args, name):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else None
    return None


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ''
    if cmd == 'check':
        user = steam_user()
        print(f'STEAM-READY {user}' if user else 'STEAM-NOT-READY')
        return 0 if user else 3
    if cmd not in ('add', 'remove', 'list', 'controller-settings'):
        print(__doc__)
        return 2
    lib = Library()

    if cmd == 'list':
        for v in lib.ours():
            print(f"{v['appid'][1]}\t{v.get('AppName')}\t{v.get('LaunchOptions')}")
        return 0

    if cmd == 'remove':
        name = arg(args, '--name') or ''
        gone = [v for v in lib.find(name) if v in lib.ours()]
        if not gone:
            print(f'NOT-FOUND {name}')
            return 1
        lib.items = [v for v in lib.items if v not in gone]
        lib.save()
        print(f'REMOVED {name}')
        return 0

    if cmd == 'controller-settings':
        appid, name = PAD_APP
        icon = os.path.join(HERE, 'icons', 'local.games.PadSettings.png')
        lib.items = [v for v in lib.items if v.get('AppName') != name]
        lib.items.append(entry(appid, name, quoted(os.path.join(COMMON, 'controller-settings.sh')),
                               keep_icon(appid, icon), {}))
        put_art(lib, appid, {k: os.path.join(HERE, 'art', f'{appid}{s}.png')
                             for k, s in (('cover', 'p'), ('wide', ''), ('hero', '_hero'), ('logo', '_logo'))})
        lib.save(steam_input_off=[appid])
        dock_entry(appid, name, 'local.games.PadSettings', 'local.games.PadSettings')
        icons = os.path.expanduser('~/.local/share/icons/hicolor/256x256/apps')
        os.makedirs(icons, exist_ok=True)
        shutil.copy2(icon, os.path.join(icons, 'local.games.PadSettings.png'))
        print(f'ADDED {name}')
        return 0

    # add
    name, exe = arg(args, '--name'), arg(args, '--exe')
    if not name or not exe or not os.path.isfile(exe):
        print(f'NO-EXE {exe}')
        return 2
    exe = os.path.abspath(exe)
    if not exe.lower().endswith('.exe'):
        print(f'NOT-EXE {exe}')
        return 2
    pics = {k: arg(args, '--' + k) for k in ('cover', 'wide', 'hero', 'logo', 'icon')}
    for k, p in pics.items():
        if p and not os.path.isfile(p):
            print(f'NO-PICTURE {k} {p}')
            return 2
    game_launcher = arg(args, '--launcher')
    if game_launcher:
        game_launcher = os.path.abspath(game_launcher)
        if not os.access(game_launcher, os.X_OK):
            print(f'LAUNCHER-NOT-EXECUTABLE {game_launcher}')
            return 2
        launch = quoted(game_launcher)
    else:
        launch = f'{quoted(os.path.join(COMMON, "play.sh"))} {quoted(exe)}'
    launcher = quoted(os.path.join(COMMON, 'steam-launch.sh'))
    appid = shortcut_id(launcher, name)
    old = lib.find(name)
    lib.items = [v for v in lib.items if v not in old]
    lib.items.append(entry(appid, name, launch, keep_icon(appid, pics['icon']), {'0': TAG}))
    put_art(lib, appid, pics)
    lib.save(steam_input_off=[appid])
    dock_entry(appid, name, os.path.join(COMMON, 'icons', f'{appid}{os.path.splitext(pics["icon"] or "")[1].lower()}')
               if pics['icon'] else None, (arg(args, '--wmclass') or os.path.basename(exe)).lower())
    print(f'ADDED {name} ({appid})')
    print(json.dumps({'steam_user_folder': lib.user, 'backup': BACKUP}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
