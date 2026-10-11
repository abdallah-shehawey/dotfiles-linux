#!/usr/bin/env bash
# Installs the horizontal-tabs layout into a Zen Browser profile.
#
#   ./install.sh                 -> the profile Zen used last, under ~/.zen
#   ./install.sh "/path/to/profile"
#
# Anything already there is copied to <file>.bak-<timestamp> first; nothing
# else in the profile is touched. Quit Zen completely before running this.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

profile="${1:-}"
if [ -z "$profile" ]; then
  # Zen keeps rewriting prefs.js while it runs, so the newest one belongs to
  # the profile it is really on. The first "*Default*" by name is not that:
  # here it was an old "Default (release)-1" that Zen had not opened since
  # August, while the live one sorted second.
  newest="$(ls -t "$HOME"/.zen/*/prefs.js 2>/dev/null | head -1 || true)"
  profile="${newest%/prefs.js}"
fi
if [ -z "$profile" ] || [ ! -d "$profile" ]; then
  echo "Zen profile not found. Pass it as an argument:" >&2
  echo "  ./install.sh \"\$HOME/.zen/xxxxxxxx.Default (release)\"" >&2
  exit 1
fi

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$profile/chrome"
for f in "chrome/userChrome.css" "user.js"; do
  if [ -e "$profile/$f" ]; then
    cp "$profile/$f" "$profile/$f.bak-$stamp"
    echo "kept old $f as $f.bak-$stamp"
  fi
  cp "$here/$f" "$profile/$f"
  echo "installed $f"
done

echo
echo "Done -> $profile"
echo "Start Zen again (a full quit, not just closing the window)."
