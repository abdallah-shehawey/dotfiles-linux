# Responsive power modes that match the Fn+Q LED

Two problems, both on the Legion 5 15IAH7 (82RC) with tuned-ppd:

1. **Power Saver stuttered** (8 Oct 2026), on battery and on the charger.
   Fedora's `powersave` TuneD profile sets the CPU's energy preference to
   `power` and turns turbo off, so the cores stay at their lowest clocks even
   for a click or an Overview animation.
2. **The power mode and the Fn+Q LED disagreed** (5-7 Nov 2026). Power Saver
   from the GNOME menu left the LED white, and Fn+Q from red (performance) to
   blue (quiet) left GNOME on Performance.

## What is installed

| GNOME mode | Charger | Battery | Firmware (LED) |
|---|---|---|---|
| Power Saver | `desktop-smooth-powersave` | same | `low-power` (blue) |
| Balanced | `desktop-smooth-balanced` | `desktop-smooth-balanced-battery` | `balanced` (white) |
| Performance | `desktop-smooth-performance` | same | `performance` (red) |

- `desktop-smooth-powersave` = `powersave` with EPP `balance_performance`
  (stock: `power`), turbo on for short bursts (stock: off) and panel power
  saving 1 (stock: 3). Until 7 Nov it also kept the firmware on `balanced`;
  it now uses `low-power` so the LED is blue, as the owner asked.
- `desktop-smooth-balanced-battery` = `balanced-battery` with EPP
  `balance_performance` (stock: `balance_power`).
- `desktop-smooth-balanced` / `desktop-smooth-performance` are the stock
  `balanced` / `throughput-performance` with only the platform profile
  handling changed (below).
- `fnq-power-mode-sync` (system service) catches the one Fn+Q step the
  firmware does not announce.

The mapping lives in `/etc/tuned/ppd.conf` (tuned-ppd is what answers GNOME's
power menu on Fedora; power-profiles-daemon is not installed).
`ppd.conf.stock` is Fedora's file, byte-identical to the RPM's (sha256
`9c0ef6b2…`).

```sh
sudo ./install.sh              # install, keeps the selected mode, then self-test
sudo ./install.sh --test       # self-test only
sudo ./install.sh --uninstall  # back to stock
tuned-adm active               # which TuneD profile the current mode maps to
journalctl -u fnq-power-mode-sync   # each time it had to follow Fn+Q
```

## Why the LED and the mode disagreed (measured 7 Nov 2026)

- **Fn+Q red -> blue is not announced.** The firmware sends the GameZone
  thermal-mode WMI event for blue -> white and white -> red, and the kernel
  (`lenovo-wmi-gamezone`) passes every event on as an inotify change of
  `/sys/firmware/acpi/platform_profile`. For red -> blue the mode reads
  `low-power` within a second but no event arrives at all, so tuned-ppd,
  which only re-reads the file on that event, never switches. The kernel
  driver notifies for every mode it gets, and no "invalid thermal mode" error
  was logged, so this is the firmware. `fnq-power-mode-sync` sleeps on
  inotify, polls once a second only while the firmware is in `performance`,
  and when the firmware has changed and settled without GNOME following, sets
  the mode the way tuned-ppd itself would.
- **TuneD's `[acpi]` plugin writes twice per switch.** On every profile change
  it first rolls back to the value it saw at the previous apply (always
  `balanced`), then writes the new one, ~20 ms apart. Right after an Fn+Q
  press the second write was once lost (GNOME on Power Saver, LED white). All
  four profiles disable `[acpi]` and run
  `profiles/desktop-smooth-common/platform-profile.sh` instead, which writes
  once and only when the firmware is not already in the wanted mode, and does
  nothing on stop.

Testing traps: tuned-ppd ignores every change while *anyone* has
`/sys/firmware/acpi/platform_profile` open, so a test script that opens or
polls that file breaks Fn+Q while it runs (this misled the first attempt on
5 Nov). Watch the directory without opening the file, or read
`/sys/class/platform-profile/*/profile`. And sysfs only sends inotify events
for a file whose inode is in memory; inside a unit with `PrivateNetwork=yes`
systemd mounts its own `/sys`, so the service keeps its own copy of the class
file open and does not use `PrivateNetwork`.

## Measured and decided

- Overview open/close on the charger, four times per mode
  ([`measurements/overview-frames-per-profile.json`](measurements/overview-frames-per-profile.json),
  8 Oct, with Power Saver's firmware still on `balanced`): median frame
  interval 6.04 ms in all three modes, p95 6.98-7.43 ms, none above 12.12 ms
  (one 165 Hz frame is 6.06 ms). Battery runtime was not measured; the
  snappier CPU may use more energy while you work. Power Saver on `low-power`
  firmware has not been re-measured.
- **Performance stays off.** Performance on the charger drove the CPU package
  to 97 °C (9 Oct). The owner chose Balanced all the time; an AC/battery
  auto-switching service was tried and removed. Don't add one back.

First installed on the laptop on 8 Oct by Codex's `install.py`, which also
keeps a root-only backup in `/var/lib/desktop-smooth-tuning/backups/20261008-032828`;
this folder is the same result in a form that installs anywhere.
