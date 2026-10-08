# Responsive Power Saver and Balanced-on-battery

The problem (8 Oct 2026): on **Power Saver** the laptop stuttered hard, on
battery and on the charger alike, and it did so before any extension work.
Fedora's `powersave` TuneD profile sets the CPU's energy preference to
`power`, turns turbo off and asks the firmware for `low-power`, so the cores
stay at their lowest clocks even for a click or an Overview animation.

The fix keeps everything else Power Saver does (disk, audio, Wi-Fi, USB power
saving) and changes only how the CPU answers short bursts of work:

| GNOME mode | Charger | Battery |
|---|---|---|
| Power Saver | `desktop-smooth-powersave` | `desktop-smooth-powersave` |
| Balanced | `balanced` (stock) | `desktop-smooth-balanced-battery` |
| Performance | `throughput-performance` (stock) | same |

- `desktop-smooth-powersave` = `powersave` with EPP `balance_performance`
  (stock: `power`), turbo on for short bursts (stock: off), firmware platform
  profile `balanced` (stock: `low-power`) and panel power saving 1 (stock: 3).
- `desktop-smooth-balanced-battery` = `balanced-battery` with EPP
  `balance_performance` (stock: `balance_power`).

The mapping lives in `/etc/tuned/ppd.conf` (tuned-ppd is what answers GNOME's
power menu on Fedora; power-profiles-daemon is not installed).
`ppd.conf.stock` is Fedora's file, byte-identical to the RPM's (sha256
`9c0ef6b2…`).

```sh
sudo ./install.sh              # install, keeps the selected mode
sudo ./install.sh --uninstall  # back to stock
tuned-adm active               # which TuneD profile the current mode maps to
```

## Measured and decided

- Overview open/close on the charger, four times per mode
  ([`measurements/overview-frames-per-profile.json`](measurements/overview-frames-per-profile.json)):
  median frame interval 6.04 ms in all three modes, p95 6.98-7.43 ms, none
  above 12.12 ms (one 165 Hz frame is 6.06 ms). Battery runtime was not
  measured; the snappier CPU may use more energy while you work.
- **Performance stays off.** Performance on the charger drove the CPU package
  to 97 °C (9 Oct). The owner chose Balanced all the time; an AC/battery
  auto-switching service was tried and removed. Don't add one back.
- Live state on 12 Oct: Balanced, EPP `balance_performance`.

Installed on the laptop on 8 Oct by Codex's `install.py`, which also keeps a
root-only backup in `/var/lib/desktop-smooth-tuning/backups/20261008-032828`;
this folder is the same result in a form that installs anywhere.
