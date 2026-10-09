# Rounded Corners Light

Local GNOME Shell 50 extension. Floating normal/dialog windows, window previews,
and large workspace previews use a visible radius of 24 pixels. Small workspace
thumbnails use a 5px content radius, matching the native 8px selection indicator
with its 3px border. Existing and newly created workspaces are tracked.

Desktop clipping reads the current frame and buffer at paint time. A buffer
whose allocation is still changing passes through intact. Clipping is suspended
before GNOME captures resize snapshots, through resize/minimize/unminimize, and
restored at the native animation completion. This prevents old maximized buffer
sizes from clipping the restored title bar or client contents.

Overview close-button requests capture a still image, then fade and slightly
shrink it for 180ms only after the client is actually unmanaged. Confirmation
and ignored close requests retain the live preview. Leaving Overview or disabling
the extension clears all pending images, timers and fading actors.

Revision 5 reuses each window's cached source buffer for live Overview clones.
There is no GLSL offscreen mask on the repeatedly resized window container.
A lightweight, non-offscreen clone effect selects the correct 24px stage radius
for that particular preview paint, including shared/sticky windows and attached
dialogs. This avoids allocating and rendering a new large preview texture on
each animation frame. Source masks are installed before the first preview paint,
including maximized/minimized apps, without rounding their real desktop windows.
Client damage still updates the native cached buffer: previews are not snapshots.
Unchanged movement/restacking no longer forcibly invalidates that buffer, and
the per-animation-value scan of every preview has been removed. Curved grip
pick rectangles are cached until their radius changes.
The extension does not modify Overview duration, easing, global animation speed,
or the user's Just Perfection settings.
Floating windows have a cached St rounded box-shadow outside their clipping
effect. Its opacity, visibility, position and stacking follow the window.
Revision 4 uses the same subtle shadow on desktop and Overview previews:
`0 2px 18px 1px rgba(0,0,0,0.20)`, instead of revision 3's
`0 3px 22px 5px rgba(0,0,0,0.50)`. Preview shadows are siblings outside the
corner mask; their allocation, scale, opacity and visibility follow the window
container in the same frame. Desktop shadows are no longer hidden early on the
Overview showing signal, while resize grips remain disabled in Overview.
Four transparent reactive actors pick only the curved edge band (6px inside,
4px outside), use the matching diagonal cursor and begin Mutter's native resize
grab. The interior, including titlebar buttons, is not picked by these grips.
Window destruction and extension teardown destroy both shadow and grips.
Workspace backgrounds use native Mutter rounded clipping.

Version 2 was checked in an isolated GNOME 50.5 Wayland session with X11 server
and client decorations and Wayland client decorations. All 18 resize/restore/
minimize/fullscreen cases retained all client edge markers, with a 1px tolerance
for outer antialiasing. Two consecutive close fades, a retained unclosed client,
Overview interruption and extension teardown passed. Evidence is saved under:
`~/.local/state/rounded-corners/20261008-030123/resize-close-validation`.

Revision 3 was independently tested in an isolated GNOME 50.5 Wayland compositor
on 2026-10-08: 43 checks, 12 actual curved-corner pointer drags (four corners in
each X11 SSD, X11 CSD and Wayland CSD fixture), 135 Overview paints with an active
rounded mask, positive shadow pixels on all four sides, titlebar interior input,
size/minimize/fullscreen transitions, and complete ornament teardown.
Evidence and the previous installed files are saved at:
`/home/abdallah-shehawey/.local/state/rounded-corners/revision3-v6CXbE`.
The test wrapper enables unsafe mode only in its private test compositor; it is
not part of the installed extension.

Revision 4 passed 61 checks in an isolated GNOME 50.5 session: 12 native pointer
corner drags, 136 entering-Overview paints and 99 leaving-Overview paints,
same-frame shadow geometry, positive shadow pixels on all four sides in all six
floating/maximized X11 SSD, X11 CSD and Wayland CSD previews, and full teardown.
Desktop test strips darkened by 8.50-11.95 RGB levels, versus 29.79-40.81 in
revision 3. Evidence and the previous installed files are saved at:
`/home/abdallah-shehawey/.local/state/rounded-corners/revision4-7S2MpW`.

Revision 5 passed 67 checks in an isolated GNOME 50.5 Wayland compositor on
2026-10-09: 12 native curved-corner drags, X11 SSD/CSD and Wayland CSD resize,
restore/minimize/fullscreen transitions, 135 entering and 98 leaving Overview
paints, unchanged subtle shadows on all four sides, live updates in a minimized
preview, retained close requests, successive close fades and full teardown.
Shared sticky previews, enabling/disabling inside Overview and five interrupted
open/close cycles also passed with zero leaked source-preview links.

Repeated QHD 2560x1440 / 165Hz tests with six 1600x1000 clients compared disabled,
revision 4 and revision 5 in alternating blocks. With the existing user's 0.8
animation factor, median paint CPU was 0.812 / 5.793 / 0.923ms; median paint
interval was 6.054 / 7.644 / 6.023ms and its 95th percentile 6.598 / 16.549 /
6.523ms. Opening/closing duration was approximately 203ms with both revision 5
and the extension disabled. An independent run gave 0.927 / 6.577 / 0.986ms
paint CPU with the same duration. These are private compositor paint timings,
not physical presentation FPS or a guarantee with all other enabled extensions.
Functional screenshots, tests, measurements and the previous installed files:
`/home/abdallah-shehawey/.local/state/rounded-corners/revision5-j9QjBU`.

The existing real session still has revision 4 cached. GNOME Shell 50's public
ReloadExtension method is deprecated and returns NOT_SUPPORTED. Disabling and
enabling does not reimport edited JavaScript. Log out and log back in once to
load revision 5; no session logout is performed automatically. Actual smoothness
with the user's other enabled extensions remains to be confirmed after login.
Fresh activation logs: "Rounded Corners Light revision 5 loaded".

Disable with: `gnome-extensions disable rounded-corners-light@local`.
