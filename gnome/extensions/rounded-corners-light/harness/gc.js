(async () => {
    const {GLib} = imports.gi;
    const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
    for (let i = 0; i < 3; i++) { imports.system.gc(); await wait(300); }
    return 'gc';
})()
