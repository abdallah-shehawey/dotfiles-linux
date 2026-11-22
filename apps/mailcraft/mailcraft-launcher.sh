#!/bin/sh
# MailCraft drawn in the desktop's own font (dotfiles-linux apps/mailcraft).
# Runs the patched build made for the MailCraft version that is installed; after an update
# that build is for an older version, so the packaged MailCraft runs until install.sh is run again.
ver=$(rpm -q --qf '%{VERSION}' mailcraft 2>/dev/null)
bin="$HOME/.local/lib/mailcraft-system-font/$ver/mailcraft"
[ -n "$ver" ] && [ -x "$bin" ] && exec "$bin" "$@"
exec /usr/bin/mailcraft "$@"
