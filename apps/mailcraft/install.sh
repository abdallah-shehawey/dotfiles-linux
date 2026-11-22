#!/bin/bash
# Build MailCraft with system-font.patch for the installed version and make it the one that opens.
#   ./install.sh              build (or rebuild after a MailCraft update) and install
#   ./install.sh --uninstall  back to the packaged MailCraft
# MAILCRAFT_SRC (default ~/Projects/mailcraft) holds the source; CARGO_TARGET_DIR as cargo reads it.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
lib="$HOME/.local/lib/mailcraft-system-font"
launcher="$HOME/.local/bin/mailcraft"
desktop_id=io.github.billsecond.mailcraft.desktop
apps="$HOME/.local/share/applications"

if [ "${1:-}" = "--uninstall" ]; then
	rm -f "$launcher" "$apps/$desktop_id"
	rm -rf "$lib"
	update-desktop-database "$apps" 2>/dev/null || true
	echo "Removed: MailCraft opens the packaged build again."
	exit 0
fi

ver=$(rpm -q --qf '%{VERSION}' mailcraft) || { echo "MailCraft is not installed (rpm -q mailcraft)." >&2; exit 1; }
src="${MAILCRAFT_SRC:-$HOME/Projects/mailcraft}"
if [ ! -d "$src/.git" ]; then
	git clone -q --depth 1 --branch "v$ver" https://github.com/UCS-Care-Group/mailcraft.git "$src"
fi
if ! git -C "$src" apply --reverse --check "$here/system-font.patch" 2>/dev/null \
	|| [ "$(git -C "$src" describe --tags --exact-match 2>/dev/null)" != "v$ver" ]; then
	git -C "$src" fetch -q --depth 1 origin tag "v$ver"
	git -C "$src" checkout -q -f "v$ver"
	git -C "$src" apply "$here/system-font.patch" || { echo "system-font.patch no longer applies to v$ver: the packaged MailCraft stays." >&2; exit 1; }
fi
(cd "$src" && cargo build --release -p mailcraft --locked)
target="${CARGO_TARGET_DIR:-$src/target}"
rm -rf "$lib"
install -D -m 755 "$target/release/mailcraft" "$lib/$ver/mailcraft"
install -D -m 755 "$here/mailcraft-launcher.sh" "$launcher"
mkdir -p "$apps"
sed -e "s|^Exec=mailcraft|Exec=$launcher|" -e "s|^TryExec=mailcraft|TryExec=$launcher|" \
	"/usr/share/applications/$desktop_id" > "$apps/$desktop_id"
update-desktop-database "$apps" 2>/dev/null || true
echo "MailCraft $ver with the desktop font: $lib/$ver/mailcraft (quit MailCraft and open it again)."
