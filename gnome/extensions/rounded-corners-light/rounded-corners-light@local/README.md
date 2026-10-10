# Rounded Corners Light

Local GNOME Shell 50 extension. Floating normal and dialog windows, their
Overview previews and the large workspace previews get a 24px radius; the small
workspace thumbnails get 5px, matching the native 8px selection indicator with
its 3px border. Maximized, tiled and fullscreen windows stay square on the
desktop and are rounded only inside their Overview preview.

## Revision 6 (2026-10-10)

**The shadow is GNOME's own default, drawn inside the window.** It is
libadwaita 1.9's `window.csd` box-shadow, taken from the installed library:

    focused   0 0 14px 5px rgb(0 0 0/15%), 0 0 5px 2px rgb(0 0 0/10%), 0 0 0 1px rgb(0 0 0/5%)
    backdrop  0 0 14px 5px transparent,    0 0 10px 5px rgb(0 0 0/8%), 0 0 0 1px rgb(0 0 0/5%)

with the same 200ms ease-out between the two on focus changes. The corner
shader replaces everything outside the rounded frame, the client's own shadow
included, with that profile. Because the shadow is part of the window's own
paint, it grows, fades, minimizes and closes with the window in every native
animation, and appears at the right scale in Overview previews, workspace
thumbnails and Alt+Tab clones. Revisions 3 to 5 drew it as a separate actor
beside the window; GNOME's opening animation scales the window from 1%, so
that full-size shadow appeared before the window did.

Nothing is added to `global.window_group` any more. Everything this extension
needs lives inside the window actor, and only while the window floats:

- `light-rounded-volume`: an empty child below the surfaces (Wayland only).
  Window actors report the union of their children as their paint volume, so
  it reserves room for the shadow without any per-frame code.
- `light-rounded-grip-0..3`: the curved resize grips, above the surfaces.
  They pick only the band around the visible arc (6px inside, 4px outside),
  use the matching diagonal cursor and start Mutter's own resize grab.

Maximized and fullscreen windows have no extra children, so Mutter's direct
scanout and single-surface paths are unaffected. Moves and restacking need
no work at all: only size and state changes are handled.

The corner shader reads the framebuffer geometry from Clutter's own paint
volume, so the mask is exact at 100%, 125%, 150% and 200% scale. Desktop
paints that repeat the previous one skip all uniform work.

Size changes: GNOME snapshots the old frame, waits for the client's new buffer
and animates between the two. The snapshot keeps the look the window had
(rounded when it was floating, square when it was maximized or fullscreen);
the frozen old buffer is shown intact until the new one arrives, and a window
restored from maximized keeps its rounded corners and shadow for the whole
animation.

Overview close requests capture a still image, then fade and slightly shrink it
for 180ms only after the client is actually unmanaged. Confirmation dialogs and
ignored close requests keep the live preview. Leaving the Overview or disabling
the extension clears all pending images, timers and fading actors.

Workspace backgrounds use Mutter's native rounded clipping.

## Verification

Private GNOME Shell 50.5 Wayland session, 2560x1440 at 165Hz, with libadwaita
(Wayland), GTK3 headerbar (Wayland) and Mutter-framed X11 windows, and Blur My
Shell running with the user's real settings:

- 107 functional checks: 12 real pointer drags on the curved corners, titlebar
  interior input, maximize/fullscreen/minimize and back, Overview entry with
  floating and maximized windows, the close fade, full teardown and re-enable.
- Shadow profile against the real libadwaita window, per pixel from the edge:
  default 22.0 15.4 13.5 11.1 9.5 7.9 6.6 5.4 4.6 3.8 3.2 2.7 1.9 1.4 1.1%,
  revision 6 21.6 15.7 13.5 11.5 9.5 7.9 6.6 5.4 4.6 3.8 3.2 2.7 1.9 1.4 1.1%.
- Opening animation, slowed 10x: the shadow grows with the window, exactly as
  with the extension disabled (revision 5 showed the full shadow first).
- 125%, 150% and 200% scale: exact masks (revision 5's mask assumed 100%).
- gnome-shell CPU against the extension disabled (six windows, one redrawing):
  Overview open/close +3% (revision 5: +19%), window drag +2% (+46%), idle with
  one window redrawing at 165Hz +21% (+52%).

Tests, measurements, screenshots and the revision 5 files are under
`~/.local/state/rounded-corners/revision6-*`.

## Activation

GNOME Shell imports an extension's code once per session: disabling and
enabling does not load edited code. Log out and back in once; the journal then
shows "Rounded Corners Light revision 6 loaded".

Disable with: `gnome-extensions disable rounded-corners-light@local`.
