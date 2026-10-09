# Performance patches for third-party extensions

Five small source patches (9 Oct 2026, Codex; reviewed 10-11 Oct) that stop
extensions from working while nothing of theirs is on screen. Nothing visible
changes: same blur, same animations, same sensor values.

| Extension (version patched) | File | What the patch does |
|---|---|---|
| Blur My Shell (74) | `components/appfolders.js` | blurs a folder's popup when it first opens, instead of building every folder dialog when the app grid loads |
| App Grid Tuner (9) | `extension.js` | applies styles before the first popup and caches unchanged folder layouts, so the grid is not redrawn for nothing |
| RunCat (37) | `indicator.js` | pauses the cat's sprite timer while the panel icon is not mapped |
| System Monitor (24) | `extension.js` | stops the one-second polls while its indicator is hidden; network rates use the real elapsed time, so no spike after a pause |
| Vitals (85) | `sensors.js` | skips sensor categories nobody can see while the menu is closed; pinned sensors still update at the same interval |

The diffs are in [`patches/`](patches/). `original/` and `patched/` hold the
exact files, which is what `apply.py` checks against.

```sh
./apply.py --check     # is every patch in place?
./apply.py             # re-patch after reinstalling the same version
./apply.py --restore   # back to upstream
```

An update to one of these extensions replaces the patched file. `apply.py`
then reports it as `SKIPPED` and does not touch it: the patch has to be redone
against the new version (the `.patch` file shows what to carry over). Log out
and back in after any change; GNOME loads extension code once per session.

## Measured

Private headless GNOME Shell 50.5, 2560x1440 at 165 Hz, all 18 extensions
active, balanced power profile. Overview paint CPU, median / p95:

| | ms |
|---|---|
| extensions off | 0.854 / 1.448 |
| before (with rounded-corners rev 4) | 6.379 / 23.325 |
| after (with rounded-corners rev 5) | 1.534 / 2.296 |

Most of that drop came from the rounded-corners revision; these five mainly
remove hidden polling and unneeded app-grid work. 28 functional checks passed.
Full write-up, including the power-profile decision, in
[`validation/summary-2026-10-09.md`](validation/summary-2026-10-09.md).
`validation/run.py` needs a full copy of every extension per variant, which is
not kept here.

## Also changed that day

Just Perfection `animation` went from 5 (0.8x) to **1** (GNOME's own speed),
which is in [`../../settings/extensions.dconf`](../../settings/extensions.dconf).
