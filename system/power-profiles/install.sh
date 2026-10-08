#!/usr/bin/env bash
# Installs the two responsive TuneD profiles and points GNOME's Power Saver
# (always) and Balanced (on battery) at them. Needs tuned + tuned-ppd
# (Fedora's default). Run with sudo:
#
#   sudo ./install.sh              install
#   sudo ./install.sh --uninstall  back to Fedora's stock mapping
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo" >&2; exit 1; }
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
conf=/etc/tuned/ppd.conf
profiles=(desktop-smooth-powersave desktop-smooth-balanced-battery)

dbus() {
  gdbus call --system --dest net.hadess.PowerProfiles --object-path /net/hadess/PowerProfiles \
    --method "org.freedesktop.DBus.Properties.$1" net.hadess.PowerProfiles ActiveProfile "${@:2}"
}
active="$(dbus Get | sed -E "s/.*'([a-z-]+)'.*/\1/")"

if [ "${1:-}" = --uninstall ]; then
  if ! cmp -s "$conf" "$here/ppd.conf"; then
    echo "$conf was edited after install; restore it by hand from ppd.conf.stock" >&2
    exit 1
  fi
  install -m 644 "$here/ppd.conf.stock" "$conf"
  for p in "${profiles[@]}"; do rm -rf "/etc/tuned/profiles/$p"; done
else
  cp -n "$conf" "$conf.bak-$(date +%Y%m%d)" 2>/dev/null || true
  for p in "${profiles[@]}"; do
    install -d -m 755 "/etc/tuned/profiles/$p"
    install -m 644 "$here/profiles/$p/tuned.conf" "/etc/tuned/profiles/$p/tuned.conf"
  done
  install -m 644 "$here/ppd.conf" "$conf"
fi

# tuned-ppd reads ppd.conf only at start; restarting it drops the selected
# mode, so put the user's choice back.
systemctl restart tuned-ppd.service
for _ in $(seq 50); do dbus Set "<'$active'>" >/dev/null 2>&1 && break; sleep 0.1; done
echo "mode: $active, TuneD profile: $(tuned-adm active | sed 's/.*: //')"
echo "CPU energy preference: $(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference)"
