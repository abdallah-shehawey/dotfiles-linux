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

Transient GPU memory (added with revision 8):

    python3 fix_min.py NAME                                   # only 'files' (Wayland) and 'cad-x11'
    python3 spike.py NAME drag:files 1 3 --no-gc              # peak while one window is resized
                                                              # through 120 sizes, and how soon it is freed
    python3 stepwise.py NAME [--no-gc]                        # memory after each step of a session
    python3 ovcycle.py NAME 4                                 # in use after rounds of 10 Overview visits

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

Reading GPU memory (12 Oct 2026, revision 8):
- Use what is in use: GEM total minus purgeable. Mesa keeps freed buffers in
  its cache marked purgeable (the kernel takes them back under pressure,
  without swap) and recycles them for the next allocations, so the total alone
  hides both what was freed and what is still pinned.
- Match the fdinfo keys exactly: drm-total-stolen-system0 also ends in
  -system0. Sizes come in bytes, KiB or MiB.
- A shell holds several DRM clients; the one that renders owns the most.
- Textures a collection releases are freed at the next frame. An idle private
  shell draws none, so queue a stage redraw before concluding that a GC freed
  nothing.
- Any JS override of a paint vfunc (paint_target, paint, pre_paint) receives
  the paint node and context, and GJS keeps them, with the textures they drew,
  until their wrappers are finalized.

Each private shell with the 9 fixture windows costs 1.5-3GB of RAM, and an
X11 drag adds up to 2GB in Xwayland for a moment. On the 16GB laptop with the
owner's apps open, a few runs pushed 3.5GB of their apps (and 113MB of the
live gnome-shell) into zram. Run one shell at a time, prefer fix_min.py, and
check MemAvailable first.
