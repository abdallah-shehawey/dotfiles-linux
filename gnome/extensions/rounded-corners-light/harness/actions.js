(async () => {
    // Repeat one everyday action A.n times: overview | appgrid | maximize | dragresize | closewin
    const A = __ARGS__;
    const {GLib, Meta} = imports.gi;
    const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
    const until = async (f, ms = 5000) => { for (let t = 0; t < ms && !f(); t += 20) await wait(20); };
    const n = A.n ?? 10;
    const wins = global.get_window_actors().map(a => a.meta_window).filter(w => w.get_window_type() === Meta.WindowType.NORMAL);
    const floating = wins.filter(w => !w.maximized_horizontally && !w.fullscreen);
    const idle = () => until(() => !Main.overview.animationInProgress && !Main.overview.visible);
    for (let i = 0; i < n; i++) {
        if (A.kind === 'overview' || A.kind === 'appgrid') {
            A.kind === 'overview' ? Main.overview.show() : Main.overview.showApps();
            await until(() => Main.overview.visible && !Main.overview.animationInProgress);
            await wait(120);
            Main.overview.hide();
            await idle();
        } else if (A.kind === 'maximize') {
            const w = floating[i % floating.length];
            w.maximize(); await wait(450);
            w.unmaximize(); await wait(450);
        } else if (A.kind === 'dragresize') {
            const w = floating.find(w => w.get_title() === 'files') ?? floating[0];
            const r = w.get_frame_rect();
            for (let k = 0; k < 60; k++) {
                w.move_resize_frame(true, r.x, r.y, 900 + (k * 7) % 500, 600 + (k * 5) % 300);
                await wait(16);
            }
            w.move_resize_frame(true, r.x, r.y, r.width, r.height);
            await wait(400);
        }
    }
    await wait(500);
    return JSON.stringify({kind: A.kind, n});
})()
