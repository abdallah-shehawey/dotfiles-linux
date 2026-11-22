# MailCraft in the desktop's own font

MailCraft draws its window in its bundled Inter on Linux. `system-font.patch` adds a setting for
it: **File › Options › General › Interface font**, either *MailCraft's own (Inter)* or *The
desktop's font*, which is the family GNOME's `org.gnome.desktop.interface font-name` names, found
through fontconfig, with the face fontconfig gives that family's Arabic put first for Arabic text.
It is also a command, `ui.interfaceFont {"value": "mailcraft"|"desktop"}`, kept in `ui.json` as
`interfaceFont`.

With the desktop's font the dark theme draws text with the rasterizer's coverage as it is.
egui's dark default (2c - c²) thickens white text: "Sent Items" in PoetsenOne had 17% more ink
per pixel of width than Pango/Cairo draws it on the desktop, and 0.6% less without it. A font
of one weight draws the bold text in that weight too, so the window keeps one font. Text sizes
are not touched.

```bash
./install.sh              # build for the installed MailCraft version and install
./install.sh --uninstall  # back to the packaged MailCraft
```

The build goes to `~/.local/lib/mailcraft-system-font/<version>/`, `~/.local/bin/mailcraft` picks
it, and a user copy of the desktop entry points the launcher there. After a MailCraft update the
packaged build opens (the patched one is for the old version) until `./install.sh` runs again.
