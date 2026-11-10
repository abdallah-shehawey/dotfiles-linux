# Network Displays, low latency

GNOME Network Displays 0.99 (`gnome-network-displays`, Miracast to a TV) hardcodes
`gst_pipeline_set_latency(500 ms)` in `src/wfd/wfd-media-factory.c`, because the
openh264 encoder spikes after scene changes. With the Intel hardware encoder
(`vah264enc`, ~4 ms per frame) that buffer is pure delay.

`gnd-low-latency.c` is an `LD_PRELOAD` shim that clamps the value to
`GND_LATENCY_MS` (default 100 in the shim, 20 in the launcher). `install.sh` builds
it into `~/.local/lib/gnd-low-latency/` and puts a launcher with the same name
in `~/.local/share/applications/`, which shadows the RPM's.

Measured 10 Nov 2026, laptop to a Samsung 43" FHD, stopwatch photographed on
both screens:

| sender buffer | total delay | inside the laptop (GStreamer latency tracer) |
|---|---|---|
| 500 ms (stock) | 613 ms | 450 ms |
| 100 ms | 192 ms | 49 ms |
| 20 ms | 162 ms | 16 ms, no late buffers |

The remaining ~145 ms is the TV's receive/decode/display and does not change from
the laptop side.

Other things that matter:
- the Wi-Fi card must not be joined to (or trying to join) a network on another
  channel while streaming; the P2P link then hops channels;
- encoder choice is not configurable in 0.99 (the README's
  `NETWORK_DISPLAYS_H264_ENC` is gone); NVENC is not supported.

To measure again:
`GST_TRACERS="latency(flags=pipeline)" GST_DEBUG=GST_TRACER:7 GST_DEBUG_FILE=trace.log`
