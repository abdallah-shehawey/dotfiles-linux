# Rounded Corners Light

Local GNOME Shell 50 extension (`rounded-corners-light@local`): floating
windows, their Overview previews and the large workspace previews get a 24px
radius, the small workspace thumbnails 5px. The shadow is libadwaita's own
default, drawn inside the same shader. What each revision changed and why is in
[`rounded-corners-light@local/README.md`](rounded-corners-light@local/README.md);
the git log of this folder holds revisions 5, 6 and 7.

```sh
./install.sh            # copies the extension into ~/.local/share/gnome-shell/extensions
                        # then log out and back in
```

## Testing without logging out

Both rigs start a private headless GNOME Shell on its own D-Bus; nothing
reaches the live session.

- `tests/` - functional checks (107 of them in `tests6.js`):
  `python3 tests/run.py rounded-corners-light@local`, then `tests/fixtures.sh`
  for the test windows and `tests/evj.py` to evaluate checks. `tests/stop.sh`
  ends it. The Wayland runtime dir is `/tmp/claude-1000/rcrt` to stay under
  the 108-byte socket limit.
- `harness/` - Overview latency and GPU memory, with the owner's real
  extensions and settings. Run `harness/snapshot-dconf.sh` once first, then
  see [`harness/README.md`](harness/README.md).
