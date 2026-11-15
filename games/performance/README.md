# Performance: split locks, CPU cores, 60 Hz, GPU

> For the AI: read [../AI-PROMPT.md](../AI-PROMPT.md) first (rules). This file
> explains every performance fix in one place: what it is, why, how to check
> it, how to fix it when it breaks. Measured on this laptop (i7-12700H,
> RTX 3050 Ti, 2560x1440 165 Hz panel) in November 2026.

## What runs while a game plays

Every launcher ends in the same command (see `common/game-env.sh`, `run_game`,
and `pes-2021/play-pes2021.sh`):

```text
python3 game-session.py  taskset -c 0-11  gamemoderun  wine Game.exe
│                        │                │
│                        │                └─ GameMode: CPU governor "performance",
│                        │                   kernel.split_lock_mitigate = 0
│                        └─ only the P-cores 0-11
└─ power profile "performance" + screen 60 Hz, both undone when the game exits
```

Plus, in the launcher: NVIDIA GPU offload, NVIDIA shader cache kept, DXVK with
1 queued frame and no frame limiter. When the game closes, everything goes
back by itself: governor `powersave`, `split_lock_mitigate = 1`, power
profile as before, screen 165 Hz.

---

## 1. Split locks (the big one)

### What it is
A **split lock** is a locked (atomic) memory instruction whose data crosses two
64-byte cache lines. The CPU has to lock the whole memory bus for it. Since
Linux 6.x, Fedora runs with split-lock detection on and
`kernel.split_lock_mitigate = 1`: every split lock traps into the kernel, which
logs it and **deliberately slows the thread down** (to stop one program from
slowing the whole machine). Windows does not do this, so Windows games do
split locks freely.

### What it did to these games
- **PES 2021:** its `JobGraph` worker threads do split locks all the time →
  regular hitches during matches.
- **PES 2019:** same `JobGraph` threads during play, plus a huge burst in its
  start-up protection code and `FilePostProcess` loading thread (see section 2).
- Blur and WWE: not measured, but they get the same fix for free.

Kernel log lines look like this (thread name / pid / address):
```text
x86/split lock detection: #AC: JobGraph::worke/20609 took a split_lock trap at address: 0x14ba3dffc
```
`journalctl -k -b | grep split_lock` lists them.

### The fix: GameMode, as a member of the `gamemode` group
GameMode (`gamemoderun` in every launcher) sets
`kernel.split_lock_mitigate = 0` when a game starts and back to `1` when it
ends. It may only do that for users in the `gamemode` group.

```bash
getent group gamemode | grep -qw "$USER" && echo IN-GROUP || echo NOT-IN-GROUP
```
NOT-IN-GROUP → give the owner `sudo usermod -aG gamemode $USER`, then a
**restart** (the owner joined on 1 Nov 2026).

### How to check it works
While a game runs:
```bash
cat /proc/sys/kernel/split_lock_mitigate     # must print 0
```
With no game: `1` (normal). After the game closes: `1` again. This exact
1 → 0 → 1 cycle was verified on this laptop after a real reboot.
`games/check.sh` also checks it when a game is running.

### If it still prints 1 during a game
1. Not in the group, or not restarted since joining → `id -nG` must list `gamemode`.
2. The game was not started through its launcher (no `gamemoderun`) → start it from Steam.
3. GameMode not installed / broken → `gamemoded -t` runs GameMode's self-test.

### Do NOT
- Do not add `split_lock_detect=off` or `clearcpuid=...` to the kernel command
  line. GameMode's per-game switch is enough and keeps the protection for the
  rest of the system.
- `clearcpuid=umip` was tried for PES 2019 (15 Nov 2026) and changed nothing;
  it was removed again.
- Boot options on this laptop need `/etc/default/grub` + `sudo grub2-mkconfig -o /boot/grub2/grub.cfg`
  (`GRUB_ENABLE_BLSCFG=false`, `grubby --args` alone does nothing).

### How to measure split locks (for a new game)
```bash
# bus (split) locks per second of one process, user space:
perf stat -e cpu_core/sq_misc.bus_lock/u -p <pid> -- sleep 5
# where they come from (addresses):
perf record -e cpu_core/mem_inst_retired.lock_loads/upp -d -p <pid> -- sleep 5 && perf report
```
In PES 2019's start-up: ~40,000 per second, IPC 0.01.

---

## 2. P-cores and E-cores

The i7-12700H has 6 P-cores (logical CPUs **0-11**, fast) and 8 E-cores
(**12-19**, small). `cat /sys/devices/cpu_core/cpus` and
`cat /sys/devices/cpu_atom/cpus` print the lists.

- **Normal play: P-cores only.** `taskset -c 0-11` in every launcher. On the
  E-cores PES 2021's worker threads fall behind and the match stutters.
  GameMode also pins games to 0-11 every few seconds (its default `pin_cores`).
- **Exception, PES 2019's start-up: E-cores.** Measured: one split lock costs
  **~25 µs on a P-core but ~3.7 µs on an E-core** (capped near 40k/s, all user
  time). So `common/pes2019-cores.py` (started by `play-pes2019.sh`) moves all
  threads to the E-cores until the loading thread is idle, then back to the
  P-cores. It re-applies in a loop because GameMode re-pins every ~4 s.
  Result: title screen at ~30 s instead of 78 s. Log:
  `~/.cache/wine-games/pes2019-cores.log`. Details: [../pes-2019/README.md](../pes-2019/README.md).
- Not measured: whether PES 2021's split locks during matches would also cost
  less on E-cores. Its match threads need P-core speed, so it stays on P-cores.

Other CPU → change `0-11` in `common/game-env.sh` and `pes-2021/play-pes2021.sh`
to the new P-core list; AMD / older Intel (no `cpu_core` file) → remove
`taskset -c 0-11`.

---

## 3. 60 Hz while playing

The PES games run at 60 fps. On a 165 Hz panel that is 2.75 refreshes per
frame: frames are shown for 2 or 3 refreshes in turn, which looks like judder
even at a perfect 60 fps. `game-session.py` switches every screen to the
same resolution at the refresh rate closest to 60 Hz (through GNOME's
`org.gnome.Mutter.DisplayConfig`, method "temporary") and puts the old mode
back when the game exits, also after a SIGTERM.

Check: the screen goes 165 → 60 Hz when the game starts and back after.
The game log must not contain `panel stays at its current rate`.
Not GNOME → the game still runs, the rate just stays.

## 4. Power profile and CPU governor

- `game-session.py` holds the `performance` power profile
  (`org.freedesktop.UPower.PowerProfiles.HoldProfile`) while the game runs;
  the hold ends by itself when the process exits.
- GameMode sets the CPU governor to `performance` and, at the end, restores
  the governor it saw at start. Because the power profile was raised first, it
  would "restore" `performance`. Fix: `~/.config/gamemode.ini` with
  `defaultgov=powersave` ([../config/gamemode.ini](../config/gamemode.ini)).
- Check after a game: `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`
  → `powersave`.
- Play on the charger: on battery the laptop limits power.

## 5. GPU

- The panel is driven by the Intel iGPU; games must render on the NVIDIA card:
  `__NV_PRIME_RENDER_OFFLOAD=1`, `__VK_LAYER_NV_optimus=NVIDIA_only`,
  `__GLX_VENDOR_LIBRARY_NAME=nvidia` in the launchers.
- NVIDIA shader cache kept between runs (`__GL_SHADER_DISK_CACHE=1`,
  `__GL_SHADER_DISK_CACHE_SKIP_CLEANUP=1`): shader stutter happens on the
  first run only.
- DXVK (`common/dxvk.conf`, `common/dxvk-pes2019.conf`,
  `pes-2021/dxvk.conf`): `maxFrameLatency = 1` (pads feel direct),
  `syncInterval = 1` (vsync), `maxFrameRate = -1` (no limiter: a limiter on
  top of vsync made frame times uneven).
- Check the GPU and frame times: start the launcher with `hud`
  (`play-pes2019.sh hud`, `play-pes2021.sh hud`, `play-wwe2k-battlegrounds.sh hud`).

## 6. Wine itself

- Wine 11.20 uses `/dev/ntsync` by itself (seen as open handles on a test
  process): no esync/fsync tuning needed.
- Disk: games on ext4 (`/media/Games`). ntfs-3g was measured at ~400 MB/s
  with 64K random reads under 0.5 ms at p99, so it was never the stutter
  cause, but ext4 loads faster and has no permission/case problems.

## 7. Measuring honestly

- Baseline after all fixes (PES 2021, 1 Nov 2026, live match at 1440p):
  59.6-59.8 fps, 99.4-99.6 % of frames on time, one missed vsync every
  2.7-5 s, nothing over 50 ms during play.
- Screen captures and `nvidia-smi` during play add their own hitches, and X
  window captures go stale in full screen. Use the DXVK `hud` frame-time
  graph, or a tiny Vulkan layer that logs a timestamp in `vkQueuePresentKHR`.

## Quick checklist

```bash
getent group gamemode | grep -qw "$USER" && echo "gamemode group: yes"
cat ~/.config/gamemode.ini                          # defaultgov=powersave
cat /sys/devices/cpu_core/cpus                      # 0-11
grep -n 'taskset' /media/Games/common/game-env.sh /media/Games/eFootball-PES-2021/play-pes2021.sh
# during a game:
cat /proc/sys/kernel/split_lock_mitigate            # 0
taskset -pc $(ps -eo pid,comm | awk '$2 ~ /PES20/ {print $1; exit}')   # 0-11 (PES 2019: 12-19 for the first ~19 s)
```
