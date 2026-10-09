import gi
import sys

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

kind = sys.argv[1]
win = Gtk.Window(title='Rounded fixture ' + kind)
win.set_default_size(1600, 1000)
if kind != 'x11-ssd':
    win.set_titlebar(Gtk.HeaderBar(title='Rounded fixture ' + kind, show_close_button=True))
area = Gtk.DrawingArea()
win.add(area)

def draw(widget, cr):
    w, h = widget.get_allocated_width(), widget.get_allocated_height()
    for color, x, y, rw, rh in [((1, 1, 1), 0, 0, w, h), ((0, 1, 0), 0, 0, w, 32),
                              ((0, 0, 1), 0, h - 32, w, 32), ((1, 0, 0), 0, 0, 32, h),
                              ((1, 1, 0), w - 32, 0, 32, h)]:
        cr.set_source_rgb(*color)
        cr.rectangle(x, y, rw, rh)
        cr.fill()
    return False

area.connect('draw', draw)
win.connect('delete-event', lambda *args: (Gtk.main_quit(), False)[1])
win.show_all()
GLib.timeout_add_seconds(115, lambda: Gtk.main_quit())
Gtk.main()
