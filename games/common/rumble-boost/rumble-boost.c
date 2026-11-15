/* Rumble boost for games under Wine.
 *
 * winebus.so dlopens libSDL2-2.0.so.0 and looks every function up in it. Put
 * this folder first in LD_LIBRARY_PATH and it finds this library instead: it
 * changes only the two rumble calls and depends on the real SDL2 by its full
 * path, so every other SDL function comes from the real library. It applies
 * to every pad the game rumbles.
 *
 * Why: PES 2021 sends short (~0.2 s) 10-60% pulses, often on the small motor
 * only, and the pantherlord driver of the Twin USB adapter scales full
 * strength down to about half of the motor's range, so most never spin up.
 *
 * Settings (environment, read once):
 *   RUMBLE_BOOST_FLOOR   percent; any non-zero strength m becomes
 *                        floor + m * (100% - floor). Default 50, 0 = no change.
 *   RUMBLE_BOOST_MIX     1 = both motors get the stronger of the two, so a
 *                        small-motor-only pulse also spins the big motor.
 *                        Default 0.
 *   RUMBLE_BOOST_MIN_MS  a pulse lasts at least this long: an early stop is
 *                        held back until then. Default 0.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#ifndef REAL_SDL2
#define REAL_SDL2 "/usr/lib64/libSDL2-2.0.so.0"
#endif

typedef int (*rumble_fn)(void *, uint16_t, uint16_t, uint32_t);

static int env_int(const char *name, int def, int lo, int hi)
{
    const char *s = getenv(name);
    int v = s && *s ? atoi(s) : def;
    return v < lo ? lo : v > hi ? hi : v;
}

static uint32_t floor_value, min_ms;
static int mix;
static pthread_once_t settings_once = PTHREAD_ONCE_INIT;

static void read_settings(void)
{
    floor_value = env_int("RUMBLE_BOOST_FLOOR", 50, 0, 100) * 0xffffu / 100;
    mix = env_int("RUMBLE_BOOST_MIX", 0, 0, 1);
    min_ms = env_int("RUMBLE_BOOST_MIN_MS", 0, 0, 5000);
}

static uint16_t boost(uint16_t m)
{
    if (!m) return 0;
    return (uint16_t)(floor_value + (uint32_t)m * (0xffffu - floor_value) / 0xffffu);
}

static rumble_fn real_fn(const char *name)
{
    static void *lib;
    if (!lib) lib = dlopen(REAL_SDL2, RTLD_LAZY | RTLD_NOLOAD);
    if (!lib) lib = dlopen(REAL_SDL2, RTLD_LAZY);
    return lib ? (rumble_fn)dlsym(lib, name) : NULL;
}

static uint64_t now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

/* Held-back stops, one slot per pad and call type. */
#define SLOTS 16
struct slot { void *joy; rumble_fn real; uint64_t started, stop_at; };
static struct slot slots[SLOTS];
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t wake = PTHREAD_COND_INITIALIZER;
static int thread_started;

static struct slot *find_slot(void *joy, rumble_fn real)
{
    struct slot *free_slot = NULL;
    for (int i = 0; i < SLOTS; i++) {
        if (slots[i].joy == joy && slots[i].real == real) return &slots[i];
        if (!slots[i].joy && !free_slot) free_slot = &slots[i];
    }
    if (free_slot) { free_slot->joy = joy; free_slot->real = real; }
    return free_slot;
}

static void *stopper(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&lock);
    for (;;) {
        uint64_t now = now_ms(), next = 0;
        for (int i = 0; i < SLOTS; i++) {
            struct slot *s = &slots[i];
            if (!s->stop_at) continue;
            if (s->stop_at <= now) {
                void *joy = s->joy; rumble_fn real = s->real;
                s->stop_at = 0;
                pthread_mutex_unlock(&lock);
                real(joy, 0, 0, 0);
                pthread_mutex_lock(&lock);
                now = now_ms();
            } else if (!next || s->stop_at < next) {
                next = s->stop_at;
            }
        }
        if (!next) {
            pthread_cond_wait(&wake, &lock);
        } else {
            struct timespec ts;
            clock_gettime(CLOCK_MONOTONIC, &ts);
            uint64_t wait = next > now ? next - now : 0;
            ts.tv_sec += wait / 1000;
            ts.tv_nsec += (wait % 1000) * 1000000;
            if (ts.tv_nsec >= 1000000000) { ts.tv_sec++; ts.tv_nsec -= 1000000000; }
            pthread_cond_timedwait(&wake, &lock, &ts);
        }
    }
    return NULL;
}

static int start_stopper(void)
{
    if (thread_started) return 1;
    pthread_condattr_t ca;
    pthread_condattr_init(&ca);
    pthread_condattr_setclock(&ca, CLOCK_MONOTONIC);
    pthread_cond_destroy(&wake);
    pthread_cond_init(&wake, &ca);
    pthread_t t;
    if (pthread_create(&t, NULL, stopper, NULL)) return 0;
    pthread_detach(t);
    return thread_started = 1;
}

static int rumble(rumble_fn real, void *joy, uint16_t a, uint16_t b, uint32_t ms)
{
    if (!real) return -1;
    pthread_once(&settings_once, read_settings);
    if (mix) a = b = a > b ? a : b;
    a = boost(a);
    b = boost(b);
    if (!min_ms) return real(joy, a, b, ms);

    pthread_mutex_lock(&lock);
    struct slot *s = find_slot(joy, real);
    if (!s || !start_stopper()) {
        pthread_mutex_unlock(&lock);
        return real(joy, a, b, ms);
    }
    uint64_t now = now_ms();
    if (a || b) {
        /* a new pulse cancels a held-back stop */
        s->started = now;
        s->stop_at = 0;
        pthread_mutex_unlock(&lock);
        return real(joy, a, b, ms && ms < min_ms ? min_ms : ms);
    }
    if (s->started && now - s->started < min_ms) {
        s->stop_at = s->started + min_ms;
        pthread_cond_signal(&wake);
        pthread_mutex_unlock(&lock);
        return 0;
    }
    s->stop_at = 0;
    pthread_mutex_unlock(&lock);
    return real(joy, 0, 0, ms);
}

int SDL_JoystickRumble(void *joy, uint16_t low, uint16_t high, uint32_t ms)
{
    static rumble_fn real;
    if (!real) real = real_fn("SDL_JoystickRumble");
    return rumble(real, joy, low, high, ms);
}

int SDL_JoystickRumbleTriggers(void *joy, uint16_t left, uint16_t right, uint32_t ms)
{
    static rumble_fn real;
    if (!real) real = real_fn("SDL_JoystickRumbleTriggers");
    return rumble(real, joy, left, right, ms);
}
