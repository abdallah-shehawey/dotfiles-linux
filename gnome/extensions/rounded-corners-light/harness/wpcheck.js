(async () => {
    const {GLib} = imports.gi;
    const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
    for (let i = 0; i < 3; i++) {
        Main.overview.show(); for (let k = 0; k < 150 && (Main.overview.animationInProgress || !Main.overview.visible); k++) await wait(20);
        await wait(200); Main.overview.hide(); for (let k = 0; k < 150 && (Main.overview.animationInProgress || Main.overview.visible); k++) await wait(20);
        await wait(200);
    }
    for (let i = 0; i < 3; i++) { imports.system.gc(); await wait(300); }
    return 'ok';
})()
