#!/usr/bin/env python3
# Controller Settings: a picture of the pad that lights up whatever each press
# does, and a list of every function like the Controller tab of PES Settings.
# Click a function (on the picture or in the list), press the pad's button,
# and it is set. Saved maps go to ~/.config/game-pads/mappings.txt, which the
# game launchers read on every start and, from the next login, every SDL game
# in the session (through ~/.config/environment.d/60-game-pads.conf).
#
# Maps belong to a pad type (SDL's GUID), not to a port: the two ports of a
# Twin USB adapter, or two adapters of the same model, always share one map.
#
# The player strip at the top sets the player order: drag a pad's box to
# another place (or Alt+Left/Right on the selected one). Apply or OK keeps it
# in ~/.config/game-pads/player-order.json, which pad_maps.py follows.
import importlib.util
import os
import signal
import subprocess
import sys
import time
from math import pi

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

HERE = os.path.dirname(os.path.realpath(__file__))
spec = importlib.util.spec_from_file_location('pad_maps', os.path.join(HERE, 'pad_maps.py'))
pad_maps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pad_maps)

APP_ID = 'local.games.PadSettings'
LISTEN_SECONDS = 10
PRESS = 20000  # how far an axis has to move to count as a press


class Func:
    """One function of the pad. badge is the icon text in the lists, game is
    the name games show for it on screen (they use Xbox letters)."""

    def __init__(self, key, label, side, badge, game=''):
        self.key, self.label, self.side = key, label, side
        self.badge, self.game = badge, game
        self.short = label
        self.is_dir = key[-1] in '+-'
        if self.is_dir:
            self.axis, self.sign = key[:-1], 1 if key[-1] == '+' else -1


# Same order as the Controller tab of PES Settings
FUNCS = [
    Func('lefttrigger', 'Left Trigger', 'L', 'L2', 'LT'),
    Func('leftshoulder', 'Left Shoulder', 'L', 'L1', 'LB'),
    Func('dpup', 'D-pad Up', 'L', '▲'),
    Func('dpdown', 'D-pad Down', 'L', '▼'),
    Func('dpleft', 'D-pad Left', 'L', '◀'),
    Func('dpright', 'D-pad Right', 'L', '▶'),
    Func('lefty-', 'Left Stick Up', 'L', 'L▲'),
    Func('leftx-', 'Left Stick Left', 'L', 'L◀'),
    Func('lefty+', 'Left Stick Down', 'L', 'L▼'),
    Func('leftx+', 'Left Stick Right', 'L', 'L▶'),
    Func('leftstick', 'Left Stick Press', 'L', 'L3', 'LS'),
    Func('back', 'Select', 'L', 'SEL', 'View'),
    Func('righttrigger', 'Right Trigger', 'R', 'R2', 'RT'),
    Func('rightshoulder', 'Right Shoulder', 'R', 'R1', 'RB'),
    Func('y', 'Triangle', 'R', '△', 'Y'),
    Func('x', 'Square', 'R', '□', 'X'),
    Func('a', 'Cross', 'R', '✕', 'A'),
    Func('b', 'Circle', 'R', '○', 'B'),
    Func('righty-', 'Right Stick Up', 'R', 'R▲'),
    Func('rightx-', 'Right Stick Left', 'R', 'R◀'),
    Func('righty+', 'Right Stick Down', 'R', 'R▼'),
    Func('rightx+', 'Right Stick Right', 'R', 'R▶'),
    Func('rightstick', 'Right Stick Press', 'R', 'R3', 'RS'),
    Func('start', 'Start', 'R', 'STA', 'Menu'),
    Func('guide', 'Home', 'R', 'PS', 'Guide'),
]
BY_KEY = {f.key: f for f in FUNCS}
# SDL output order for the saved line
ORDER = ['a', 'b', 'x', 'y', 'back', 'guide', 'start', 'leftstick', 'rightstick',
         'leftshoulder', 'rightshoulder', 'dpup', 'dpdown', 'dpleft', 'dpright',
         'leftx', '+leftx', '-leftx', 'lefty', '+lefty', '-lefty',
         'rightx', '+rightx', '-rightx', 'righty', '+righty', '-righty',
         'lefttrigger', 'righttrigger']
HAT_NAMES = {1: '↑', 2: '→', 4: '↓', 8: '←'}


# --- inputs ("b3", "h0.4", "a1", "a1~", "+a2", "-a2") ----------------------

def atoms(inp):
    """The parts of the pad an input uses, to find two functions on one input."""
    s = inp.rstrip('~')
    if s[0] == 'a':
        return {'+' + s, '-' + s}
    return {s}


def describe(inp):
    inverted = inp.endswith('~')
    s = inp.rstrip('~')
    if s[0] == 'b':
        return f'Button {int(s[1:]) + 1}'
    if s[0] == 'h':
        hat, bit = s[1:].split('.')
        return 'Hat ' + HAT_NAMES.get(int(bit), bit) + (f' ({int(hat) + 1})' if hat != '0' else '')
    if s[0] in '+-':
        return f'Axis {int(s[2:]) + 1} {"+" if s[0] == "+" else "−"}'
    return f'Axis {int(s[1:]) + 1}' + (' inverted' if inverted else '')


def value(inp, st):
    """0..1 for a button or half axis, -1..1 for a whole axis."""
    inverted = inp.endswith('~')
    s = inp.rstrip('~')
    try:
        if s[0] == 'b':
            return 1.0 if st.buttons[int(s[1:])] else 0.0
        if s[0] == 'h':
            hat, bit = s[1:].split('.')
            return 1.0 if st.hats[int(hat)] & int(bit) else 0.0
        if s[0] in '+-':
            v = st.axes[int(s[2:])] / 32767
            return max(0.0, v if s[0] == '+' else -v)
        v = max(-1.0, st.axes[int(s[1:])] / 32767)
        return -v if inverted else v
    except (IndexError, ValueError):
        return 0.0


def is_whole_axis(inp):
    return inp[0] == 'a'


def half_of(whole, direction):
    """The half of a whole-axis input that pushes the output towards direction."""
    raw = -direction if whole.endswith('~') else direction
    return ('+' if raw > 0 else '-') + whole.rstrip('~')


class State:
    def __init__(self, axes, hats, buttons):
        self.axes, self.hats, self.buttons = axes, hats, buttons


class PadMap:
    """One pad type's map as {SDL output: input}."""

    def __init__(self, fields):
        self.f = {k: v for k, v in fields.items() if k in ORDER or k.lstrip('+-') in ORDER}

    def copy(self):
        return PadMap(dict(self.f))

    def binding(self, func):
        if func.is_dir:
            if func.axis in self.f:
                return self.f[func.axis]
            return self.f.get(('+' if func.sign > 0 else '-') + func.axis)
        return self.f.get(func.key)

    def describe(self, func):
        inp = self.binding(func)
        if inp is None:
            return 'Not set'
        if func.is_dir and func.axis in self.f:
            return describe(half_of(inp, func.sign))
        return describe(inp)

    def stick(self, axis, st):
        if axis in self.f:
            return value(self.f[axis], st)
        plus, minus = self.f.get('+' + axis), self.f.get('-' + axis)
        return (value(plus, st) if plus else 0.0) - (value(minus, st) if minus else 0.0)

    def active(self, func, st):
        if func.is_dir:
            return self.stick(func.axis, st) * func.sign > 0.5
        inp = self.f.get(func.key)
        if inp is None:
            return False
        v = value(inp, st)
        return (v + 1) / 2 > 0.5 if is_whole_axis(inp) else v > 0.5

    def assign(self, func, inp):
        """Put inp on func and take it off whatever else used it; returns the
        functions that lost it."""
        whole = is_whole_axis(inp)
        if func.is_dir:
            half_key = ('+' if func.sign > 0 else '-') + func.axis
            target = func.axis if whole else half_key
        else:
            target = func.key
        lost = []
        for k, v in list(self.f.items()):
            if k != target and atoms(v) & atoms(inp):
                del self.f[k]
                lost.append(k)
        if func.is_dir:
            if whole:
                self.f.pop('+' + func.axis, None)
                self.f.pop('-' + func.axis, None)
            elif func.axis in self.f:
                # Keep the other direction on its half of the old axis
                other = -func.sign
                old = self.f.pop(func.axis)
                self.f[('+' if other > 0 else '-') + func.axis] = half_of(old, other)
        self.f[target] = inp
        return lost

    def clear(self, func):
        if func.is_dir:
            if func.axis in self.f:
                other = -func.sign
                old = self.f.pop(func.axis)
                self.f[('+' if other > 0 else '-') + func.axis] = half_of(old, other)
            else:
                self.f.pop(('+' if func.sign > 0 else '-') + func.axis, None)
        else:
            self.f.pop(func.key, None)

    def ordered(self):
        return {k: self.f[k] for k in ORDER if k in self.f}


def lost_names(keys):
    names = []
    for k in keys:
        if k in BY_KEY:
            names.append(BY_KEY[k].short)
        else:
            axis = k.lstrip('+-')
            names.append(('Left' if axis.startswith('left') else 'Right') + ' stick')
    return ', '.join(dict.fromkeys(names))


# --- pads -------------------------------------------------------------------

class Pad:
    def __init__(self, sdl, jid):
        self.sdl, self.jid = sdl, jid
        info = sdl.info(jid)
        self.guid, self.name, self.path = info['guid'], info['name'], info['path']
        self.joy = sdl.lib.SDL_OpenJoystick(jid)
        lib = sdl.lib
        self.n_axes = lib.SDL_GetNumJoystickAxes(self.joy) if self.joy else 0
        self.n_hats = lib.SDL_GetNumJoystickHats(self.joy) if self.joy else 0
        self.n_buttons = lib.SDL_GetNumJoystickButtons(self.joy) if self.joy else 0
        self.mapping = info['mapping']
        self.stuck = self.path.startswith('/dev/input/') and len(pad_maps.held_buttons(self.path)) >= 2
        self.rest = None
        self.prev = None

    def state(self):
        lib = self.sdl.lib
        if not self.joy:
            return State((), (), ())
        return State(tuple(lib.SDL_GetJoystickAxis(self.joy, i) for i in range(self.n_axes)),
                     tuple(lib.SDL_GetJoystickHat(self.joy, i) for i in range(self.n_hats)),
                     tuple(bool(lib.SDL_GetJoystickButton(self.joy, i)) for i in range(self.n_buttons)))

    def close(self):
        if self.joy:
            self.sdl.lib.SDL_CloseJoystick(self.joy)
            self.joy = None


def detect(base, st):
    """The first input that changed since base: ('button', n), ('hat', h, bit)
    or ('axis', n, direction, rest)."""
    for n, down in enumerate(st.buttons):
        if down and not base.buttons[n]:
            return ('button', n)
    for h, v in enumerate(st.hats):
        new = v & ~base.hats[h]
        if new:
            return ('hat', h, next(b for b in (1, 2, 4, 8) if new & b))
    for n, a in enumerate(st.axes):
        d = a - base.axes[n]
        if abs(d) > PRESS:
            return ('axis', n, 1 if d > 0 else -1, base.axes[n])
    return None


def to_input(func, det):
    kind = det[0]
    if kind == 'button':
        return f'b{det[1]}'
    if kind == 'hat':
        return f'h{det[1]}.{det[2]}'
    n, direction, rest = det[1:]
    if func.is_dir:
        return f'a{n}' + ('' if direction == func.sign else '~')
    if rest < -24000:  # a trigger that rests at one end
        return f'a{n}'
    if rest > 24000:
        return f'a{n}~'
    return ('+' if direction > 0 else '-') + f'a{n}'


# --- the pad picture ----------------------------------------------------------
# Drawn with cairo in a 760x500 space, in the shape of the pad in PES Settings
# (left stick high, d-pad and right stick low), with PlayStation symbols.

import cairo  # noqa: E402

W, H = 760, 500
LSTICK, RSTICK, DPAD, FACE = (232, 212), (460, 290), (300, 290), (562, 212)
GUIDE, SELECT, START = (380, 150), (328, 212), (432, 212)
FACE_POS = {'y': (FACE[0], FACE[1] - 38), 'b': (FACE[0] + 38, FACE[1]),
            'a': (FACE[0], FACE[1] + 38), 'x': (FACE[0] - 38, FACE[1])}
STICK_POS = {'left': LSTICK, 'right': RSTICK}


def rgb(hex_color, alpha=1.0):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (alpha,)


COLORS = {
    'active': rgb('#1a9fff'), 'listen': rgb('#66c0f4'), 'text': rgb('#c6d4df'),
    'dim': rgb('#6b7785'), 'unset': rgb('#ff6b6b'), 'ink': rgb('#0b0d10'),
    'y': rgb('#4fd1a1'), 'b': rgb('#ff6b6b'), 'a': rgb('#7aa8ff'), 'x': rgb('#ff8ad8'),
}


def mirrored(path):
    """The right-hand twin of a left-hand path."""
    def draw(cr):
        m = cr.get_matrix()
        cr.translate(W, 0)
        cr.scale(-1, 1)
        path(cr)
        cr.set_matrix(m)
    return draw


def body(cr):
    # Left half from the top centre down to the bottom centre, then the same
    # curves mirrored back up the right side
    top = (380, 118)
    half = [((330, 118), (290, 104), (230, 102)), ((170, 100), (120, 112), (92, 148)),
            ((62, 186), (50, 240), (42, 300)), ((32, 380), (28, 440), (62, 466)),
            ((92, 488), (136, 478), (156, 448)), ((178, 414), (198, 380), (236, 364)),
            ((280, 350), (330, 348), (380, 350))]
    cr.move_to(*top)
    for c1, c2, end in half:
        cr.curve_to(*c1, *c2, *end)
    ends = [top] + [seg[2] for seg in half]
    for i in range(len(half) - 1, -1, -1):
        c1, c2, _ = half[i]
        cr.curve_to(W - c2[0], c2[1], W - c1[0], c1[1], W - ends[i][0], ends[i][1])
    cr.close_path()


def left_trigger(cr):
    cr.move_to(118, 132)
    cr.curve_to(114, 88, 146, 52, 198, 46)
    cr.curve_to(238, 42, 264, 58, 272, 102)
    cr.line_to(274, 120)
    cr.close_path()


def left_bumper(cr):
    cr.move_to(70, 178)
    cr.curve_to(86, 128, 138, 96, 214, 90)
    cr.curve_to(258, 87, 300, 90, 330, 99)
    cr.curve_to(339, 102, 338, 114, 327, 114)
    cr.curve_to(296, 109, 256, 107, 214, 109)
    cr.curve_to(150, 113, 110, 140, 90, 182)
    cr.curve_to(85, 191, 67, 188, 70, 178)
    cr.close_path()


def circle(cx, cy, r):
    def draw(cr):
        cr.new_sub_path()
        cr.arc(cx, cy, r, 0, 2 * pi)
    return draw


def dpad_arm(dx, dy):
    def draw(cr):
        x, y = DPAD
        w, near, far = 26, 12, 38
        if dx:
            x0 = x + near if dx > 0 else x - far
            rrect(cr, x0, y - w / 2, far - near, w, 4)
        else:
            y0 = y + near if dy > 0 else y - far
            rrect(cr, x - w / 2, y0, w, far - near, 4)
    return draw


def dpad_cross(cr):
    x, y = DPAD
    w, far = 26, 38
    cr.move_to(x - w / 2, y - far + 4)
    for px, py in ((x + w / 2, y - far + 4), (x + w / 2, y - w / 2), (x + far - 4, y - w / 2),
                   (x + far - 4, y + w / 2), (x + w / 2, y + w / 2), (x + w / 2, y + far - 4),
                   (x - w / 2, y + far - 4), (x - w / 2, y + w / 2), (x - far + 4, y + w / 2),
                   (x - far + 4, y - w / 2), (x - w / 2, y - w / 2)):
        cr.line_to(px, py)
    cr.close_path()


def arrow(cx, cy, dx, dy, s=11):
    def draw(cr):
        px, py = -dy, dx
        cr.move_to(cx + dx * s, cy + dy * s)
        cr.line_to(cx - dx * s * 0.5 + px * s * 0.9, cy - dy * s * 0.5 + py * s * 0.9)
        cr.line_to(cx - dx * s * 0.5 - px * s * 0.9, cy - dy * s * 0.5 - py * s * 0.9)
        cr.close_path()
    return draw


def rrect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, pi / 2)
    cr.arc(x + r, y + h - r, r, pi / 2, pi)
    cr.arc(x + r, y + r, r, pi, 3 * pi / 2)
    cr.close_path()


# key -> (path, anchor for the "not set" dot)
SHAPES = {
    'lefttrigger': (left_trigger, (262, 64)),
    'righttrigger': (mirrored(left_trigger), (W - 262, 64)),
    'leftshoulder': (left_bumper, (318, 100)),
    'rightshoulder': (mirrored(left_bumper), (W - 318, 100)),
    'dpup': (dpad_arm(0, -1), (DPAD[0] + 13, DPAD[1] - 38)),
    'dpdown': (dpad_arm(0, 1), (DPAD[0] + 13, DPAD[1] + 26)),
    'dpleft': (dpad_arm(-1, 0), (DPAD[0] - 38, DPAD[1] - 13)),
    'dpright': (dpad_arm(1, 0), (DPAD[0] + 38, DPAD[1] - 13)),
    'back': (circle(*SELECT, 11), (SELECT[0] + 9, SELECT[1] - 9)),
    'start': (circle(*START, 11), (START[0] + 9, START[1] - 9)),
    'guide': (circle(*GUIDE, 22), (GUIDE[0] + 17, GUIDE[1] - 17)),
}
for key, (cx, cy) in FACE_POS.items():
    SHAPES[key] = (circle(cx, cy, 17), (cx + 13, cy - 13))
for side, (cx, cy) in STICK_POS.items():
    SHAPES[side + 'stick'] = (circle(cx, cy, 31), (cx + 24, cy - 24))
    for d, (dx, dy) in (('y-', (0, -1)), ('y+', (0, 1)), ('x-', (-1, 0)), ('x+', (1, 0))):
        SHAPES[side + d] = (arrow(cx + dx * 54, cy + dy * 54, dx, dy, 9), (cx + dx * 54 + 9, cy + dy * 54 - 9))
# Topmost first, for the mouse
HIT_ORDER = ([k for k in SHAPES if k[-1] in '+-'] +
             ['leftstick', 'rightstick', 'guide', 'back', 'start', 'y', 'b', 'a', 'x',
              'dpup', 'dpdown', 'dpleft', 'dpright', 'leftshoulder', 'rightshoulder',
              'lefttrigger', 'righttrigger'])
_HIT = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 1, 1))


def hit(key, x, y):
    path, anchor = SHAPES[key]
    if key[-1] in '+-':  # small arrows get a roomier target
        return (x - anchor[0] + 9) ** 2 + (y - anchor[1] - 9) ** 2 <= 17 ** 2
    _HIT.new_path()
    path(_HIT)
    return _HIT.in_fill(x, y)


def text(cr, s, x, y, size=12, color=COLORS['text'], weight=1):
    cr.select_font_face('Inter', 0, weight)
    cr.set_font_size(size)
    ext = cr.text_extents(s)
    cr.set_source_rgba(*color)
    cr.move_to(x - ext.width / 2 - ext.x_bearing, y - ext.height / 2 - ext.y_bearing)
    cr.show_text(s)


def glow(cr, path, color, scale=1.0):
    for width, alpha in ((16, 0.08), (10, 0.16), (5, 0.32)):
        cr.new_path()
        path(cr)
        cr.set_source_rgba(color[0], color[1], color[2], alpha)
        cr.set_line_width(width * scale)
        cr.stroke()


def vgrad(y0, y1, *stops):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for pos, color in stops:
        g.add_color_stop_rgba(pos, *rgb(color))
    return g


def face_symbol(cr, key, cx, cy, color, s=7.5):
    cr.set_source_rgba(*color)
    cr.set_line_width(2.4)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.new_path()
    if key == 'y':
        cr.move_to(cx, cy - s)
        cr.line_to(cx + s, cy + s * 0.72)
        cr.line_to(cx - s, cy + s * 0.72)
        cr.close_path()
    elif key == 'b':
        cr.arc(cx, cy, s, 0, 2 * pi)
    elif key == 'a':
        cr.move_to(cx - s, cy - s)
        cr.line_to(cx + s, cy + s)
        cr.move_to(cx + s, cy - s)
        cr.line_to(cx - s, cy + s)
    else:
        cr.rectangle(cx - s * 0.85, cy - s * 0.85, s * 1.7, s * 1.7)
    cr.stroke()


def draw_pad(cr, width, height, view):
    """view: dict with map, state, listen, hover and pulse; any may be None."""
    scale = min(width / W, height / H)
    cr.translate((width - W * scale) / 2, (height - H * scale) / 2)
    cr.scale(scale, scale)
    pmap, st = view.get('map'), view.get('state')
    listen, hover = view.get('listen'), view.get('hover')
    pulse = view.get('pulse', 1.0)

    def lit(key):
        return bool(pmap and st and pmap.active(BY_KEY[key], st))

    def state_overlay(key, path=None, color=None):
        """Light an element up when pressed, listening or under the mouse."""
        path = path or SHAPES[key][0]
        if listen == key:
            glow(cr, path, COLORS['listen'])
            cr.new_path()
            path(cr)
            c = COLORS['listen']
            cr.set_source_rgba(c[0], c[1], c[2], 0.25 + 0.45 * pulse)
            cr.fill()
        elif lit(key):
            c = color or COLORS['active']
            glow(cr, path, c)
            cr.new_path()
            path(cr)
            cr.set_source_rgba(c[0], c[1], c[2], 0.92)
            cr.fill()
        elif hover == key:
            cr.new_path()
            path(cr)
            cr.set_source_rgba(1, 1, 1, 0.12)
            cr.fill()

    def on(key):
        return listen == key or lit(key)

    # Soft floor shadow
    cr.save()
    cr.translate(380, 478)
    cr.scale(340, 22)
    shadow = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    shadow.add_color_stop_rgba(0, 0, 0, 0, 0.55)
    shadow.add_color_stop_rgba(1, 0, 0, 0, 0)
    cr.set_source(shadow)
    cr.arc(0, 0, 1, 0, 2 * pi)
    cr.fill()
    cr.restore()

    # Triggers behind the body
    for key, label in (('lefttrigger', 'L2'), ('righttrigger', 'R2')):
        path = SHAPES[key][0]
        cr.new_path()
        path(cr)
        cr.set_source(vgrad(42, 130, (0, '#3a3e45'), (0.5, '#24272c'), (1, '#121417')))
        cr.fill_preserve()
        cr.set_source_rgba(0, 0, 0, 0.9)
        cr.set_line_width(2)
        cr.stroke()
        state_overlay(key)
        x = 196 if key == 'lefttrigger' else W - 196
        text(cr, label, x, 68, 13, COLORS['ink'] if on(key) else COLORS['dim'])

    # Body
    cr.new_path()
    body(cr)
    cr.set_source(vgrad(100, 490, (0, '#33373e'), (0.35, '#1e2125'), (1, '#0c0d0f')))
    cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 1)
    cr.set_line_width(2.5)
    cr.stroke()
    # Sheen across the upper half
    cr.save()
    cr.new_path()
    body(cr)
    cr.clip()
    sheen = cairo.RadialGradient(380, 40, 40, 380, 120, 330)
    sheen.add_color_stop_rgba(0, 1, 1, 1, 0.10)
    sheen.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(sheen)
    cr.paint()
    # Darker grips
    for gx in (95, W - 95):
        grip = cairo.RadialGradient(gx, 420, 10, gx, 420, 110)
        grip.add_color_stop_rgba(0, 0, 0, 0, 0.35)
        grip.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(grip)
        cr.paint()
    cr.restore()

    # Bumpers over the top edge
    for key, label, lx in (('leftshoulder', 'L1', 200), ('rightshoulder', 'R1', W - 200)):
        path = SHAPES[key][0]
        cr.new_path()
        path(cr)
        cr.set_source(vgrad(88, 190, (0, '#4a4f57'), (0.4, '#2a2d33'), (1, '#16181b')))
        cr.fill_preserve()
        cr.set_source_rgba(0, 0, 0, 0.95)
        cr.set_line_width(1.8)
        cr.stroke()
        state_overlay(key)
        text(cr, label, lx, 101, 11, COLORS['ink'] if on(key) else COLORS['dim'])

    # Guide plate and button (a plain ring, no maker's logo)
    gx, gy = GUIDE
    cr.new_path()
    cr.arc(gx, gy, 30, 0, 2 * pi)
    cr.set_source(vgrad(gy - 30, gy + 30, (0, '#0d0e10'), (1, '#2a2d32')))
    cr.fill()
    cr.new_path()
    cr.arc(gx, gy, 22, 0, 2 * pi)
    cr.set_source(vgrad(gy - 22, gy + 22, (0, '#3c4048'), (1, '#16181b')))
    cr.fill()
    state_overlay('guide')
    cr.new_path()
    cr.arc(gx, gy, 12, 0, 2 * pi)
    cr.set_line_width(2.4)
    cr.set_source_rgba(*(COLORS['ink'] if on('guide') else (0.85, 0.88, 0.92, 0.85)))
    cr.stroke()
    text(cr, 'HOME', gx, gy + 36, 8, COLORS['dim'])

    # Select and Start
    for key, (cx, cy), label in (('back', SELECT, 'SELECT'), ('start', START, 'START')):
        cr.new_path()
        cr.arc(cx, cy, 13, 0, 2 * pi)
        cr.set_source_rgba(0, 0, 0, 0.6)
        cr.fill()
        cr.new_path()
        cr.arc(cx, cy, 11, 0, 2 * pi)
        cr.set_source(vgrad(cy - 11, cy + 11, (0, '#40444c'), (1, '#1a1c20')))
        cr.fill()
        state_overlay(key)
        ink = COLORS['ink'] if on(key) else (0.8, 0.83, 0.87, 0.9)
        cr.set_source_rgba(*ink)
        cr.set_line_width(1.4)
        if key == 'back':
            cr.rectangle(cx - 5, cy - 3.5, 6, 5)
            cr.rectangle(cx - 1, cy - 1.5, 6, 5)
        else:
            for dy in (-3, 0, 3):
                cr.move_to(cx - 4.5, cy + dy)
                cr.line_to(cx + 4.5, cy + dy)
        cr.stroke()
        text(cr, label, cx, cy + 22, 8, COLORS['dim'])

    # D-pad in its round well
    dx, dy = DPAD
    well = cairo.RadialGradient(dx, dy - 10, 10, dx, dy, 48)
    well.add_color_stop_rgba(0, *rgb('#050607'))
    well.add_color_stop_rgba(0.85, *rgb('#121417'))
    well.add_color_stop_rgba(1, *rgb('#2a2d33'))
    cr.new_path()
    cr.arc(dx, dy, 45, 0, 2 * pi)
    cr.set_source(well)
    cr.fill()
    cr.new_path()
    dpad_cross(cr)
    cr.set_source(vgrad(dy - 38, dy + 38, (0, '#4a4e56'), (0.5, '#2b2e34'), (1, '#1a1c20')))
    cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 0.9)
    cr.set_line_width(1.5)
    cr.stroke()
    for key, (ax, ay) in (('dpup', (0, -1)), ('dpdown', (0, 1)), ('dpleft', (-1, 0)), ('dpright', (1, 0))):
        state_overlay(key)
        arrow(dx + ax * 27, dy + ay * 27, ax, ay, 5)(cr)
        cr.set_source_rgba(*(COLORS['ink'] if on(key) else (0.75, 0.78, 0.82, 0.8)))
        cr.fill()

    # Sticks: recessed well, direction marks, concave cap moved by the stick
    for side, (cx, cy) in STICK_POS.items():
        well = cairo.RadialGradient(cx, cy - 8, 20, cx, cy, 46)
        well.add_color_stop_rgba(0, *rgb('#020203'))
        well.add_color_stop_rgba(0.8, *rgb('#0e1012'))
        well.add_color_stop_rgba(1, *rgb('#2c2f35'))
        cr.new_path()
        cr.arc(cx, cy, 45, 0, 2 * pi)
        cr.set_source(well)
        cr.fill()
        for d in ('y-', 'y+', 'x-', 'x+'):
            key = side + d
            path = SHAPES[key][0]
            cr.new_path()
            path(cr)
            cr.set_source_rgba(1, 1, 1, 0.16)
            cr.fill()
            state_overlay(key)
        ox = pmap.stick(side + 'x', st) if pmap and st else 0
        oy = pmap.stick(side + 'y', st) if pmap and st else 0
        key = side + 'stick'
        px, py = cx + ox * 14, cy + oy * 14
        cap = circle(px, py, 31)
        cr.new_path()
        cr.arc(px + 1, py + 3, 32, 0, 2 * pi)
        cr.set_source_rgba(0, 0, 0, 0.6)
        cr.fill()
        rim = cairo.RadialGradient(px - 10, py - 14, 4, px, py, 32)
        rim.add_color_stop_rgba(0, *rgb('#565b64'))
        rim.add_color_stop_rgba(1, *rgb('#1c1e22'))
        cr.new_path()
        cap(cr)
        cr.set_source(rim)
        cr.fill()
        dish = cairo.RadialGradient(px + 4, py + 6, 2, px, py, 22)
        dish.add_color_stop_rgba(0, *rgb('#3a3e45'))
        dish.add_color_stop_rgba(1, *rgb('#16181b'))
        cr.new_path()
        cr.arc(px, py, 22, 0, 2 * pi)
        cr.set_source(dish)
        cr.fill()
        state_overlay(key, cap)
        text(cr, 'L3' if side == 'left' else 'R3', px, py, 11,
             COLORS['ink'] if on(key) else (0.55, 0.59, 0.64, 1))

    # Face buttons: glossy black with the PlayStation symbols
    for key, (cx, cy) in FACE_POS.items():
        cr.new_path()
        cr.arc(cx + 0.5, cy + 2, 18.5, 0, 2 * pi)
        cr.set_source_rgba(0, 0, 0, 0.7)
        cr.fill()
        cr.new_path()
        cr.arc(cx, cy, 17, 0, 2 * pi)
        cr.set_source(vgrad(cy - 17, cy + 17, (0, '#3a3e45'), (1, '#0f1012')))
        cr.fill()
        gloss = cairo.RadialGradient(cx - 5, cy - 8, 1, cx, cy - 4, 14)
        gloss.add_color_stop_rgba(0, 1, 1, 1, 0.22)
        gloss.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.new_path()
        cr.arc(cx, cy, 17, 0, 2 * pi)
        cr.set_source(gloss)
        cr.fill()
        state_overlay(key, color=COLORS[key])
        face_symbol(cr, key, cx, cy, COLORS['ink'] if lit(key) and listen != key else COLORS[key])

    # A red dot on every function the pad does not have yet
    if pmap:
        for key, (_path, (ax, ay)) in SHAPES.items():
            if pmap.binding(BY_KEY[key]) is None:
                cr.new_path()
                cr.arc(ax, ay, 4.5, 0, 2 * pi)
                cr.set_source_rgba(*COLORS['unset'])
                cr.fill_preserve()
                cr.set_source_rgba(0, 0, 0, 0.8)
                cr.set_line_width(1.2)
                cr.stroke()
    return scale


# --- the window ---------------------------------------------------------------

CSS = """
:root {
  --window-bg-color: #1b2838; --window-fg-color: #c6d4df;
  --view-bg-color: #16202d; --view-fg-color: #c6d4df;
  --headerbar-bg-color: #171a21; --headerbar-fg-color: #dcdedf;
  --headerbar-backdrop-color: #171a21; --headerbar-shade-color: rgba(0,0,0,0.5);
  --card-bg-color: rgba(0,0,0,0.2); --popover-bg-color: #202d3c;
  --dialog-bg-color: #202d3c; --dialog-fg-color: #c6d4df;
  --accent-bg-color: #1a9fff; --accent-fg-color: #ffffff; --accent-color: #66c0f4;
}
window, label, button { font-family: "Inter", "Adwaita Sans", sans-serif; }
.steam-window {
  background: linear-gradient(180deg, #213246 0%, #1b2838 30%, #141c26 100%);
}
headerbar { box-shadow: 0 1px rgba(0,0,0,0.6); }
.app-title { font-weight: 800; font-size: 13px; letter-spacing: 3px; color: #dcdedf; }
.app-icon { color: #66c0f4; }

.pad-strip { padding: 14px 22px 0 22px; }
.strip-title { margin: 0; }
.chip-rail { padding: 6px 2px 12px 2px; }
/* Solid colours: boxes slide over each other while one is dragged */
.pad-chip {
  background: #253446; border: 1px solid #2c3a4b;
  border-radius: 6px; padding: 8px 12px 8px 16px;
}
.pad-chip:hover { background: #2b3a4c; }
.pad-chip:checked {
  background: linear-gradient(180deg, #1d4e77, #1e3c59);
  border-color: #1a9fff; box-shadow: 0 0 12px rgba(26,159,255,0.35);
}
.pad-chip.dragging {
  background: linear-gradient(180deg, #2b5f8a, #1d3f5e); border-color: #66c0f4;
  box-shadow: 0 8px 20px rgba(0,0,0,0.6), 0 0 16px rgba(102,192,244,0.45);
}
.chip-grip { color: #4b5866; }
.pad-chip:hover .chip-grip, .pad-chip.dragging .chip-grip { color: #c6d4df; }
.chip-where { font-size: 11px; color: #5c6a78; }
.pad-chip:checked .chip-where { color: #8fb4d4; }
.hint.warn { color: #e5b143; }
.small-btn { padding: 3px 12px; font-size: 12px; }
.chip-player { font-size: 10px; font-weight: 700; letter-spacing: 2px; color: #7d8a96; }
.pad-chip:checked .chip-player { color: #66c0f4; }
.chip-name { font-size: 13px; font-weight: 600; color: #dcdedf; }
.dot-ok { color: #59bf40; font-size: 9px; }
.dot-bad { color: #ff6b6b; font-size: 9px; }
.share-note { color: #7d8a96; font-size: 12px; }

.panel {
  background: rgba(10,16,24,0.45); border: 1px solid rgba(255,255,255,0.04);
  border-radius: 8px; padding: 14px 10px;
}
.section-title { font-size: 11px; font-weight: 800; letter-spacing: 2.5px; color: #7d8a96;
  margin: 0 8px 8px 8px; }
.pad-heading { font-size: 18px; font-weight: 700; color: #ffffff; }
.pad-sub { font-size: 12px; color: #7d8a96; }
.hint { font-size: 12px; color: #7d8a96; }

.map-row { background: transparent; border-radius: 4px; padding: 3px 4px 3px 10px;
  min-height: 30px; box-shadow: none; }
.map-row:hover { background: rgba(255,255,255,0.05); }
.map-row.active { background: rgba(26,159,255,0.16); box-shadow: inset 3px 0 #1a9fff; }
.map-row.listening { box-shadow: inset 3px 0 #66c0f4; animation: listen 0.8s ease-in-out infinite alternate; }
@keyframes listen { from { background: rgba(102,192,244,0.32); } to { background: rgba(102,192,244,0.08); } }
.row-name { color: #c6d4df; font-size: 13px; }
.map-row.active .row-name { color: #ffffff; }
.pill { background: rgba(255,255,255,0.06); border-radius: 3px; padding: 2px 9px;
  font-size: 12px; font-weight: 600; color: #dcdedf; min-width: 86px; }
.map-row.active .pill { background: #1a9fff; color: #ffffff; }
.map-row.listening .pill { background: rgba(102,192,244,0.25); color: #ffffff; }
.pill.unset { color: #ff6b6b; background: rgba(255,107,107,0.1); }
.row-clear { min-width: 24px; min-height: 24px; padding: 0; opacity: 0.35; }
.row-clear:hover { opacity: 1; }

.footer { background: #171a21; padding: 12px 22px; box-shadow: 0 -1px rgba(255,255,255,0.04); }
.status { color: #8f98a0; font-size: 12px; }
.status-icon { color: #66c0f4; }
.steam-btn { background: rgba(103,193,245,0.12); color: #66c0f4; border-radius: 3px;
  padding: 7px 16px; font-weight: 600; box-shadow: none; }
.steam-btn:hover { background: linear-gradient(-60deg, #417a9b 5%, #67c1f5 95%); color: #ffffff; }
.steam-primary { background: linear-gradient(90deg, #06bfff 0%, #2d73ff 100%); color: #ffffff;
  border-radius: 3px; padding: 7px 26px; font-weight: 700; box-shadow: none; }
.steam-primary:hover { background: linear-gradient(90deg, #3fd0ff 0%, #5a92ff 100%); }
.steam-primary:disabled { background: rgba(255,255,255,0.06); color: #5c6670; }
.badge { min-width: 34px; min-height: 22px; border-radius: 4px; background: #2a3542;
  color: #dcdedf; font-size: 10px; font-weight: 800; }
.badge.round { min-width: 24px; min-height: 24px; border-radius: 12px; background: #0f1216;
  font-size: 13px; border: 1px solid rgba(255,255,255,0.08); }
.badge.tri { color: #4fd1a1; } .badge.cir { color: #ff6b6b; }
.badge.crs { color: #7aa8ff; } .badge.sqr { color: #ff8ad8; }
.badge.dpad { background: #1c232c; color: #c6d4df; font-size: 9px; }
.badge.stick { border-radius: 11px; background: #1c232c; }
.map-row.active .badge { background: #1a9fff; color: #ffffff; }
.game-name { color: #5c6a78; font-size: 11px; }
.revert { margin-top: 4px; }
.player-note { color: #7d8a96; font-size: 11px; }
"""


BADGE_CLASSES = {
    'y': ['round', 'tri'], 'b': ['round', 'cir'], 'a': ['round', 'crs'], 'x': ['round', 'sqr'],
    'dpup': ['dpad'], 'dpdown': ['dpad'], 'dpleft': ['dpad'], 'dpright': ['dpad'],
}
XINPUT_PLAYERS = 4  # XInput (Windows, and Wine) has four slots
CHIP_W, CHIP_GAP = 200, 10  # player boxes: narrowest width, and the space between
DRAG_START = 8  # pixels the mouse moves before a press on a box becomes a drag
ORDER_HINT = 'Drag a controller to change its player number. Press a button on a pad to find it.'


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Controller Settings', default_width=1440,
                         default_height=860, css_classes=['steam-window'])
        self.sdl = pad_maps.SDL()
        self.pads = []          # connected Pad objects, in player order
        self.maps = {}          # guid -> PadMap being edited
        self.saved = {}         # guid -> PadMap as saved
        self.current = None     # selected Pad
        self.listen = None      # (func, deadline, baseline)
        self.hover = None
        self.scale, self.offset = 1.0, (0, 0)
        self.last_view = None
        self.chips = []         # widgets in the player strip
        self.chip_of = {}       # Pad -> (box, its PLAYER n label)
        self.chip_x = {}        # Pad -> where its box is drawn now (it slides to its slot)
        self.slot = CHIP_W + CHIP_GAP
        self.drag = None        # the box being dragged, see on_strip_press
        self.plug_nodes = []    # evdev pads in plug-in order
        self.order_saved = pad_maps.load_player_order()
        self.order_pending = list(self.order_saved)  # what Apply would save
        self.order_changed = False

        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.toasts = Adw.ToastOverlay()
        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        title = Gtk.Box(spacing=10)
        title.append(Gtk.Image(icon_name='input-gaming-symbolic', pixel_size=18,
                               css_classes=['app-icon']))
        title.append(Gtk.Label(label='CONTROLLER SETTINGS', css_classes=['app-title']))
        header.set_title_widget(title)
        view.add_top_bar(header)
        self.toasts.set_child(view)
        self.set_content(self.toasts)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        view.set_content(root)

        strip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, css_classes=['pad-strip'])
        head = Gtk.Box(spacing=14)
        head.append(Gtk.Label(label='PLAYERS', css_classes=['section-title', 'strip-title']))
        self.order_hint = Gtk.Label(label=ORDER_HINT, xalign=0, hexpand=True, wrap=True,
                                    css_classes=['hint'])
        head.append(self.order_hint)
        self.share_note = Gtk.Label(css_classes=['share-note'], valign=Gtk.Align.CENTER)
        head.append(self.share_note)
        self.order_reset = Gtk.Button(label='Default Order', visible=False,
                                      css_classes=['steam-btn', 'small-btn'],
                                      tooltip_text='Players in the order the pads were plugged in')
        self.order_reset.connect('clicked', self.on_order_reset)
        head.append(self.order_reset)
        strip.append(head)
        # The boxes sit at fixed places so they can slide while one is dragged
        self.chip_box = Gtk.Fixed(css_classes=['chip-rail'])
        self.chip_scroll = Gtk.ScrolledWindow(hexpand=True, vscrollbar_policy=Gtk.PolicyType.NEVER,
                                              hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                                              propagate_natural_height=True)
        self.chip_scroll.set_child(self.chip_box)
        drag = Gtk.GestureDrag(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        drag.connect('drag-begin', self.on_strip_press)
        drag.connect('drag-update', self.on_strip_drag)
        drag.connect('drag-end', self.on_strip_release)
        self.chip_box.add_controller(drag)
        strip.append(self.chip_scroll)
        root.append(strip)

        middle = Gtk.Box(spacing=16, vexpand=True, margin_top=12, margin_bottom=16,
                         margin_start=22, margin_end=22)
        self.rows = {}
        middle.append(self.side_panel('L', 'LEFT SIDE'))
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True,
                         css_classes=['panel'])
        self.pad_heading = Gtk.Label(xalign=0, css_classes=['pad-heading'], margin_start=8)
        self.pad_sub = Gtk.Label(xalign=0, css_classes=['pad-sub'], margin_start=8)
        center.append(self.pad_heading)
        center.append(self.pad_sub)
        self.area = Gtk.DrawingArea(hexpand=True, vexpand=True, content_width=560,
                                    content_height=360)
        self.area.set_draw_func(self.on_draw)
        click = Gtk.GestureClick()
        click.connect('pressed', self.on_click)
        self.area.add_controller(click)
        motion = Gtk.EventControllerMotion()
        motion.connect('motion', self.on_motion)
        motion.connect('leave', lambda *_: self.set_hover(None))
        self.area.add_controller(motion)
        center.append(self.area)
        center.append(Gtk.Label(
            label='Pads with an ANALOG button: turn the light on while you set them. With the light '
                  'off the pad itself makes the left stick act as the d-pad and the right stick as '
                  'the face buttons, the same as on a PlayStation.',
            wrap=True, justify=Gtk.Justification.CENTER, css_classes=['hint'], margin_start=20,
            margin_end=20))
        reset = Gtk.Button(label='Revert to Default Settings', halign=Gtk.Align.CENTER,
                           css_classes=['steam-btn', 'revert'])
        reset.connect('clicked', self.on_reset)
        center.append(reset)
        middle.append(center)
        middle.append(self.side_panel('R', 'RIGHT SIDE'))
        root.append(middle)

        footer = Gtk.Box(spacing=14, css_classes=['footer'])
        status_box = Gtk.Box(spacing=8, hexpand=True, halign=Gtk.Align.START)
        status_box.append(Gtk.Image(icon_name='input-gaming-symbolic', css_classes=['status-icon']))
        self.status = Gtk.Label(wrap=True, xalign=0, css_classes=['status'], width_chars=70,
                                max_width_chars=120)
        status_box.append(self.status)
        footer.append(status_box)
        rumble = Gtk.Button(label='Test Vibration', css_classes=['steam-btn'])
        rumble.connect('clicked', self.on_rumble)
        footer.append(rumble)
        cancel = Gtk.Button(label='Cancel', css_classes=['steam-btn'])
        cancel.connect('clicked', self.on_cancel)
        footer.append(cancel)
        self.save_button = Gtk.Button(label='Apply', css_classes=['steam-btn'], sensitive=False)
        self.save_button.connect('clicked', lambda *_: self.save())
        footer.append(self.save_button)
        ok = Gtk.Button(label='OK', css_classes=['steam-primary'])
        ok.connect('clicked', self.on_ok)
        footer.append(ok)
        root.append(footer)

        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self.on_key)
        self.add_controller(keys)
        self.connect('close-request', self.on_close)

        self.idle_status()
        self.refresh_pads()
        GLib.timeout_add(16, self.tick)
        GLib.timeout_add(700, self.check_hotplug)

    # --- layout helpers
    def side_panel(self, side, title):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, width_request=340,
                        css_classes=['panel'])
        panel.append(Gtk.Label(label=title, xalign=0, css_classes=['section-title']))
        for func in FUNCS:
            if func.side != side:
                continue
            row = Gtk.Box(spacing=4)
            button = Gtk.Button(hexpand=True, css_classes=['map-row'])
            inner = Gtk.Box(spacing=10)
            inner.append(Gtk.Label(label=func.badge, css_classes=['badge'] + BADGE_CLASSES.get(
                func.key, ['stick'] if func.is_dir or func.key.endswith('stick') else [])))
            name = Gtk.Label(label=func.label, xalign=0, css_classes=['row-name'])
            inner.append(name)
            inner.append(Gtk.Label(label=func.game, xalign=0, hexpand=True,
                                   css_classes=['game-name']))
            pill = Gtk.Label(css_classes=['pill'])
            inner.append(pill)
            button.set_child(inner)
            button.connect('clicked', lambda _b, f=func: self.start_listen(f))
            clear = Gtk.Button(icon_name='edit-clear-symbolic', tooltip_text='Clear',
                               css_classes=['flat', 'circular', 'row-clear'],
                               valign=Gtk.Align.CENTER)
            clear.connect('clicked', lambda _b, f=func: self.clear(f))
            row.append(button)
            row.append(clear)
            panel.append(row)
            self.rows[func.key] = (button, pill)
        return panel

    def idle_status(self):
        self.status.set_label('Click a function on the picture or in the lists, then press the '
                              'button you want for it on the pad. Press the pad without clicking '
                              'first to see what each button does.')

    # --- pads
    def refresh_pads(self):
        for pad in self.pads:
            pad.close()
        self.end_drag()
        # Every pad gets a new Pad object; the selection follows by path
        old = self.current.path if self.current else None
        self.current = None
        by_path, others = {}, []
        for jid in self.sdl.joysticks():
            pad = Pad(self.sdl, jid)
            if pad.path.startswith('/dev/input/'):
                by_path[pad.path] = pad
            else:
                others.append(pad)
        # Only pads the launchers can place (pad_maps.joystick_nodes) can move
        self.plug_nodes = [n for n in pad_maps.plug_order() if n in by_path]
        order = [by_path[n] for n in pad_maps.sort_players(self.plug_nodes, self.order_pending)]
        order += [p for p in by_path.values() if p not in order] + others
        self.pads = order
        for pad in order:
            if pad.guid not in self.maps:
                mapping = pad.mapping
                if not mapping:
                    # Same guess the games make; kept so it never changes
                    mapping = (f"{pad.guid},{pad.name.replace(',', ' ')},"
                               + pad_maps.guess(pad.n_axes, pad.n_hats, pad.n_buttons))
                    pad_maps.remember_guess(mapping)
                pmap = PadMap(pad_maps.parse(mapping)[2])
                self.maps[pad.guid] = pmap
                self.saved[pad.guid] = pmap.copy()
            pad.rest = pad.prev = pad.state()

        for chip in self.chips:
            self.chip_box.remove(chip)
        self.chips, self.chip_of, self.chip_x = [], {}, {}
        # Where each pad is plugged in, to tell pads of one model apart
        places = {p: pad_maps.node_identity(p.path) for p in order if self.movable(p)}
        per_socket = {}
        for ident in places.values():
            per_socket[ident['socket']] = per_socket.get(ident['socket'], 0) + 1
        for pad in order:
            chip = Gtk.ToggleButton(css_classes=['pad-chip'],
                                    group=self.chips[0] if self.chips else None)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            top = Gtk.Box(spacing=6)
            top.append(Gtk.Label(label='●', css_classes=['dot-bad' if pad.stuck else 'dot-ok']))
            player = Gtk.Label(xalign=0, hexpand=True, css_classes=['chip-player'])
            top.append(player)
            if self.movable(pad):
                top.append(Gtk.Image(icon_name='list-drag-handle-symbolic', pixel_size=14,
                                     css_classes=['chip-grip']))
                chip.set_cursor_from_name('grab')
            box.append(top)
            box.append(Gtk.Label(label=pad.name, xalign=0, css_classes=['chip-name'],
                                 ellipsize=3, max_width_chars=22))
            ident = places.get(pad)
            if ident:
                where = ident['socket'] + (f'  ·  Port {ident["sub"] + 1}'
                                           if per_socket[ident['socket']] > 1 else '')
            else:
                where = 'Driven by SDL directly'
            box.append(Gtk.Label(label=where, xalign=0, css_classes=['chip-where'],
                                 ellipsize=3, max_width_chars=26))
            chip.set_child(box)
            chip.connect('toggled', lambda c, p=pad: c.get_active() and self.pick(p))
            self.chip_box.put(chip, 0, 0)
            self.chips.append(chip)
            self.chip_of[pad] = (chip, player)
        if not order:
            empty = Gtk.Label(label='No pads connected. Plug one in and it shows up here.',
                              css_classes=['share-note'])
            self.chip_box.put(empty, 0, 0)
            self.chips.append(empty)
            self.chip_box.set_size_request(-1, -1)
            self.update_order_state()
            self.pick(None)
            return
        # Every box as wide as the widest, so they all fit the same slots
        width = max([CHIP_W] + [c.measure(Gtk.Orientation.HORIZONTAL, -1)[1] for c in self.chips])
        for chip in self.chips:
            chip.set_size_request(width, -1)
        self.slot = width + CHIP_GAP
        for i, pad in enumerate(order):
            self.chip_x[pad] = i * self.slot
            self.chip_box.move(self.chip_of[pad][0], self.chip_x[pad], 0)
        self.chip_box.set_size_request(len(order) * self.slot - CHIP_GAP, -1)
        self.relabel_chips()
        self.update_order_state()
        pick = next((p for p in order if p.path == old), next((p for p in order if not p.stuck),
                                                             order[0]))
        self.select(pick)

    def select(self, pad):
        chip = self.chip_of[pad][0]
        if chip.get_active():
            self.pick(pad)
        else:
            chip.set_active(True)

    def check_hotplug(self):
        if self.drag:  # after the drop
            return True
        if sorted(self.sdl.joysticks()) != sorted(p.jid for p in self.pads):
            self.cancel_listen()
            self.refresh_pads()
        return True

    def pick(self, pad):
        self.current = pad
        if pad:
            same = [p for p in self.pads if p.guid == pad.guid]
            self.share_note.set_label(f'Map shared by all {len(same)} pads of this type'
                                      if len(same) > 1 else '')
            self.pad_heading.set_label(pad.name)
        else:
            self.share_note.set_label('')
            self.pad_heading.set_label('No controller')
        self.update_heading()
        self.update_rows()
        self.area.queue_draw()

    def update_heading(self):
        pad = self.current
        if not pad:
            self.pad_sub.set_label('')
            return
        n = self.pads.index(pad) + 1
        self.pad_sub.set_label(f'Player {n}  ·  {pad.n_buttons} buttons  ·  {pad.n_axes} axes  ·  '
                               f'{pad.n_hats} hat' + ('s' if pad.n_hats != 1 else '')
                               + ('  ·  XInput games see players 1–4 only'
                                  if n > XINPUT_PLAYERS else ''))

    # --- player order
    def movable(self, pad):
        return pad.path in self.plug_nodes

    def movable_count(self):
        return sum(self.movable(p) for p in self.pads)

    def relabel_chips(self):
        for i, pad in enumerate(self.pads, 1):
            chip, player = self.chip_of[pad]
            player.set_label(f'PLAYER {i}')
            tips = []
            if pad.stuck:
                tips.append('Looks broken: it holds buttons down by itself, so it goes last '
                            'unless you drag it somewhere else')
            if i > XINPUT_PLAYERS:
                tips.append('Games that read pads through XInput see players 1 to 4 only')
            if self.movable(pad):
                tips.append('Drag to change the player order (or Alt+← / Alt+→)')
            else:
                tips.append('SDL drives this pad itself, so it always comes after the others')
            chip.set_tooltip_text('\n'.join(tips))
        self.update_heading()

    def move_pad(self, pad, index):
        """Put pad at index in the player order; True if it moved."""
        i = self.pads.index(pad)
        index = max(0, min(index, self.movable_count() - 1))
        if index == i:
            return False
        self.pads.insert(index, self.pads.pop(i))
        self.relabel_chips()
        return True

    def order_moved(self):
        """After a drop: what Apply saves, and the status line."""
        nodes = [p.path for p in self.pads if self.movable(p)]
        self.order_pending = pad_maps.order_entries(nodes, self.order_pending)
        self.update_order_state()
        self.update_rows()
        if self.order_changed:
            self.status.set_label('✓  Player order changed. Press Apply or OK to keep it; games '
                                  'started after that use it.')
        else:
            self.status.set_label('This is the saved player order.')

    def update_order_state(self):
        nodes = [p.path for p in self.pads if self.movable(p)]
        self.order_changed = nodes != pad_maps.sort_players(self.plug_nodes, self.order_saved)
        self.order_reset.set_visible(nodes != self.plug_nodes)
        # Wine's XInput puts different pad models in model order whatever SDL is told
        first = sum(not p.path.startswith('/dev/input/event') for p in self.pads)
        slots = pad_maps.plan_slots(nodes, first)[1] if nodes else nodes
        if slots != nodes:
            self.order_hint.set_label(
                'Wine games (PES, Blur, WWE) always put different pad models in model order, so '
                'there XInput slots 1, 2, 3… go to players ' + ', '.join(
                    f'{self.pads.index(next(p for p in self.pads if p.path == n)) + 1}'
                    for n in slots) + '. Other games follow this order.')
            self.order_hint.add_css_class('warn')
        else:
            self.order_hint.set_label(ORDER_HINT)
            self.order_hint.remove_css_class('warn')

    def on_order_reset(self, *_):
        self.end_drag()
        self.order_pending = []
        by_path = {p.path: p for p in self.pads}
        self.pads = ([by_path[n] for n in self.plug_nodes]
                     + [p for p in self.pads if not self.movable(p)])
        self.relabel_chips()
        self.order_moved()
        if self.order_changed:
            self.status.set_label('Players are back in plug-in order. Press Apply or OK to keep it.')

    def hadj(self):
        return self.chip_scroll.get_hadjustment()

    def on_strip_press(self, gesture, x, _y):
        pad = next((p for p in self.pads if self.movable(p)
                    and self.chip_x[p] <= x < self.chip_x[p] + self.slot - CHIP_GAP), None)
        if pad is None:
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return
        # x is where the mouse is in the strip, adj how far it was scrolled then
        self.drag = {'pad': pad, 'grab': x - self.chip_x[pad], 'x0': x, 'x': x,
                     'adj': self.hadj().get_value(), 'active': False}

    def on_strip_drag(self, gesture, dx, _dy):
        d = self.drag
        if not d:
            return
        d['x'], d['adj'] = d['x0'] + dx, self.hadj().get_value()
        if not d['active']:
            if abs(dx) < DRAG_START:
                return
            # From here on it is a drag, not a click on the box
            d['active'] = True
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            chip = self.chip_of[d['pad']][0]
            chip.add_css_class('dragging')
            chip.set_cursor_from_name('grabbing')
            chip.insert_before(self.chip_box, None)  # drawn over the others
        self.drag_to()

    def drag_to(self):
        """Keep the dragged box under the mouse and the others out of its way."""
        d = self.drag
        mouse = d['x'] + self.hadj().get_value() - d['adj']
        x = min(max(mouse - d['grab'], 0), (self.movable_count() - 1) * self.slot)
        self.chip_x[d['pad']] = x
        self.chip_box.move(self.chip_of[d['pad']][0], x, 0)
        self.move_pad(d['pad'], round(x / self.slot))

    def on_strip_release(self, _gesture, _dx, _dy):
        d = self.drag
        self.end_drag()
        if d and d['active']:
            self.order_moved()
            self.select(d['pad'])

    def end_drag(self):
        d, self.drag = self.drag, None
        if d and d['active'] and d['pad'] in self.chip_of:
            chip = self.chip_of[d['pad']][0]
            chip.remove_css_class('dragging')
            chip.set_cursor_from_name('grab')

    def animate_chips(self):
        """Slide every box towards its player's slot; while a box is held at
        either end of the strip, scroll it."""
        d = self.drag
        if d and d['active']:
            adj = self.hadj()
            in_view = d['x'] - d['adj']
            step = (-14 if in_view < 48 else 14 if in_view > adj.get_page_size() - 48 else 0)
            if step:
                value = adj.get_value()
                adj.set_value(min(max(value + step, adj.get_lower()),
                                  adj.get_upper() - adj.get_page_size()))
                if adj.get_value() != value:
                    self.drag_to()
        for i, pad in enumerate(self.pads):
            if d and d['active'] and pad is d['pad']:
                continue
            x, target = self.chip_x.get(pad), i * self.slot
            if x is None or x == target:
                continue
            x = target if abs(target - x) < 0.5 else x + (target - x) * 0.3
            self.chip_x[pad] = x
            self.chip_box.move(self.chip_of[pad][0], x, 0)

    def current_map(self):
        return self.maps.get(self.current.guid) if self.current else None

    # --- listening
    def start_listen(self, func):
        if not self.current:
            self.status.set_label('No pad is connected.')
            return
        self.listen = (func, time.monotonic() + LISTEN_SECONDS, self.current.state())
        self.status.set_label(f'Press the pad button you want for “{func.label}”…  (Esc to cancel)')
        self.update_rows()

    def cancel_listen(self, text=None):
        if self.listen:
            self.listen = None
            self.update_rows()
            if text:
                self.status.set_label(text)
            else:
                self.idle_status()

    def got_input(self, func, det):
        pad = self.current
        inp = to_input(func, det)
        warn = None
        if func.key.startswith('dp') and det[0] == 'axis' and det[1] < 2 and pad.n_hats:
            warn = ('The d-pad came in as the left stick',
                    'The ANALOG light is probably off. Turn it on and try again. If this pad has no '
                    'sticks at all, choose “Use as D-pad”; the left stick of pads of the same type '
                    'then stops moving.')
        elif func.is_dir and func.axis.startswith('right') and det[0] == 'button' and pad.n_axes >= 4:
            warn = ('The right stick came in as a button',
                    'The ANALOG light is probably off: the pad then sends the right stick as Triangle, '
                    'Circle, Cross and Square. Turn the light on and try again.')
        if warn:
            self.listen = None
            dialog = Adw.AlertDialog(heading=warn[0], body=warn[1])
            dialog.add_response('keep', 'Use as D-pad' if func.key.startswith('dp') else 'Keep It')
            dialog.add_response('retry', 'Try Again')
            dialog.set_response_appearance('retry', Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response('retry')
            dialog.connect('response', lambda _d, r: (self.apply(func, inp) if r == 'keep'
                                                     else self.start_listen(func)))
            dialog.present(self)
            return
        self.apply(func, inp)

    def apply(self, func, inp):
        pmap = self.current_map()
        lost = pmap.assign(func, inp)
        self.listen = None
        text = f'✓  {func.label} = {pmap.describe(func)}'
        if lost:
            text += f'  (taken off {lost_names(lost)})'
        self.status.set_label(text + '. Press Apply or OK to keep it.')
        self.update_rows()

    def clear(self, func):
        pmap = self.current_map()
        if pmap:
            pmap.clear(func)
            self.cancel_listen()
            self.update_rows()

    # --- every frame
    def tick(self):
        self.sdl.lib.SDL_PumpEvents()
        self.sdl.lib.SDL_FlushEvents(0, 0xFFFFFFFF)
        now = time.monotonic()
        states = {p.jid: p.state() for p in self.pads}
        if self.listen and self.current:
            func, deadline, base = self.listen
            st = states.get(self.current.jid)
            # A button held when listening started counts once it is let go
            base.buttons = tuple(b and s for b, s in zip(base.buttons, st.buttons))
            base.hats = tuple(b & s for b, s in zip(base.hats, st.hats))
            det = detect(base, st)
            if det:
                self.got_input(func, det)
            elif now > deadline:
                self.cancel_listen('Nothing came from the pad. Click the function again to retry.')
        else:
            # Show the pad that was just used
            for pad in self.pads:
                st = states[pad.jid]
                if (pad is not self.current and not pad.stuck
                        and detect(pad.rest, st) and not detect(pad.rest, pad.prev)):
                    self.select(pad)
                    break
        for pad in self.pads:
            pad.prev = states[pad.jid]
        self.animate_chips()
        view = self.view(states, now)
        if view != self.last_view:
            self.last_view = view
            self.area.queue_draw()
            self.update_rows()
        return True

    def view(self, states, now):
        st = states.get(self.current.jid) if self.current else None
        pmap = self.current_map()
        active = tuple(f.key for f in FUNCS if pmap and st and pmap.active(f, st))
        sticks = tuple(round(pmap.stick(a, st), 2) for a in ('leftx', 'lefty', 'rightx', 'righty')) \
            if pmap and st else ()
        pulse = round((now * 2) % 1, 1) if self.listen else 1.0
        return (active, sticks, self.listen[0].key if self.listen else None, self.hover, pulse,
                self.current.jid if self.current else None)

    def update_rows(self):
        pmap = self.current_map()
        active = self.last_view[0] if self.last_view else ()
        listen = self.listen[0].key if self.listen else None
        for key, (button, pill) in self.rows.items():
            func = BY_KEY[key]
            for css, on in (('listening', key == listen), ('active', key in active and key != listen)):
                (button.add_css_class if on else button.remove_css_class)(css)
            text = 'Press on the pad…' if key == listen else (pmap.describe(func) if pmap else '—')
            if pill.get_label() != text:
                pill.set_label(text)
            unset = pmap is not None and pmap.binding(func) is None and key != listen
            (pill.add_css_class if unset else pill.remove_css_class)('unset')
        self.save_button.set_sensitive(self.is_dirty())

    def is_dirty(self):
        return self.order_changed or any(self.maps[g].f != self.saved[g].f for g in self.maps)

    # --- drawing and mouse
    def on_draw(self, _area, cr, width, height):
        st = self.current.state() if self.current else None
        pulse = (time.monotonic() * 2) % 1 if self.listen else 1.0
        self.scale = draw_pad(cr, width, height, {
            'map': self.current_map(), 'state': st,
            'listen': self.listen[0].key if self.listen else None,
            'hover': self.hover, 'pulse': abs(pulse - 0.5) * 2})
        self.offset = ((width - W * self.scale) / 2, (height - H * self.scale) / 2)

    def key_at(self, x, y):
        px, py = (x - self.offset[0]) / self.scale, (y - self.offset[1]) / self.scale
        return next((key for key in HIT_ORDER if hit(key, px, py)), None)

    def set_hover(self, key):
        if key != self.hover:
            self.hover = key
            self.area.set_cursor(Gdk.Cursor.new_from_name('pointer') if key else None)

    def on_motion(self, _ctrl, x, y):
        self.set_hover(self.key_at(x, y))

    def on_click(self, _gesture, _n, x, y):
        key = self.key_at(x, y)
        if key:
            self.start_listen(BY_KEY[key])

    def on_key(self, _ctrl, keyval, _code, state):
        if keyval == Gdk.KEY_Escape and self.listen:
            self.cancel_listen()
            return True
        if (state & Gdk.ModifierType.ALT_MASK and keyval in (Gdk.KEY_Left, Gdk.KEY_Right)
                and self.current and self.movable(self.current) and not self.drag):
            step = 1 if keyval == Gdk.KEY_Right else -1
            if self.move_pad(self.current, self.pads.index(self.current) + step):
                self.order_moved()
            return True
        return False

    # --- buttons
    def on_rumble(self, *_):
        if self.current and self.current.joy:
            if not self.sdl.lib.SDL_RumbleJoystick(self.current.joy, 0xFFFF, 0xFFFF, 700):
                self.status.set_label('This pad does not take vibration, or its adapter does not '
                                      'pass it on.')

    def on_reset(self, *_):
        if not self.current:
            return
        import json
        guid = self.current.guid
        pad_maps.remove_learned(guid)
        env = {k: v for k, v in os.environ.items() if not k.startswith('SDL_')}
        out = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pad_maps.py'), '--json',
                              '--default'], capture_output=True, text=True, env=env).stdout
        default = next((p['mapping'] for p in json.loads(out or '[]') if p['guid'] == guid), None)
        pad = self.current
        if not default:
            default = f'{guid},{pad.name},' + pad_maps.guess(pad.n_axes, pad.n_hats, pad.n_buttons)
        pmap = PadMap(pad_maps.parse(default)[2])
        self.maps[guid] = pmap
        self.saved[guid] = pmap.copy()
        self.cancel_listen()
        self.update_rows()
        self.status.set_label('This pad type is back to its default settings.')

    def save(self):
        names = {p.guid: p.name for p in self.pads}
        for guid, pmap in self.maps.items():
            if pmap.f != self.saved[guid].f:
                pad_maps.save_learned(guid, names.get(guid, 'pad'), pmap.ordered())
                self.saved[guid] = pmap.copy()
        if self.order_changed:
            pad_maps.save_player_order(self.order_pending)
            self.order_saved = list(self.order_pending)
            self.update_order_state()
        self.cancel_listen()
        self.idle_status()
        self.update_rows()
        self.toasts.add_toast(Adw.Toast.new('Saved ✓  Every game you start from now on uses it'))
        return True

    def on_ok(self, *_):
        if self.is_dirty():
            self.save()
        self.close()

    def on_cancel(self, *_):
        self.maps = {g: m.copy() for g, m in self.saved.items()}
        self.order_pending, self.order_changed = list(self.order_saved), False
        self.close()

    def on_close(self, *_):
        if not self.is_dirty():
            self.sdl.lib.SDL_Quit()
            return False
        dialog = Adw.AlertDialog(heading='Unsaved Changes', body='Save them before closing?')
        dialog.add_response('cancel', 'Back')
        dialog.add_response('discard', 'Don’t Save')
        dialog.add_response('save', 'Save')
        dialog.set_response_appearance('save', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_response_appearance('discard', Adw.ResponseAppearance.DESTRUCTIVE)

        def done(_d, response):
            if response == 'save':
                self.save()
            if response in ('save', 'discard'):
                self.saved = {g: m.copy() for g, m in self.maps.items()}
                self.order_changed = False
                self.close()
        dialog.connect('response', done)
        dialog.present(self)
        return True


def main():
    # Read the pads exactly as the games will: from the shared map, not from
    # whatever the session or Steam put in the environment
    os.environ.pop('SDL_GAMECONTROLLERCONFIG_FILE', None)
    os.environ['SDL_GAMECONTROLLERCONFIG'] = '\n'.join(pad_maps.base_mappings())
    app = Adw.Application(application_id=APP_ID)
    app.connect('activate', lambda a: (a.get_active_window() or Window(a)).present())
    # Steam's Stop button and logout send these; close like the window's X
    try:
        gi.require_version('GLibUnix', '2.0')
        from gi.repository import GLibUnix
        signal_add = GLibUnix.signal_add
    except (ImportError, ValueError):
        signal_add = GLib.unix_signal_add
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal_add(GLib.PRIORITY_DEFAULT, sig, lambda: app.quit() or False)
    app.run([])


if __name__ == '__main__':
    main()
