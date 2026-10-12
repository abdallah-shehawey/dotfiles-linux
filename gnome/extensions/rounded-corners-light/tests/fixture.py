import sys, time
kind = sys.argv[1]          # gtk3-csd | gtk3-ssd | adw
title = sys.argv[2] if len(sys.argv) > 2 else kind
import gi
if kind == 'adw':
    gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, GLib
    app = Adw.Application(application_id='test.rc.' + title.replace('-', ''))
    def act(a):
        w = Adw.ApplicationWindow(application=a, title=title, default_width=900, default_height=560)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Adw.HeaderBar())
        lab = Gtk.Label(label=title, vexpand=True); box.append(lab)
        w.set_content(box); w.present()
    app.connect('activate', act)
    GLib.timeout_add_seconds(3600, lambda: app.quit())
    app.run([])
else:
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    win = Gtk.Window(title=title)
    win.set_default_size(900, 560)
    if kind == 'gtk3-csd':
        win.set_titlebar(Gtk.HeaderBar(title=title, show_close_button=True))
    area = Gtk.DrawingArea()
    def draw(w, cr):
        cr.set_source_rgb(1, 1, 1); cr.paint(); return False
    area.connect('draw', draw)
    win.add(area)
    win.connect('delete-event', lambda *a: (Gtk.main_quit(), False)[1])
    win.show_all()
    GLib.timeout_add_seconds(3600, lambda: Gtk.main_quit())
    Gtk.main()
