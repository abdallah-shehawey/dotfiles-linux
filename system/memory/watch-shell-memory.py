#!/usr/bin/env python3
"""Read-only log of the live gnome-shell's memory.

    watch-shell-memory.py [HOURS [SECONDS]]   # log, default 8 h every 5 s
    watch-shell-memory.py summary [CSV]       # trend of the newest (or given) log

One CSV row per sample, in ~/.local/state/gnome-performance/: the shell's
GPU buffers (i915 fdinfo), RSS and swap, its cgroup, system swap and zram,
the shell's CPU over the interval, and how many times the Overview has opened
(OverviewActive changes on D-Bus). Nothing is written to the shell or the
session.
"""
import csv, datetime, os, pathlib, subprocess, sys, threading, time

LOG_DIR = pathlib.Path(os.environ.get('XDG_STATE_HOME') or pathlib.Path.home() / '.local/state') / 'gnome-performance'
MB = 1 << 20
UNITS = {'': 1, 'KiB': 1 << 10, 'MiB': 1 << 20}
FIELDS = ['time', 'shell_min', 'pid', 'gem_total', 'gem_resident', 'gem_purgeable',
          'rss', 'vmswap', 'cg_current', 'cg_swap', 'cg_shmem', 'mem_available',
          'swap_used', 'zram_orig', 'zram_used', 'overview_opens', 'shell_cpu_pct']


def shell_pid():
    out = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'gnome-shell'],
                         capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else None


def drm_fd(pid):
    # The shell holds several DRM clients; the one that renders owns the most.
    best, most = None, -1
    for fd in os.listdir(f'/proc/{pid}/fdinfo'):
        try:
            total = gem(pid, fd).get('total', -1)
        except (OSError, KeyError, ValueError):
            continue
        if total > most:
            best, most = fd, total
    return best


def gem(pid, fd):
    # The kernel prints each size in the largest unit that divides it: bytes,
    # KiB or MiB. Never assume KiB.
    v = {}
    for line in open(f'/proc/{pid}/fdinfo/{fd}'):
        k, _, val = line.partition(':')
        if k.startswith('drm-') and k.endswith('-system0'):
            n, *unit = val.split()
            v[k[4:-8]] = int(n) * UNITS[unit[0] if unit else '']
    return v


def proc_status(pid):
    v = {}
    for line in open(f'/proc/{pid}/status'):
        k, _, val = line.partition(':')
        if k in ('VmRSS', 'VmSwap'):
            v[k] = int(val.split()[0]) << 10
    return v


def cgroup(pid):
    path = '/sys/fs/cgroup' + open(f'/proc/{pid}/cgroup').read().strip().split(':', 2)[2]
    stat = dict(line.split() for line in open(f'{path}/memory.stat'))
    return {'current': int(open(f'{path}/memory.current').read()),
            'swap': int(open(f'{path}/memory.swap.current').read()),
            'shmem': int(stat['shmem'])}


def meminfo():
    m = {}
    for line in open('/proc/meminfo'):
        k, _, val = line.partition(':')
        m[k] = int(val.split()[0]) << 10
    return m


def zram():
    try:
        f = open('/sys/block/zram0/mm_stat').read().split()
        return int(f[0]), int(f[2])
    except OSError:
        return 0, 0


def proc_stat(pid):
    f = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
    return int(f[11]) + int(f[12]), int(f[19])      # utime+stime, starttime (ticks)


class OverviewCounter(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.opens = 0
        self.proc = None

    def run(self):
        while True:
            self.proc = subprocess.Popen(
                ['gdbus', 'monitor', '--session', '--dest', 'org.gnome.Shell',
                 '--object-path', '/org/gnome/Shell'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            for line in self.proc.stdout:
                if "'OverviewActive'" in line and '<true>' in line:
                    self.opens += 1
            time.sleep(5)       # the shell restarted or the bus hiccuped


def log(hours, step):
    hz = os.sysconf('SC_CLK_TCK')
    btime = next(int(l.split()[1]) for l in open('/proc/stat') if l.startswith('btime'))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out = LOG_DIR / f'shell-memory-{datetime.datetime.fromtimestamp(btime):%Y%m%d-%H%M}.csv'
    new = not out.exists()
    counter = OverviewCounter()
    counter.start()
    pid = fd = None
    last = None
    end = time.monotonic() + hours * 3600
    with open(out, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(FIELDS)
        while time.monotonic() < end:
            try:
                if pid is None or not os.path.exists(f'/proc/{pid}'):
                    pid, fd, last = shell_pid(), None, None
                if pid is not None and fd is None:
                    fd = drm_fd(pid)
                if pid is None or fd is None:
                    raise FileNotFoundError
                g = gem(pid, fd)
                s = proc_status(pid)
                c = cgroup(pid)
                m = meminfo()
                zo, zu = zram()
                ticks, start = proc_stat(pid)
                now = time.monotonic()
                cpu = '' if last is None else round(100 * (ticks - last[0]) / hz / (now - last[1]), 1)
                last = (ticks, now)
                uptime = float(open('/proc/uptime').read().split()[0])
                w.writerow([datetime.datetime.now().isoformat(timespec='seconds'),
                            round((uptime - start / hz) / 60, 1), pid,
                            *(round(g.get(k, 0) / MB) for k in ('total', 'resident', 'purgeable')),
                            round(s['VmRSS'] / MB), round(s['VmSwap'] / MB),
                            round(c['current'] / MB), round(c['swap'] / MB), round(c['shmem'] / MB),
                            round(m['MemAvailable'] / MB), round((m['SwapTotal'] - m['SwapFree']) / MB),
                            round(zo / MB), round(zu / MB), counter.opens, cpu])
                fh.flush()
            except (FileNotFoundError, ProcessLookupError, KeyError, OSError):
                fd = None       # shell gone or its DRM fd moved: find it again
            time.sleep(step)
    if counter.proc:
        counter.proc.terminate()


def summary(path):
    if path is None:
        path = max(LOG_DIR.rglob('shell-memory-*.csv'), key=lambda p: p.stat().st_mtime)
    rows = list(csv.DictReader(open(path)))
    if not rows:
        print(f'{path}: no rows yet')
        return
    num = lambda r, k: float(r[k]) if r[k] not in ('', None) else 0.0
    print(f'{path}  ({len(rows)} samples, {rows[0]["time"]} .. {rows[-1]["time"]})')
    print(f'{"time":>8} {"min":>6} {"GEM":>6} {"purg":>5} {"RSS":>6} {"cgswap":>6} '
          f'{"avail":>6} {"swap":>6} {"ovw":>4} {"cpu%":>5}')
    # One line per ~5 minutes, plus the last sample.
    step = max(1, round(300 / max(1, (datetime.datetime.fromisoformat(rows[-1]['time']) -
                                      datetime.datetime.fromisoformat(rows[0]['time'])).total_seconds()
                                  / len(rows))))
    for i, r in enumerate(rows):
        if i % step and i != len(rows) - 1:
            continue
        print(f'{r["time"][11:19]:>8} {r["shell_min"]:>6} {r["gem_total"]:>6} {r["gem_purgeable"]:>5} '
              f'{r["rss"]:>6} {r["cg_swap"]:>6} {r["mem_available"]:>6} {r["swap_used"]:>6} '
              f'{r["overview_opens"]:>4} {r["shell_cpu_pct"]:>5}')
    gems = [num(r, 'gem_total') for r in rows]
    peak = max(range(len(rows)), key=lambda i: gems[i])
    cpus = [num(r, 'shell_cpu_pct') for r in rows if r['shell_cpu_pct']]
    print(f'GEM first {gems[0]:.0f} MB, last {gems[-1]:.0f} MB, min {min(gems):.0f}, '
          f'peak {gems[peak]:.0f} at {rows[peak]["time"][11:19]}; '
          f'Overview opened {rows[-1]["overview_opens"]} times; '
          f'shell cgroup swap max {max(num(r, "cg_swap") for r in rows):.0f} MB; '
          f'shell CPU mean {sum(cpus) / max(1, len(cpus)):.1f}%')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'summary':
        summary(pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        log(float(sys.argv[1]) if len(sys.argv) > 1 else 8,
            float(sys.argv[2]) if len(sys.argv) > 2 else 5)
