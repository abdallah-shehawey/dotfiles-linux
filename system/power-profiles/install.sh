#!/usr/bin/env bash
# Installs the responsive TuneD profiles, points GNOME's power modes at them,
# and installs fnq-power-mode-sync (follows the Fn+Q step the Legion firmware
# does not announce). Needs tuned + tuned-ppd (Fedora's default). Run with sudo:
#
#   sudo ./install.sh              install, then run the self-test
#   sudo ./install.sh --test       only run the self-test
#   sudo ./install.sh --uninstall  back to Fedora's stock mapping
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo" >&2; exit 1; }
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
conf=/etc/tuned/ppd.conf
profiles=(desktop-smooth-common desktop-smooth-powersave desktop-smooth-balanced
          desktop-smooth-balanced-battery desktop-smooth-performance)
sync_bin=/usr/local/sbin/fnq-power-mode-sync
sync_unit=/etc/systemd/system/fnq-power-mode-sync.service
pp=/sys/firmware/acpi/platform_profile

dbus() {
  gdbus call --system --dest net.hadess.PowerProfiles --object-path /net/hadess/PowerProfiles \
    --method "org.freedesktop.DBus.Properties.$1" net.hadess.PowerProfiles ActiveProfile "${@:2}"
}
mode() { dbus Get | sed -E "s/.*'([a-z-]+)'.*/\1/"; }
set_mode() { for _ in $(seq 50); do dbus Set "<'$1'>" >/dev/null 2>&1 && return 0; sleep 0.1; done; return 1; }
hw() { cat "$pp" 2>/dev/null || echo none; }

self_test() {
  [ -f "$pp" ] || { echo "self-test: no platform profile here, skipped"; return 0; }
  local orig fail=0 since
  orig="$(mode)"
  check() { # $1 what, $2 got, $3 want
    if [ "$2" = "$3" ]; then echo "  ok   $1: $2"; else echo "  FAIL $1: $2 (want $3)"; fail=1; fi
  }
  echo "self-test (mode now $orig):"
  for m in performance power-saver balanced; do
    set_mode "$m"; sleep 2
    case $m in power-saver) want=low-power ;; *) want=$m ;; esac
    check "GNOME $m -> firmware" "$(hw)" "$want"
  done
  # A firmware change tuned-ppd does not hear about, like Fn+Q red -> blue:
  # tuned-ppd ignores writes, so only fnq-power-mode-sync can follow this one.
  set_mode performance; sleep 2
  since="$(date '+%Y-%m-%d %H:%M:%S')"
  printf 'low-power\n' > "$pp"; sleep 3
  check "unannounced performance -> low-power, GNOME" "$(mode)" power-saver
  check "  firmware stays" "$(hw)" low-power
  journalctl -u fnq-power-mode-sync --since "$since" --no-pager -o cat | grep -q 'switching to power-saver' \
    && echo "  ok   fnq-power-mode-sync did it" || { echo "  FAIL fnq-power-mode-sync did not log the switch"; fail=1; }
  set_mode "$orig"; sleep 2
  echo "  back to $orig, firmware $(hw)"
  if grep -q 'platform-profile.sh' /var/log/tuned/tuned.log && ! grep -q 'platform-profile.sh.*\(rror\|denied\)' /var/log/tuned/tuned.log; then
    echo "  ok   TuneD runs platform-profile.sh"
  else
    echo "  FAIL TuneD did not run platform-profile.sh cleanly (see /var/log/tuned/tuned.log)"; fail=1
  fi
  return $fail
}

if [ "${1:-}" = --test ]; then self_test; exit $?; fi

active="$(mode)"

if [ "${1:-}" = --uninstall ]; then
  if ! cmp -s "$conf" "$here/ppd.conf"; then
    echo "$conf was edited after install; restore it by hand from ppd.conf.stock" >&2
    exit 1
  fi
  systemctl disable --now fnq-power-mode-sync.service 2>/dev/null || true
  rm -f "$sync_bin" "$sync_unit"
  systemctl daemon-reload
  install -m 644 "$here/ppd.conf.stock" "$conf"
  for p in "${profiles[@]}"; do rm -rf "/etc/tuned/profiles/$p"; done
else
  cp -n "$conf" "$conf.bak-$(date +%Y%m%d)" 2>/dev/null || true
  for p in "${profiles[@]}"; do
    install -d -m 755 "/etc/tuned/profiles/$p"
    for f in "$here/profiles/$p"/*; do
      case $f in *.sh) m=755 ;; *) m=644 ;; esac
      install -m $m "$f" "/etc/tuned/profiles/$p/"
    done
  done
  install -m 644 "$here/ppd.conf" "$conf"
  install -m 755 "$here/fnq-power-mode-sync" "$sync_bin"
  install -m 644 "$here/fnq-power-mode-sync.service" "$sync_unit"
  command -v restorecon >/dev/null && restorecon -R /etc/tuned/profiles "$conf" "$sync_bin" "$sync_unit"
  systemctl daemon-reload
fi

# tuned-ppd reads ppd.conf only at start; restarting it drops the selected
# mode, so put the user's choice back.
systemctl restart tuned-ppd.service
set_mode "$active" || true
# If the TuneD profile in use is one of ours it is not reloaded by the switch
# above; reapply it so the new file takes effect.
cur="$(tuned-adm active | sed 's/.*: //')"
case " ${profiles[*]} " in *" $cur "*) tuned-adm profile "$cur" ;; esac
# restart, not just enable --now: a running copy would keep the old code
[ "${1:-}" = --uninstall ] || { systemctl enable fnq-power-mode-sync.service; systemctl restart fnq-power-mode-sync.service; }
echo "mode: $(mode), TuneD profile: $(tuned-adm active | sed 's/.*: //'), firmware: $(hw)"
echo "CPU energy preference: $(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference)"
[ "${1:-}" = --uninstall ] || self_test
