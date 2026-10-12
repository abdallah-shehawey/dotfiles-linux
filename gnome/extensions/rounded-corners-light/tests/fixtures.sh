#!/bin/bash
# Launch the three fixture windows into the private shell.
cd "$(dirname "$0")"; . ./env.sh
XA=$(ls /tmp/claude-1000/rcrt/.mutter-Xwaylandauth.* 2>/dev/null | head -1)
unset DISPLAY
(GDK_BACKEND=wayland setsid python3 fixture.py adw adw-one >/dev/null 2>&1 &)
sleep 1.2
(GDK_BACKEND=wayland setsid python3 fixture.py gtk3-csd csd-two >/dev/null 2>&1 &)
sleep 1.2
(unset WAYLAND_DISPLAY; GDK_BACKEND=x11 DISPLAY=$NESTED_X11_DISPLAY XAUTHORITY=$XA setsid python3 fixture.py gtk3-ssd ssd-three >/dev/null 2>&1 &)
sleep 3
