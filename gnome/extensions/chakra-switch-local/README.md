# Local Chakra Switch changes

Updated 2026-10-07 against upstream `5bf29f3`.

Combined upstream PR: https://github.com/NarkAgni/chakra-switch/pull/6
Commit: `bf71fa6`. PR #6 and the earlier #3-#5 closed on 2026-10-07 when the fork
was deleted; nobody upstream reviewed them.

Open upstream from the recreated fork (2026-10-10):

- https://github.com/NarkAgni/chakra-switch/pull/7: the idle-container fix,
  reworked for upstream's own `PeekView`.
- https://github.com/NarkAgni/chakra-switch/pull/8: the `open-in-overview` option.

The local repo branch `codex/switcher-lifecycle-and-local-improvements` matches
the installed files (`a7b22ec`).

The installed extension and the reviewed copies here contain:

- GNOME MRU ordering, valid one-window selection, and backward initial selection.
- Keyboard-only selection: mouse movement, clicks and scrolling cannot select a card.
- A Coverflow carousel of live window previews behind the original app icon cards.
- A circular icon carousel at every window count, synchronized with the previews.
- Transparent repositioning at wraparound so cards do not sweep across the center.
- A 130 ms fade for both cards and backdrop, with safe rapid reopening.
- Unconditional preview cleanup on dismissal, even before the first animation frame.
- Cancellation of pending window-opacity transitions before restoring windows.
- Preview destruction and signal cleanup when the extension is disabled or a window closes.
- The full-screen preview container is hidden while idle (local only, 2026-10-10; not
  in `bf71fa6`). At opacity 0 it stayed mapped, and drag-and-drop picks its drop
  target with `Clutter.PickMode.ALL`, so every Overview window drag to another
  workspace (adjacent workspace or thumbnail) snapped back. Broken since the
  Coverflow peek was first installed on 2026-10-01.
- An "Open in Overview" switch (Layout > Behavior, key `open-in-overview`, as in
  PR #8). Off binds Alt+Tab in `Shell.ActionMode.NORMAL` only, as GNOME binds its
  own switcher, so nothing opens over the Overview or the app grid. It is set to
  off here. `disable()` hands GNOME's switcher back in normal mode only; upstream
  restored it with `OVERVIEW` added.

## Persistence

`apply.py` restores six reviewed snapshots:

| Installed file | Reviewed snapshot |
| --- | --- |
| `schemas/…chakra-switch.gschema.xml` | `chakra-switch.gschema.local.xml` |
| `src/ChakraSwitcher.js` | `ChakraSwitcher.local.js` |
| `src/PeekView.js` | `PeekView.coverflow.js` |
| `extension.js` | `extension.local.js` |
| `prefs.js` | `prefs.local.js` |
| `src/DiagonalBlade.js` | `DiagonalBlade.carousel.js` |

`known-sources.json` records the hashes of the exact upstream and previous local
versions that can safely be replaced. An unknown source is reported as `SKIPPED`
and left untouched. `extension.js` and `prefs.js` read `open-in-overview`, so they
are held back unless the schema snapshot is installed. The script recompiles
`gschemas.compiled` when it lacks a key. It never writes dconf preferences.

```sh
~/.local/share/chakra-switch-local/apply.py --check
~/.local/share/chakra-switch-local/apply.py
systemctl --user status chakra-switch-repatch.path
journalctl --user -u chakra-switch-repatch.service
```

The path unit watches only `metadata.json` and reapplies reviewed changes after an
extension update. An update replaces the whole directory, so that one watch is
enough, and each `PathChanged=` line costs an inotify instance (this account runs
at the 128-instance limit; six lines failed with "Too many open files" on
2026-10-11). A new GNOME session loads the saved modules.
Disabling/enabling the extension in the same session can keep cached modules.

## Verification

GNOME Shell 50.5 native-animation tests cover first-frame dismissal, interrupted
window fades, rapid reopening, window closure, teardown, and synchronized forward
and backward cycling with 1, 2, 3, 5 and 8 windows. Before the subsequent login,
real desktop verification covered four open windows and six actual Alt+Tab
sequences, including immediate Alt release. No preview, modal grab or hidden
window remained after those sequences.

The test source is in `~/My_Projects/chakra-switch/tests/nested-shell.js` and should
be run only in an isolated nested shell, as documented in that repository.

## Backups

The pre-fix local sources and persistence script are under
`backups/20261007-100053/`. Temporary live loading used `live-20261007/src/`;
subsequent logins use the normal installed extension sources.

## Installing from this repo

`./install.sh` copies the snapshots and `apply.py` to
`~/.local/share/chakra-switch-local`, installs the two units from `systemd/`
and enables the path unit. The upstream fork stays on GitHub
(`abdallah-shehawey/chakra-switch`) only because PRs #7 and #8 are opened from
it: deleting a fork closes its PRs.
