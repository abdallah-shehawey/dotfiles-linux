(async () => {
    const Gio = (await import('gi://Gio')).default;
    const GLib = (await import('gi://GLib')).default;
    const Clutter = (await import('gi://Clutter')).default;
    const Shell = (await import('gi://Shell')).default;
    const St = (await import('gi://St')).default;
    const dir = '__DIR__';
    const uuid = 'rounded-corners-light@local';
    const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
    const rect = r => ({x: r.x, y: r.y, width: r.width, height: r.height});
    const snap = async name => {
        const stream = Gio.File.new_for_path(`${dir}/shots/t6-${name}.png`).replace(null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        await new Shell.Screenshot().screenshot(false, stream);
        stream.close(null);
    };
    const results = [];
    const fail = [];
    const check = (name, ok, info = {}) => { results.push({name, ok, ...info}); if (!ok) fail.push(name); };
    const ext = () => Main.extensionManager.lookup(uuid).stateObj;
    Main.overview.hide();
    await wait(400);
    const backend = global.stage.context.get_backend();
    const pointer = backend.get_default_seat().create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
    pointer.notify_absolute_motion(GLib.get_monotonic_time(), 1280, 720);
    await wait(300);
    // A new virtual pointer starts at (0,0), the hot corner.
    Main.overview.hide();
    await wait(700);
    const titles = ['adw-one', 'csd-two', 'ssd-three'];
    const windows = Object.fromEntries(global.get_window_actors()
        .filter(a => titles.includes(a.metaWindow.get_title())).map(a => [a.metaWindow.get_title(), a.metaWindow]));
    for (const t of titles)
        windows[t].minimize();
    await wait(500);
    const kidsOf = actor => actor.get_children().map(c => c.name || c.constructor.$gtype.name);
    const modeOf = record => record.effect?._values?.[3]?.[0];

    for (const title of titles) {
        const w = windows[title];
        w.unminimize();
        w.activate(global.get_current_time());
        await wait(500);
        w.move_frame(false, 500, 260);
        await wait(400);
        let actor = w.get_compositor_private();
        let record = ext()._windows.get(actor);
        check(`${title}: tracked + enabled`, !!record?.effect?.enabled);
        check(`${title}: paints in shadow mode`, modeOf(record) === 2, {mode: modeOf(record)});
        const kids = kidsOf(actor);
        check(`${title}: grips are the top children`, kids.slice(-4).join() ===
            'light-rounded-grip-0,light-rounded-grip-1,light-rounded-grip-2,light-rounded-grip-3', {kids});
        if (!record.x11)
            check(`${title}: volume child at the bottom`, kids[0] === 'light-rounded-volume', {kids});
        check(`${title}: nothing added to window group`,
            !global.window_group.get_children().some(c => c.name?.startsWith('light-rounded-')));

        // Real input in the private compositor: drag each curved corner.
        for (const corner of [0, 1, 2, 3]) {
            const before = rect(w.get_frame_rect());
            const right = corner % 2, bottom = corner >= 2;
            const inset = 24 * (1 - Math.SQRT1_2);
            const x = before.x + (right ? before.width - inset : inset);
            const y = before.y + (bottom ? before.height - inset : inset);
            pointer.notify_absolute_motion(GLib.get_monotonic_time(), x, y);
            await wait(120);
            const picked = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y);
            const isGrip = picked === record.grips?.[corner];
            pointer.notify_button(GLib.get_monotonic_time(), 1, Clutter.ButtonState.PRESSED);
            await wait(100);
            pointer.notify_absolute_motion(GLib.get_monotonic_time(), x + (right ? -70 : 70), y + (bottom ? -40 : 40));
            await wait(200);
            pointer.notify_button(GLib.get_monotonic_time(), 1, Clutter.ButtonState.RELEASED);
            await wait(300);
            const after = rect(w.get_frame_rect());
            check(`${title}: corner ${corner} picks its grip`, isGrip, {picked: String(picked?.name ?? picked)});
            check(`${title}: corner ${corner} resizes`, after.width < before.width - 20 && after.height < before.height - 10,
                {before, after});
            w.move_resize_frame(false, 500, 260, before.width, before.height);
            await wait(350);
        }
        const frame = w.get_frame_rect();
        const interior = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, frame.x + frame.width - 27, frame.y + 24);
        check(`${title}: titlebar interior is not a grip`, !record.grips.includes(interior));
        pointer.notify_absolute_motion(GLib.get_monotonic_time(), 1280, 1300);

        for (const step of ['maximize', 'fullscreen', 'minimize']) {
            if (step === 'maximize') w.maximize();
            if (step === 'fullscreen') w.make_fullscreen();
            if (step === 'minimize') w.minimize();
            await wait(600);
            actor = w.get_compositor_private();
            record = ext()._windows.get(actor);
            if (step !== 'minimize') {
                check(`${title}: ${step}d has no extra children`, actor.get_n_children() === 1, {kids: kidsOf(actor)});
                check(`${title}: ${step}d effect disabled`, !record.effect?.enabled);
            } else {
                check(`${title}: minimized keeps its mask for the Overview`, !!record.effect?.enabled);
            }
            if (step === 'maximize') w.unmaximize();
            if (step === 'fullscreen') w.unmake_fullscreen();
            if (step === 'minimize') w.unminimize();
            await wait(700);
            record = ext()._windows.get(w.get_compositor_private());
            check(`${title}: restored from ${step}: enabled`, !!record.effect?.enabled);
            check(`${title}: restored from ${step}: shadow mode`, modeOf(record) === 2, {mode: modeOf(record)});
            check(`${title}: restored from ${step}: children back`, kidsOf(w.get_compositor_private()).length === (record.x11 ? 5 : 6));
        }
        await snap(`${title}-desktop`);

        // Overview with this window floating, then maximized.
        for (const state of ['floating', 'maximized']) {
            if (state === 'maximized') { w.maximize(); await wait(600); }
            const modes = [];
            const sig = global.stage.connect('after-paint', () => {
                const r = ext()._windows.get(w.get_compositor_private());
                modes.push({enabled: !!r.effect?.enabled, previewMode: r.effect?.geometry?.previewMode});
            });
            Main.overview.show();
            await wait(20);
            await snap(`${title}-overview-${state}-early`);
            await wait(500);
            await snap(`${title}-overview-${state}-settled`);
            global.stage.disconnect(sig);
            check(`${title}: overview ${state}: mask on every frame`, modes.length > 0 && modes.every(m => m.enabled), {frames: modes.length});
            check(`${title}: overview ${state}: preview mode`, modes.every(m => m.previewMode === (state === 'floating' ? 2 : 1)));
            Main.overview.hide();
            await wait(550);
            const r = ext()._windows.get(w.get_compositor_private());
            if (state === 'maximized') {
                check(`${title}: after overview maximized effect off`, !r.effect?.enabled);
                w.unmaximize();
                await wait(600);
            } else {
                check(`${title}: after overview floating shadow mode`, modeOf(r) === 2);
            }
        }
        w.minimize();
        await wait(500);
    }

    // Close fade in the Overview: a real client closing through its preview.
    const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE});
    launcher.setenv('GDK_BACKEND', 'wayland', true);
    const proc = launcher.spawnv(['python3', dir + '/fixture.py', 'gtk3-csd', 'fade-one']);
    await wait(1500);
    Main.overview.show();
    await wait(700);
    const preview = [...ext()._previews.keys()].find(p => p.metaWindow?.get_title() === 'fade-one');
    check('close fade: preview found', !!preview);
    if (preview) {
        preview._deleteAll();
        await wait(60);
        check('close fade: ghost fading', ext()._closeGhosts.size === 1, {ghosts: ext()._closeGhosts.size});
        await snap('close-fade');
        await wait(400);
        check('close fade: ghost cleaned up', ext()._closeGhosts.size === 0 && ext()._pendingClose.size === 0);
    }
    Main.overview.hide();
    await wait(600);
    proc.force_exit();

    // Teardown and re-enable.
    for (const t of titles) windows[t].unminimize();
    await wait(600);
    const e = ext();
    e.disable();
    const leftovers = [];
    const visit = a => {
        if (a.name?.startsWith('light-rounded-')) leftovers.push(a.name);
        if (a.get_effects?.().some(fx => fx.get_name?.()?.startsWith('light-rounded'))) leftovers.push('effect on ' + (a.name || a.constructor.$gtype.name));
        for (const c of a.get_children()) visit(c);
    };
    visit(global.stage);
    check('disable leaves nothing behind', leftovers.length === 0, {leftovers});
    e.enable();
    await wait(500);
    check('re-enable tracks windows', ext()._windows.size >= 3, {windows: ext()._windows.size});
    await wait(200);
    check('re-enable paints shadow mode', [...ext()._windows.values()].every(r => !r.window.minimized ? modeOf(r) === 2 : true));
    return JSON.stringify({checks: results.length, failed: fail, results: results.filter(r => !r.ok)});
})()
