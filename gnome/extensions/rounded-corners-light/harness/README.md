# Overview latency / GPU memory harness (12 Oct 2026)

Private headless GNOME Shell 50 sessions with the owner's real extensions and
settings (`dconf/` is a dump of /org/gnome/shell, desktop interface/background/
wm/peripherals and mutter, taken 12 Oct). Nothing reaches the live session.
/tmp is tmpfs: this copy is the one that survives a reboot.

    python3 nest.py start NAME all|none|all-minus:uuid,...   # own systemd scope
    python3 fix.py NAME                                       # 9 test windows (4 maximized, 2 X11)
    python3 ovbench.py NAME --runs 30                         # Super-tap latency, hot
    python3 ovbench.py NAME --runs 10 --cold max --rewarm 6   # after paging the shell out
    python3 leak3.py NAME overview|dragresize|maximize N      # GPU memory: Mesa cache vs JS-held
    python3 nest.py stop NAME

Env: NEST_EXT_OVERRIDE='uuid=/src/dir' swaps one extension's source,
NEST_WALLPAPER=/path.png swaps the wallpaper, NEST_SHELL_ENV='K=V ...' passes
environment to gnome-shell. ev.py NAME -e 'js' evaluates in the private shell.

Timing hooks: ov_arm.js taps Super through a Clutter virtual keyboard and
records 'showing' and the first after-paint; never connect to the stage's
'presented' signal from JS (its ClutterFrameInfo pointer cannot be converted:
one JS ERROR with a stack trace per frame, which skews every number).
GPU memory is read from /proc/PID/fdinfo (drm-total/shared/resident-system0).
After freeing buffers Mesa keeps them in its cache until the next free, so
"freed by a GC" and "freed by any later buffer free" look the same unless you
separate them as leak3.py does.
