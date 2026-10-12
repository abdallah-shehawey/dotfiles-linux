(() => {
    // Arm one Super tap: hooks first, then press/release after A.delay ms.
    const A = __ARGS__;
    const {GLib, Clutter} = imports.gi;
    const now = () => GLib.get_monotonic_time() / 1000;
    const stat = () => {
        const [, b] = GLib.file_get_contents('/proc/self/stat');
        const f = new TextDecoder().decode(b).split(') ')[1].split(' ');
        return {minflt: +f[7], majflt: +f[9], cpu: (+f[11] + +f[12]) * 10};
    };
    if (globalThis.__ov)
        for (const [o, id] of globalThis.__ov.ids)
            o.disconnect(id);
    const S = globalThis.__ov = {ev: {}, paints: [], ids: [], done: false};
    if (!globalThis.__ovKbd) {
        const seat = global.stage.context.get_backend().get_default_seat();
        globalThis.__ovKbd = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
    }
    const kbd = globalThis.__ovKbd;
    const conn = (o, s, cb) => S.ids.push([o, o.connect(s, cb)]);
    conn(Main.overview, 'showing', () => { S.ev.showing = now(); });
    conn(Main.overview, 'shown', () => { S.ev.shown = now(); S.ev.statShown = stat(); S.done = true; });
    conn(global.stage, 'before-update', () => S.paints.push(['bu', now()]));
    conn(global.stage, 'after-paint', () => S.paints.push(['ap', now()]));
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, A.delay ?? 200, () => {
        S.ev.press = now();
        kbd.notify_key(GLib.get_monotonic_time(), 125, Clutter.KeyState.PRESSED);
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, A.hold ?? 60, () => {
            S.ev.statRelease = stat();
            S.ev.release = now();
            kbd.notify_key(GLib.get_monotonic_time(), 125, Clutter.KeyState.RELEASED);
            return GLib.SOURCE_REMOVE;
        });
        return GLib.SOURCE_REMOVE;
    });
    return 'armed';
})()
