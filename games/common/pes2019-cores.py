#!/usr/bin/env python3
"""Keep PES 2019's split-lock-heavy work on the E-cores (started by play-pes2019.sh).

While it starts and loads, PES 2019's copy protection (main thread) and its
FilePostProcess thread make tens of thousands of split locks a second. On this
i7-12700H one split lock stalls a P-core for ~25 us but an E-core for only
~3.7 us, and the launcher and gamemode pin the game to the P-cores. Measured to
the title screen: 78 s on P-cores, 31 s with start-up on E-cores (plus the
stack fix in pes2019-stack-fix.py). There are no split locks at the title screen.

What this does:
1. From the moment PES2019.exe appears, every thread runs on the E-cores.
2. Once FilePostProcess has done its start-up loading and been idle for 3 s
   (or after 90 s), every thread goes back to the P-cores.
3. FilePostProcess stays on the E-cores until the game exits, for later
   loading screens. gamemode re-pins all threads every few seconds, so the
   affinity is checked and set again in a loop.
"""
import os
import sys
import time

EXE = "PES2019.exe"
LOADER = "FilePostProcess"


def cpus(path, fallback):
    try:
        text = open(path).read().strip()
    except OSError:
        return fallback
    out = set()
    for part in text.split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


E_CORES = cpus("/sys/devices/cpu_atom/cpus", set())
P_CORES = cpus("/sys/devices/cpu_core/cpus", set(range(os.cpu_count())))


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def find_game():
    uid = os.getuid()
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if open(f"/proc/{pid}/comm").read().strip() == EXE and os.stat(f"/proc/{pid}").st_uid == uid:
                return int(pid)
        except OSError:
            pass
    return None


def threads(pid):
    try:
        return [int(t) for t in os.listdir(f"/proc/{pid}/task")]
    except OSError:
        return []


def comm(pid, tid):
    try:
        return open(f"/proc/{pid}/task/{tid}/comm").read().strip()
    except OSError:
        return ""


def cpu_ticks(pid, tid):
    try:
        fields = open(f"/proc/{pid}/task/{tid}/stat").read().rsplit(")", 1)[1].split()
        return int(fields[11]) + int(fields[12])
    except (OSError, IndexError, ValueError):
        return 0


def pin(tid, cores):
    try:
        if os.sched_getaffinity(tid) != cores:
            os.sched_setaffinity(tid, cores)
    except OSError:
        pass  # thread already gone


def main():
    if not E_CORES:
        log("no E-cores on this CPU, nothing to do")
        return
    deadline = time.monotonic() + 120
    pid = None
    while pid is None:
        if time.monotonic() > deadline:
            log(f"{EXE} did not start")
            return
        pid = find_game()
        if pid is None:
            time.sleep(0.05)
    start = time.monotonic()
    log(f"{EXE} is pid {pid}: start-up on E-cores {sorted(E_CORES)}")

    # 1. start-up: everything on the E-cores
    loader, last_ticks, idle_since = None, 0, None
    while os.path.exists(f"/proc/{pid}"):
        for tid in threads(pid):
            pin(tid, E_CORES)
            if loader is None and comm(pid, tid) == LOADER:
                loader = tid
        now = time.monotonic()
        if loader is not None:
            ticks = cpu_ticks(pid, loader)
            if ticks != last_ticks:
                last_ticks, idle_since = ticks, now
            elif last_ticks > 30 and now - idle_since >= 3:
                log(f"{LOADER} idle after {now - start:.1f} s")
                break
        if now - start > 90:
            log("start-up still busy after 90 s, moving on")
            break
        time.sleep(0.2)

    # 2. back to the P-cores, except the loader thread
    for tid in threads(pid):
        pin(tid, E_CORES if tid == loader else P_CORES)
    log("game threads back on the P-cores")

    # 3. keep the loader thread on the E-cores until the game exits
    while os.path.exists(f"/proc/{pid}"):
        if loader is None:
            loader = next((t for t in threads(pid) if comm(pid, t) == LOADER), None)
        if loader is not None:
            pin(loader, E_CORES)
        time.sleep(1)
    log("game exited")


if __name__ == "__main__":
    sys.exit(main())
