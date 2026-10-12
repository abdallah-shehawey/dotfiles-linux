# GNOME Shell extensions

Fedora 44, GNOME Shell 50.5, Wayland. Everything here was written or patched
locally between 1 and 12 Oct 2026 (Codex first, then reviewed and fixed by
Claude). GNOME loads extension code once per session: after installing any of
it, log out and back in.

| Folder | What it is | Put it back |
|---|---|---|
| [`rounded-corners-light/`](rounded-corners-light/) | Our own extension: rounded windows, Overview previews and workspace thumbnails, with libadwaita's default shadow. Revision 7. | `./install.sh` |
| [`workspace-wrap/`](workspace-wrap/) | Our own extension: Super+Tab (next workspace) goes from the last workspace back to the first, and Shift+Super+Tab the other way. | `./install.sh` |
| [`chakra-switch-local/`](chakra-switch-local/) | Local fixes on top of Chakra Switch (Alt+Tab): MRU order, keyboard-only, Coverflow peek, Overview drags no longer swallowed, open-in-overview option. Re-applied after every update by a systemd path unit. | install the extension, then `./install.sh` |
| [`performance-patches/`](performance-patches/) | Five patches that stop Blur My Shell, App Grid Tuner, RunCat, System Monitor and Vitals from working while hidden. | `./apply.py` |

Settings for all installed extensions: [`../settings/`](../settings/).

The other extensions are stock from extensions.gnome.org:
app-grid-tuner, appindicator, background-logo, blur-my-shell, chakra-switch,
clipboard-indicator, dash-to-panel, gnome-fuzzy-app-search, gsconnect,
just-perfection, runcat, status-area-horizontal-spacing, system-monitor,
tiling-assistant, touchpad-gesture-customization, unlock-dialog-background,
vitals (list with uuids in [`../settings/enabled-extensions.txt`](../settings/enabled-extensions.txt)).

## Things that cost time once

- **Reloading code:** `gnome-extensions disable/enable` does not reload an
  extension's JS, and bumping `metadata.json`'s version makes the shell refuse
  to load it until the next login. Test in a private headless shell instead
  (both rigs in `rounded-corners-light/` do this).
- **GPU memory:** a JS reference to a texture keeps it alive until a JS GC, and
  GJS never collects because of GPU memory. Never call `get_texture()` or
  `paint_to_content()` from a paint path.
- **Overview drags that snap back:** GNOME's drag-and-drop picks its target
  with `PickMode.ALL`, so an invisible (opacity 0) full-screen actor in
  `uiGroup` eats every drop. Hide such actors (`visible = false`) while idle.
- **Idle cost** (10 Oct, live shell at ~10% of a core): Blur My Shell ~4%,
  RunCat ~2.3%, Vitals ~1%, the rest within noise.
