#!/usr/bin/env python3
"""A test window: fixture.py KIND TITLE W H @NEST   (KIND: gtk4 | gtk4-dynamic | gtk3-x11)"""
import math, sys, time
import gi
kind, title, w, h = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
if kind.startswith('gtk4'):
    gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, GLib
    app = Adw.Application(application_id='test.ovw.' + ''.join(c for c in title if c.isalnum()))
    def act(a):
        win = Adw.ApplicationWindow(application=a, title=title, default_width=w, default_height=h)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Adw.HeaderBar())
        area = Gtk.DrawingArea(vexpand=True)
        def draw(_a, cr, wd, ht):
            cr.set_source_rgb(0.93, 0.94, 0.96); cr.paint()
            cr.set_source_rgb(0.3, 0.3, 0.35)
            for i in range(0, ht, 22):
                cr.rectangle(20, i + 6, (wd - 40) * (0.4 + 0.5 * abs(math.sin(i))), 10)
            cr.fill()
            if kind == 'gtk4-dynamic':
                t = time.monotonic()
                cr.set_source_rgb(0.2, 0.4, 0.8)
                cr.arc(wd / 2 + 200 * math.sin(t * 3), ht / 2, 60, 0, 2 * math.pi); cr.fill()
        area.set_draw_func(draw)
        box.append(area)
        win.set_content(box); win.present()
        if kind == 'gtk4-dynamic':
            area.add_tick_callback(lambda *_: (area.queue_draw(), True)[1])
    app.connect('activate', act)
    GLib.timeout_add_seconds(7200, lambda: app.quit())
    app.run([])
else:
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    win = Gtk.Window(title=title); win.set_default_size(w, h)
    area = Gtk.DrawingArea()
    area.connect('draw', lambda _w, cr: (cr.set_source_rgb(0.97, 0.95, 0.92), cr.paint(), False)[2])
    win.add(area)
    win.connect('delete-event', lambda *a: (Gtk.main_quit(), False)[1])
    win.show_all()
    GLib.timeout_add_seconds(7200, lambda: Gtk.main_quit())
    Gtk.main()
