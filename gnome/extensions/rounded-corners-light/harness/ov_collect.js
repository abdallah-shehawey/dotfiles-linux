(async () => {
    // Timings of the armed tap (ms after the Super release), then close the Overview.
    const {GLib} = imports.gi;
    const wait = ms => new Promise(r => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { r(); return GLib.SOURCE_REMOVE; }));
    const S = globalThis.__ov;
    for (let i = 0; i < 200 && !S.done; i++)
        await wait(50);
    for (const [o, id] of S.ids.splice(0))
        o.disconnect(id);
    const r = S.ev.release;
    const rel = t => t === undefined ? null : +(t - r).toFixed(2);
    const after = S.paints.filter(p => S.ev.showing !== undefined && p[1] >= S.ev.showing);
    const firstAp = after.find(p => p[0] === 'ap');
    const end = S.ev.shown ?? Infinity;
    const aps = after.filter(p => p[0] === 'ap' && p[1] <= end).map(p => p[1]);
    const gaps = aps.slice(1).map((t, i) => +(t - aps[i]).toFixed(2));
    const st0 = S.ev.statRelease, st1 = S.ev.statShown;
    const res = {showing: rel(S.ev.showing), firstPaint: rel(firstAp?.[1]), shown: rel(S.ev.shown),
        frames: aps.length, maxGap: gaps.length ? Math.max(...gaps) : null,
        majflt: st1 && st0 ? st1.majflt - st0.majflt : null, cpu: st1 && st0 ? st1.cpu - st0.cpu : null};
    Main.overview.hide();
    for (let i = 0; i < 100 && (Main.overview.visible || Main.overview.animationInProgress); i++)
        await wait(50);
    await wait(200);
    return JSON.stringify(res);
})()
