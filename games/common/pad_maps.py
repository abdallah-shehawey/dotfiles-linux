#!/usr/bin/env python3
# Builds the pad map for the game launchers and prints it as shell exports
# (pads.sh evals the output). Every connected pad ends up as a gamepad, so Wine
# gives it to the game as an XInput pad with sticks, d-pad and all buttons.
# pad-settings.py uses the same file as a module.
#
# Where each pad's map comes from, later ones win:
#   1. SDL's own list (most branded pads, Twin USB included)
#   2. Steam's list and pads set up in Steam's controller settings
#   3. the Twin USB map below
#   4. PlayStation-style guesses for pads none of these know, kept in
#      ~/.config/game-pads/auto-mappings.txt once a pad has been seen
#   5. pads set in Controller Settings (~/.config/game-pads/mappings.txt)
# Maps follow the pad's type, never its USB port or plug order, and stay on
# disk, so a pad keeps its buttons when it is unplugged and plugged back in
# (also during a game), moved to another port, swapped for another pad and
# back, or used after a reboot. Every game gets the same map.
#
# Player order is plug-in order (oldest first, a broken pad last) unless the
# player strip in Controller Settings set another one. That one is kept in
# ~/.config/game-pads/player-order.json by the socket each pad is in (USB port,
# or Bluetooth address, and its port on the adapter), so it holds after a
# replug or a reboot; an adapter moved to another USB port keeps its place too.
#
# Usage: pad_maps.py                     shell exports for the launchers
#        pad_maps.py --json [--default]  each connected pad's map, as JSON;
#                                        --default leaves out the saved ones
import ctypes
import json
import os
import re
import shlex
import sys

CONFIG_DIR = os.path.expanduser('~/.config/game-pads')
LEARNED = os.path.join(CONFIG_DIR, 'mappings.txt')
AUTO = os.path.join(CONFIG_DIR, 'auto-mappings.txt')
# The guesses and saved maps together, for every SDL program in the session
# (Steam, Proton and native games, Lutris, Heroic) through environment.d
SESSION_DB = os.path.join(CONFIG_DIR, 'gamecontrollerdb.txt')
ENVIRONMENT_D = os.path.expanduser('~/.config/environment.d/60-game-pads.conf')
PLAYER_ORDER = os.path.join(CONFIG_DIR, 'player-order.json')
STEAM_CONFIG = os.path.expanduser('~/.local/share/Steam/config/config.vdf')

# Twin USB PS2 adapter (0810:0001), both ports. b4/b5 are L2/R2 and b6/b7 are
# L1/R1. With the ANALOG light off the pad sends the d-pad and the left stick
# both as a0/a1 and the right stick as the face buttons, as it does on a
# PlayStation; with the light on the d-pad is the hat and both sticks are analog.
TWIN_USB = ('a:b2,b:b1,x:b3,y:b0,back:b8,start:b9,leftshoulder:b6,lefttrigger:b4,'
            'rightshoulder:b7,righttrigger:b5,leftstick:b10,rightstick:b11,'
            'leftx:a0,lefty:a1,rightx:a3,righty:a2,'
            'dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,platform:Linux,')
BUILT_IN = [f'{guid},Twin USB PS2 Adapter,{TWIN_USB}'
            for guid in ('03004a9f100800000100000010010000',
                         '03000000100800000100000010010000')]


def log(msg):
    print(f'pad-maps: {msg}', file=sys.stderr)


def mapping_lines(text):
    return [line.strip() for line in (text or '').splitlines()
            if re.match(r'^[0-9a-fA-F]{32},[^,]*,', line.strip())]


def steam_binds():
    try:
        with open(STEAM_CONFIG, encoding='utf-8', errors='replace') as f:
            m = re.search(r'"SDL_GamepadBind"\s+"([^"]*)"', f.read())
        return mapping_lines(m.group(1)) if m else []
    except OSError:
        return []


def read_lines(path):
    try:
        with open(path, encoding='utf-8') as f:
            return mapping_lines(f.read())
    except OSError:
        return []


def learned():
    return read_lines(LEARNED)


def base_mappings(with_learned=True):
    return (mapping_lines(os.environ.get('STEAM_PAD_MAPPINGS')) + steam_binds()
            + BUILT_IN + read_lines(AUTO) + (learned() if with_learned else []))


def write_file(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + ('\n' if lines else ''))
    os.replace(tmp, path)


def remember_guess(mapping):
    """Keep a guessed map, so the pad gets the same one when it comes back."""
    guid = mapping[:32].lower()
    lines = read_lines(AUTO)
    if any(line[:32].lower() == guid for line in lines):
        return
    write_file(AUTO, lines + [mapping])
    write_session_db()


def write_session_db():
    write_file(SESSION_DB, read_lines(AUTO) + learned())
    ensure_session_env()


def without_crc(guid):
    # SDL before 2.26 and SDL3 lines meant for any name keep bytes 2-3 zero
    return guid[:4] + '0000' + guid[8:]


def save_learned(guid, name, fields):
    """Store fields ({output: input}) as this pad type's map."""
    body = ','.join(f'{k}:{v}' for k, v in fields.items())
    name = name.replace(',', ' ')
    guids = {guid, without_crc(guid)}
    keep = [line for line in learned() if line[:32].lower() not in guids]
    new = [f'{g},{name},{body},platform:Linux,' for g in sorted(guids, reverse=True)]
    write_file(LEARNED, keep + new)
    write_session_db()


def remove_learned(guid):
    guids = {guid, without_crc(guid)}
    write_file(LEARNED, [line for line in learned() if line[:32].lower() not in guids])
    write_session_db()


def ensure_session_env():
    line = f'SDL_GAMECONTROLLERCONFIG_FILE={SESSION_DB}\n'
    try:
        with open(ENVIRONMENT_D, encoding='utf-8') as f:
            if f.read() == line:
                return
    except OSError:
        pass
    os.makedirs(os.path.dirname(ENVIRONMENT_D), exist_ok=True)
    with open(ENVIRONMENT_D, 'w', encoding='utf-8') as f:
        f.write(line)


def held_buttons(node):
    """Buttons down on an evdev node right now (EVIOCGKEY)."""
    import array
    import fcntl
    keys = array.array('B', bytes(96))
    try:
        fd = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
        try:
            fcntl.ioctl(fd, 0x80604518, keys)
        finally:
            os.close(fd)
    except OSError:
        return []
    return [i for i in range(768) if keys[i // 8] >> (i % 8) & 1]


def udev_properties(node):
    try:
        minor = os.minor(os.stat(node).st_rdev)
        with open(f'/run/udev/data/c13:{minor}') as f:
            return dict(line[2:].split('=', 1) for line in f.read().split('\n')
                        if line.startswith('E:') and '=' in line)
    except OSError:
        return {}


def plug_order():
    """Every evdev node udev tags as a joystick, oldest first, and last any
    port that holds two or more buttons on its own (a broken pad on an adapter
    does that), so it never takes a real pad's slot."""
    nodes = [f'/dev/input/{name}' for name in os.listdir('/dev/input')
             if name.startswith('event')
             and udev_properties(f'/dev/input/{name}').get('ID_INPUT_JOYSTICK') == '1']
    nodes.sort(key=lambda n: int(n.rsplit('event', 1)[1]))
    stuck = [n for n in nodes if len(held_buttons(n)) >= 2]
    for n in stuck:
        log(f'{n} holds {held_buttons(n)} by itself, moved to the last slot')
    return [n for n in nodes if n not in stuck] + stuck


def _read(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    except OSError:
        return ''


def node_identity(node):
    """What finds a pad again after a replug or a reboot, as a dict:
    port   the socket it is in: Bluetooth address or USB path, plus its place on
           the adapter (the Twin USB adapter is one USB device with an input
           per pad port)
    model  vendor:product plus that place, for an adapter moved to another port
    socket and sub, for the app to tell pads of one model apart"""
    dev = os.path.realpath(f'/sys/class/input/{os.path.basename(node)}/device')
    parent = os.path.dirname(dev)
    sub = 0
    if (os.path.basename(parent) == 'input'
            and os.path.basename(os.path.dirname(parent)) != 'virtual'):
        siblings = sorted((d for d in os.listdir(parent) if re.fullmatch(r'input\d+', d)),
                          key=lambda d: int(d[5:]))
        sub = siblings.index(os.path.basename(dev)) if os.path.basename(dev) in siblings else 0
    uniq, phys = _read(dev + '/uniq'), _read(dev + '/phys')
    bus = _read(dev + '/id/bustype')
    vid, pid = node_ids(node)
    where = uniq or udev_properties(node).get('ID_PATH') or phys or _read(dev + '/name')
    m = re.match(r'usb-[^-/]+-([\d.]+)', phys)
    if bus == '0005':
        socket = 'Bluetooth'
    elif m:
        socket = f'USB {m.group(1)}'
    elif bus == '0006' or dev.startswith('/sys/devices/virtual/'):
        socket = 'Virtual'
    else:
        socket = phys or 'Other'
    return {'port': f'{where}#{sub}', 'model': f'{vid:04x}:{pid:04x}#{sub}',
            'socket': socket, 'sub': sub}


def load_player_order():
    try:
        with open(PLAYER_ORDER, encoding='utf-8') as f:
            players = json.load(f).get('players', [])
        return [p for p in players if isinstance(p, dict) and 'port' in p]
    except (OSError, ValueError, AttributeError):
        return []


def save_player_order(entries):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = PLAYER_ORDER + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'players': entries}, f, indent=1)
        f.write('\n')
    os.replace(tmp, PLAYER_ORDER)


def match_players(nodes, entries):
    """{node: index of its entry}: the entry for its exact socket first, then,
    for a pad in a socket the list does not know, the first free entry of the
    same model (its adapter was moved to another USB port)."""
    ids = {n: node_identity(n) for n in nodes}
    rank, used = {}, set()
    for field in ('port', 'model'):
        for n in nodes:
            if n in rank:
                continue
            i = next((i for i, e in enumerate(entries)
                      if i not in used and e.get(field) == ids[n][field]), None)
            if i is not None:
                rank[n] = i
                used.add(i)
    return rank


def sort_players(nodes, entries):
    """nodes (in plug order) in the saved player order; pads it does not know
    come after, in plug order."""
    rank = match_players(nodes, entries)
    return sorted((n for n in nodes if n in rank), key=rank.get) + [n for n in nodes if n not in rank]


def order_entries(nodes, old):
    """The list to save for nodes in this order. Pads that are not connected
    keep their entries after them, so they come back after the ones placed now."""
    used = set(match_players(nodes, old).values())
    new = []
    for n in nodes:
        ident = node_identity(n)
        new.append({'port': ident['port'], 'model': ident['model'],
                    'name': _read(f'/sys/class/input/{os.path.basename(n)}/device/name')})
    return new + [e for i, e in enumerate(old) if i not in used]


def joystick_nodes(entries=None):
    """Every pad's evdev node in player order: the saved order (entries, or
    the file when None), then plug order."""
    return sort_players(plug_order(), load_player_order() if entries is None else entries)


def fnv1(text):
    h = 0x811c9dc5
    for c in text:
        h = ((h * 16777619) & 0xffffffff) ^ ord(c)
    return h


def xinput_key(vid, pid, index, root='1&f33442ae'):
    """What Wine's xinput sorts pads by. winebus names the pad's device
    <root>&0&<index>, index being the order SDL opened it in, and every
    device below takes a prefix that is the FNV-1 hash of its parent's path.
    xinput fills its four slots in the order of the XI_00 child's name."""
    ids = f'VID_{vid:04X}&PID_{pid:04X}'
    bus_id = f'{root}&0&{index:x}'
    bus = f'WINEBUS\\{ids}\\{bus_id}'
    xi = f'WINEXINPUT\\{ids}&XI_00\\2&{fnv1(bus):x}&0&{bus_id}'
    return f'HID#{ids}&XI_00#3&{fnv1(xi):x}&0&0000'.upper()


def node_ids(node):
    base = f'/sys/class/input/{os.path.basename(node)}/device/id/'
    try:
        return tuple(int(open(base + f).read(), 16) for f in ('vendor', 'product'))
    except (OSError, ValueError):
        return (0, 0)


def plan_slots(players, first_index=0):
    """(the order to hand SDL the pads in so that Wine's XInput slots follow
    players, the wanted player order; the order those slots end up in).
    Pads of one model can be put in any order this way; different models
    always sort by vendor and product id. SDL opens pads it drives itself
    (HIDAPI: DualShock, DualSense, Switch) first, so the evdev ones start at
    first_index."""
    groups = {}
    for node in players:
        groups.setdefault(node_ids(node), []).append(node)
    index_of, free = {}, first_index
    for ids, nodes in groups.items():
        indexes = sorted(range(free, free + len(nodes)), key=lambda i: xinput_key(*ids, i))
        free += len(nodes)
        index_of.update(zip(nodes, indexes))
    order = sorted(players, key=index_of.get)
    slots = sorted(players, key=lambda n: xinput_key(*node_ids(n), index_of[n]))
    return order, slots


def open_order(players, first_index=0):
    order, slots = plan_slots(players, first_index)
    log('players: ' + ', '.join(os.path.basename(n) for n in players)[:400])
    log('XInput slots: ' + ', '.join(os.path.basename(n) for n in slots)[:400])
    return order


def guess(axes, hats, buttons):
    # The layout most PC pads sold as PlayStation-style use: 1-4 are
    # Triangle, Circle, Cross, Square, then L1 R1 L2 R2 Select Start L3 R3
    names = ['y', 'b', 'a', 'x', 'leftshoulder', 'rightshoulder', 'lefttrigger',
             'righttrigger', 'back', 'start', 'leftstick', 'rightstick', 'guide']
    fields = [f'{n}:b{i}' for i, n in enumerate(names[:buttons])]
    if axes >= 2:
        fields += ['leftx:a0', 'lefty:a1']
    if axes >= 6:
        # X Y Z Rx Ry Rz like an Xbox pad: Z and Rz are the triggers
        fields = [f for f in fields if not f.startswith(('lefttrigger', 'righttrigger'))]
        fields += ['lefttrigger:a2', 'rightx:a3', 'righty:a4', 'righttrigger:a5']
    elif axes == 5:
        fields += ['rightx:a3', 'righty:a4']
    elif axes == 4:
        fields += ['rightx:a2', 'righty:a3']
    if hats:
        fields += ['dpup:h0.1', 'dpdown:h0.4', 'dpleft:h0.8', 'dpright:h0.2']
    return ','.join(fields) + ',platform:Linux,'


def parse(mapping):
    """'guid,name,k:v,...' -> (guid, name, {k: v}) without platform/crc."""
    guid, name, rest = mapping.split(',', 2)
    fields = {}
    for f in rest.split(','):
        if ':' in f:
            k, v = f.split(':', 1)
            if k not in ('platform', 'crc', 'hint', 'type', 'face', 'sdk>=', 'sdk<='):
                fields[k] = v
    return guid, name, fields


class SDL:
    """The few SDL3 calls the scripts here need, through ctypes."""

    class GUID(ctypes.Structure):
        _fields_ = [('data', ctypes.c_uint8 * 16)]

    def __init__(self):
        lib = ctypes.CDLL('libSDL3.so.0')
        u32, cstr, ptr, i32 = ctypes.c_uint32, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int
        for fn, res, args in (
                ('SDL_Init', ctypes.c_bool, [u32]),
                ('SDL_Quit', None, []),
                ('SDL_PumpEvents', None, []),
                ('SDL_FlushEvents', None, [u32, u32]),
                ('SDL_GetJoysticks', ctypes.POINTER(u32), [ctypes.POINTER(i32)]),
                ('SDL_GetJoystickNameForID', cstr, [u32]),
                ('SDL_GetJoystickPathForID', cstr, [u32]),
                ('SDL_GetGamepadMappingForID', cstr, [u32]),
                ('SDL_GetJoystickGUIDForID', self.GUID, [u32]),
                ('SDL_OpenJoystick', ptr, [u32]),
                ('SDL_CloseJoystick', None, [ptr]),
                ('SDL_GetNumJoystickAxes', i32, [ptr]),
                ('SDL_GetNumJoystickHats', i32, [ptr]),
                ('SDL_GetNumJoystickButtons', i32, [ptr]),
                ('SDL_GetJoystickAxis', ctypes.c_int16, [ptr, i32]),
                ('SDL_GetJoystickHat', ctypes.c_uint8, [ptr, i32]),
                ('SDL_GetJoystickButton', ctypes.c_bool, [ptr, i32]),
                ('SDL_RumbleJoystick', ctypes.c_bool, [ptr, ctypes.c_uint16, ctypes.c_uint16, u32])):
            getattr(lib, fn).restype = res
            getattr(lib, fn).argtypes = args
        if not lib.SDL_Init(0x2000):  # SDL_INIT_GAMEPAD, which brings joysticks
            raise RuntimeError('SDL_Init failed')
        self.lib = lib

    def joysticks(self):
        count = ctypes.c_int()
        ids = self.lib.SDL_GetJoysticks(ctypes.byref(count))
        return list(ids[:count.value]) if ids else []

    def info(self, jid):
        lib = self.lib
        mapping = lib.SDL_GetGamepadMappingForID(jid)
        return {
            'id': jid,
            'guid': bytes(lib.SDL_GetJoystickGUIDForID(jid).data).hex(),
            'name': (lib.SDL_GetJoystickNameForID(jid) or b'pad').decode(errors='replace'),
            'path': (lib.SDL_GetJoystickPathForID(jid) or b'').decode(errors='replace'),
            'mapping': mapping.decode(errors='replace') if mapping else None,
        }

    def shape(self, jid):
        joy = self.lib.SDL_OpenJoystick(jid)
        if not joy:
            return None
        lib = self.lib
        shape = (lib.SDL_GetNumJoystickAxes(joy), lib.SDL_GetNumJoystickHats(joy),
                 lib.SDL_GetNumJoystickButtons(joy))
        lib.SDL_CloseJoystick(joy)
        return shape


def resolve(sdl):
    """Each connected pad type once, with the map SDL (and so Wine) gives it."""
    pads, seen = [], set()
    for jid in sdl.joysticks():
        pad = sdl.info(jid)
        if pad['guid'] in seen:  # both ports of an adapter share one map
            continue
        seen.add(pad['guid'])
        if pad['mapping']:
            pad['source'] = 'known'
        else:
            shape = sdl.shape(jid)
            if not shape:
                log(f"{pad['path']} {pad['name']}: cannot open, left out")
                continue
            pad['mapping'] = f"{pad['guid']},{pad['name'].replace(',', ' ')},{guess(*shape)}"
            pad['source'] = 'guessed for %d axes, %d hats, %d buttons' % shape
            remember_guess(pad['mapping'])
        # Pin the map to this pad's exact GUID so nothing else outranks it
        pad['mapping'] = pad['guid'] + pad['mapping'][pad['mapping'].index(','):]
        pads.append(pad)
    return pads


def main():
    as_json = '--json' in sys.argv
    base = base_mappings(with_learned='--default' not in sys.argv)
    # SDL reads the map from the environment when it starts; the session's
    # file is already part of base
    os.environ.pop('SDL_GAMECONTROLLERCONFIG_FILE', None)
    os.environ['SDL_GAMECONTROLLERCONFIG'] = '\n'.join(base)
    paths = []
    try:
        sdl = SDL()
        paths = [sdl.info(j)['path'] for j in sdl.joysticks()]
        pads = resolve(sdl)
        sdl.lib.SDL_Quit()
    except Exception as e:  # keep the games playable with the static map
        log(f'SDL check failed ({e}), using the static map')
        pads = []
    if as_json:
        print(json.dumps(pads))
        return
    write_session_db()
    lines = base + [p['mapping'] for p in pads]
    for p in pads:
        log(f"{p['path']} {p['name']}: {p['source']}: {p['mapping']}")
    # Everything the session file holds is in lines already
    print('unset SDL_GAMECONTROLLERCONFIG_FILE')
    print('export SDL_GAMECONTROLLERCONFIG=' + shlex.quote('\n'.join(lines)))
    nodes = open_order(joystick_nodes(), sum(not p.startswith('/dev/input/event') for p in paths))
    if nodes:
        print('export SDL_JOYSTICK_DEVICE=' + shlex.quote(':'.join(nodes)))
    else:
        print('unset SDL_JOYSTICK_DEVICE')


if __name__ == '__main__':
    main()
