# workspace-wrap@local

Super+Tab goes to the next workspace (see [`../../settings/`](../../settings/)),
but GNOME stops at the last one. This extension makes it go round: from the
last workspace to the first, and from the first back to the last with
Shift+Super+Tab.

It takes over GNOME's `switch-to-workspace-left` / `-right` handlers, so
every key on those bindings wraps (Super+Page Up/Down, Ctrl+Alt+Left/Right
too). Away from an edge, or with a vertical layout, it calls GNOME's own
handler unchanged. At an edge it hands that handler `switch-to-workspace-1`
or `-last`, so the popup and the Overview behave as stock. With dynamic
workspaces the empty one at the end is part of the loop.

`disable()` puts GNOME's handler back.

Install with `./install.sh`, then log out and back in.

## Tested (12 Oct 2026, GNOME 50.5)

In a private headless shell, with a virtual keyboard pressing the real keys:

- 4 static workspaces, starting on the first: Super+Tab x5 went 1, 2, 3, 0, 1.
  Shift+Super+Tab x3 went 3, 2, 1.
- Super+Page Down on the last workspace wraps to the first.
- The popup shows after a wrap, and in the Overview it wraps with no popup.
- Disabled: Super+Tab on the last workspace stays there, and on the
  second it still moves right. Enabled again: it wraps.
- Dynamic workspaces, 2 windows on 2 workspaces plus the empty one:
  Super+Tab x5 went 1, 2, 0, 1, 2.
