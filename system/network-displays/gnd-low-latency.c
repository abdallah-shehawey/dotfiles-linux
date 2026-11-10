/* LD_PRELOAD shim for gnome-network-displays 0.99.
 * The app hardcodes gst_pipeline_set_latency(500 ms) for openh264's sake;
 * with a hardware encoder that only adds ~450 ms of buffering.
 * Clamp it to GND_LATENCY_MS (default 100). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

void gst_pipeline_set_latency(void *pipeline, uint64_t latency)
{
    static void (*real)(void *, uint64_t);
    if (!real)
        real = (void (*)(void *, uint64_t))dlsym(RTLD_NEXT, "gst_pipeline_set_latency");
    const char *e = getenv("GND_LATENCY_MS");
    uint64_t ms = e ? strtoull(e, NULL, 10) : 100;
    uint64_t want = ms * 1000000ULL;
    if (latency > want) {
        fprintf(stderr, "gnd-low-latency: pipeline latency %llu ms -> %llu ms\n",
                (unsigned long long)(latency / 1000000ULL), (unsigned long long)ms);
        latency = want;
    }
    real(pipeline, latency);
}
