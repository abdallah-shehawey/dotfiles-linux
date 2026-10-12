(async () => {
    // Drag-resize one window by title, as a pointer would: A.steps size changes 16 ms apart.
    const A = __ARGS__;
    const {GLib, Meta} = imports.gi;
    const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
    const w = global.get_window_actors().map(a => a.meta_window).find(w => w.get_title() === A.title);
    if (!w)
        return JSON.stringify({error: 'no window ' + A.title});
    if (w.maximized_horizontally || w.maximized_vertically) {
        w.unmaximize(); await wait(600);
    }
    w.move_frame(true, 60, 60); await wait(200);
    const r = w.get_frame_rect();
    const steps = A.steps ?? 120;
    for (let k = 0; k < steps; k++) {
        w.move_resize_frame(true, 60, 60, 1200 + (k * 9) % 1200, 800 + (k * 5) % 550);
        await wait(16);
    }
    w.move_resize_frame(true, r.x, r.y, r.width, r.height);
    await wait(500);
    return JSON.stringify({title: A.title, steps, x11: w.get_client_type() === Meta.WindowClientType.X11});
})()
