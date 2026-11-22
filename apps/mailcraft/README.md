# MailCraft in the desktop's own font

MailCraft draws its window in its bundled Inter on Linux. `system-font.patch` makes it use the
desktop's interface font instead (GNOME's `org.gnome.desktop.interface font-name`, found through
fontconfig), and put first, for Arabic text, the face fontconfig gives that family's Arabic, so
the window matches the rest of the desktop in English and Arabic. A font with one weight draws
the bold text in that weight too, so the window keeps one font.

```bash
./install.sh              # build for the installed MailCraft version and install
./install.sh --uninstall  # back to the packaged MailCraft
```

The build goes to `~/.local/lib/mailcraft-system-font/<version>/`, `~/.local/bin/mailcraft` picks
it, and a user copy of the desktop entry points the launcher there. After a MailCraft update the
packaged build opens (the patched one is for the old version) until `./install.sh` runs again.
