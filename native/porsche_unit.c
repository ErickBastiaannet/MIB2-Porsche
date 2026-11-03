#define _POSIX_C_SOURCE 200809L
#include "porsche_sha256.h"
#include "porsche_geometry.h"
#include "porsche_session.h"
#include "porsche_nvss.h"
#include "porsche_wire.h"
#include "porsche_dm.h"
#include "porsche_jar.h"
#ifdef CW_YUV_RENDERER
#include "porsche_yuv_capture.h"
#include "porsche_yuv_gl.h"
#include "porsche_window_loader.h"
#include "porsche_pixels.h"
#include "porsche_frame_quality.h"
#endif
#include "altscreen_frame_protocol.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <dlfcn.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <errno.h>

#ifndef CW_RUNTIME
#define CW_RUNTIME "/ramdisk"
#endif
#define GEOMETRY CW_RUNTIME "/cw-carplay-geometry.v3"
#define CONTEXT CW_RUNTIME "/cw-carplay-context.v1"
#define READY CW_RUNTIME "/cw-carplay-ready.v1"
#define VIDEO_READY CW_RUNTIME "/cw-carplay-video.v1"
#define SOURCE_READY CW_RUNTIME "/cw-porsche-altstream.ready"
#define RING CW_RUNTIME "/cw-porsche-alt-ring.bin"
#define IDR CW_RUNTIME "/cw-porsche-alt-force-idr.request"
#define LOCK CW_RUNTIME "/cw-porsche-supervisor.pid"
#define CONTEXT_OWNER CW_RUNTIME "/cw-porsche-context-owner.v1"
#define LAYER 78U
static volatile sig_atomic_t stopped;
static void on_signal(int number) {
    (void)number;
    stopped = 1;
}
static void pause_ms(unsigned ms) {
    struct timespec t = {(time_t)(ms / 1000), (long)(ms % 1000) * 1000000};
    nanosleep(&t, NULL);
}
static uint32_t now_seconds(void) {
    time_t n = time(NULL);
    return n == (time_t)-1 ? 0 : (uint32_t)n;
}
static void request_idr(void) {
    int fd = open(IDR, O_CREAT | O_WRONLY | O_TRUNC, 0600);
    if (fd >= 0)
        close(fd);
}
static uint32_t next_sequence(uint32_t n) { return n == UINT32_MAX ? 1 : n + 1; }

static int source_ready(pid_t owner) {
    long pid = 0;
    unsigned long timestamp = 0;
    uint32_t now = now_seconds();
    FILE *file = fopen(SOURCE_READY, "rb");
    int ok;
    if (!file)
        return 0;
    ok = fscanf(file, "%ld %lu", &pid, &timestamp) == 2;
    fclose(file);
    return ok && pid == (long)owner && timestamp <= now && now - timestamp <= 3;
}
static int verified_file(const char *path, const char *expected) {
    char digest[65];
    return cw_sha256_file(path, digest) && !strcmp(digest, expected);
}
static int firmware_check(void) {
    unsigned backend;
    if (!cw_dm_backend_id(1, &backend) || backend != 4) {
        fputs("ERROR: Display configuration differs from the verified MU1417 profile\n", stderr);
        return 0;
    }
    if (!verified_file("/ifs/lsd.jxe",
                       "a7c5e723904be98a349b5fcdb9e04846f1306b64ef1ef538d9ee08502864c04d")) {
        fputs("ERROR: HMI does not match the recovered Porsche MU1417 firmware\n", stderr);
        return 0;
    }
    if (!verified_file("/eso/lib/libairplay.so",
                       "816f1fa8b333ca091676cea65d405f36adb82ceee5119eb6f8f99538678b527a")) {
        fputs("ERROR: AirPlay library differs from the verified Porsche firmware\n", stderr);
        return 0;
    }
    if (!verified_file("/mnt/app/armle/lib/libnvss_video.so",
                       "b57f3eb1697c6846d06a1c546ad8b06834c630ccfac88c6ea6787dd5ccc41475")) {
        fputs("ERROR: Video decoder library differs from the verified Porsche firmware\n", stderr);
        return 0;
    }
    puts("FIRMWARE_VERIFIED K5137 MU1417");
    return 1;
}

/* Native geometry replaces all Java/HMI boot overrides. */
static int publish_geometry(const char *root, cw_display *display) {
    static uint32_t generation, old_width, old_height;
    char report[16384];
    uint32_t values[12];
    if (!cw_dm_query(root, "gs", report, sizeof(report)) || !cw_dm_display(report, display) ||
        display->width > 1920 || display->height > 1080)
        return 0;
    if (!generation || display->width != old_width || display->height != old_height) {
        generation = next_sequence(generation);
        old_width = display->width;
        old_height = display->height;
    }
    values[0] = generation;
    values[1] = now_seconds();
    values[2] = 1;
    values[3] = cw_map_context((unsigned)display->context) || display->context == 70;
    values[4] = 0;
    values[5] = 3; /* Native secondary LVDS terminal. */
    values[6] = display->width;
    values[7] = display->height;
    values[8] = 0;
    values[9] = 0;
    values[10] = display->width;
    values[11] = display->height;
    return cw_wire_write(GEOMETRY, "CWCP3", values, 12);
}

static int prepare_context(const char *root) {
    char report[65536];
    uint32_t owner[4];
    int state;
    if (!cw_dm_query(root, "gc", report, sizeof(report)))
        return 0;
    state = cw_dm_context_state(report, 70, LAYER);
#ifdef CW_YUV_RENDERER
    {
        static const unsigned layers[] = {78, 33};
        if (cw_dm_context_layers(report, 70, layers, 2) == 1)
            state = 1;
    }
#endif
    if (state == 0) {
#ifndef CW_YUV_RENDERER
        if (!cw_dm_declare(root, 70, LAYER))
            return 0;
#endif
    } else if (state == 1) {
        if (!cw_wire_read(CONTEXT_OWNER, "CWCO1", owner, 4) || owner[0] <= 1 || owner[2] != 70 ||
            owner[3] != LAYER)
            return 0;
        if (owner[0] != (uint32_t)getpid() && (kill((pid_t)owner[0], 0) == 0 || errno != ESRCH))
            return 0;
    } else
        return 0;
    owner[0] = (uint32_t)getpid();
    owner[1] = now_seconds();
    owner[2] = 70;
    owner[3] = LAYER;
    return cw_wire_write(CONTEXT_OWNER, "CWCO1", owner, 4);
}

/* The child owns a separate decoder layer. Only emergency recovery may change
 * the context if its supervising parent has died unexpectedly. */
static void restore_context(const char *root, unsigned original);
#ifdef CW_YUV_RENDERER
static int source_worker(const cw_geometry *geometry, const char *root, unsigned original,
                         pid_t parent, cw_pixels *channel) {
#else
static int decode_worker(const cw_geometry *geometry, const char *root, unsigned original,
                         pid_t parent) {
#endif
    cw_nvss sink;
    cw_nvss_api api;
    void *library = NULL;
    AltFrameRing *ring = NULL;
    uint8_t *message = NULL, *config = NULL;
    size_t config_size = 0;
    uint32_t generation = 0, sequence = 1;
    uint64_t last_data = cw_monotonic_ms();
    int fd = -1, result = 1;
    struct stat st;
#ifdef CW_YUV_RENDERER
    cw_yuv_mailbox pixels;
    uint8_t *image = NULL;
    uint64_t image_sequence = 0, last_pixels = cw_monotonic_ms();
    memset(&pixels, 0, sizeof(pixels));
#endif
    memset(&sink, 0, sizeof(sink));
    unlink(VIDEO_READY);
#ifdef CW_YUV_RENDERER
    (void)root;
    (void)original;
    if (!cw_yuv_open(&pixels, geometry->width, geometry->height) ||
        !cw_yuv_capture_open_parser(&pixels, "/mnt/app/armle/usr/lib/libnvmedia.so")) {
        fputs("CARPLAY_SOURCE_FAILED stage=yuv-parser-open\n", stderr);
        goto done;
    }
    image = malloc(pixels.size);
    if (!image) {
        fputs("CARPLAY_SOURCE_FAILED stage=image-allocation\n", stderr);
        goto done;
    }
#endif
    library = dlopen("libnvss_video.so", RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        fputs("CARPLAY_SOURCE_FAILED stage=nvss-dlopen\n", stderr);
        goto done;
    }
    api.open = (int32_t (*)(void **, const cw_nvss_open *))dlsym(library, "NvSSVideoOpen");
    api.configure =
        (int32_t (*)(void *, const cw_nvss_stream *))dlsym(library, "NvSSVideoStreamConfigure");
    api.decode =
        (int32_t (*)(void *, const cw_nvss_unit *, uint32_t))dlsym(library, "NvSSVideoDecode");
    api.close = (int32_t (*)(void *))dlsym(library, "NvSSVideoClose");
    if (!api.open || !api.configure || !api.decode || !api.close) {
        fputs("CARPLAY_SOURCE_FAILED stage=nvss-symbols\n", stderr);
        goto done;
    }
    fd = open(RING, O_RDONLY);
    if (fd < 0 || fstat(fd, &st) || st.st_size != (off_t)sizeof(*ring)) {
        fprintf(stderr, "CARPLAY_SOURCE_FAILED stage=ring-open errno=%d size=%ld expected=%lu\n",
                errno, fd >= 0 ? (long)st.st_size : -1L, (unsigned long)sizeof(*ring));
        goto done;
    }
    ring = mmap(NULL, sizeof(*ring), PROT_READ, MAP_SHARED, fd, 0);
    if (ring == MAP_FAILED) {
        ring = NULL;
        goto done;
    }
    message = malloc(ALT_FRAME_RING_SLOT_DATA_MAX);
    config = malloc(ALT_FRAME_RING_SLOT_DATA_MAX);
    if (!message || !config) {
        fputs("CARPLAY_SOURCE_FAILED stage=ring-buffers\n", stderr);
        goto done;
    }
    request_idr();
    while (!stopped && getppid() == parent) {
        uint32_t available;
        cw_geometry current;
        if (!cw_geometry_read(GEOMETRY, now_seconds(), &current) || !current.active ||
            current.width != geometry->width || current.height != geometry->height)
            break;
        if (ring->magic != ALT_FRAME_RING_MAGIC || ring->version != ALT_FRAME_RING_VERSION) {
            pause_ms(10);
            continue;
        }
        __sync_synchronize();
        if (generation != ring->generation) {
            generation = ring->generation;
            cw_nvss_stop(&sink);
#ifdef CW_YUV_RENDERER
            (void)cw_yuv_take(&pixels, image, pixels.size, &image_sequence);
            last_pixels = cw_monotonic_ms();
#endif
            config_size = 0;
            unlink(VIDEO_READY);
            available = ring->write_sequence;
            sequence = available > 63 ? available - 63 : 1;
            request_idr();
        }
        available = ring->write_sequence;
        if (!available) {
            pause_ms(5);
            continue;
        }
        if ((uint32_t)(available - sequence) >= ALT_FRAME_RING_SLOT_COUNT &&
            sequence != next_sequence(available)) {
            sequence = available > 63 ? available - 63 : 1;
            cw_nvss_stop(&sink);
            config_size = 0;
            unlink(VIDEO_READY);
            request_idr();
        }
        while (sequence != next_sequence(available) && !stopped) {
            AltFrameRingSlot *slot = &ring->slots[(sequence - 1) % ALT_FRAME_RING_SLOT_COUNT];
            uint32_t committed = slot->committed_sequence, type, size;
            if (committed != sequence)
                break;
            __sync_synchronize();
            type = slot->type;
            size = slot->size;
            if (!size || size > ALT_FRAME_RING_SLOT_DATA_MAX)
                goto done;
            memcpy(message, slot->data, size);
            __sync_synchronize();
            if (slot->committed_sequence != sequence || ring->generation != generation)
                break;
            last_data = cw_monotonic_ms();
            if (type == ALT_FRAME_TYPE_CONFIG) {
                if (config_size != size || memcmp(config, message, size)) {
                    cw_nvss_stop(&sink);
                    unlink(VIDEO_READY);
#ifdef CW_YUV_RENDERER
                    (void)cw_yuv_take(&pixels, image, pixels.size, &image_sequence);
                    last_pixels = cw_monotonic_ms();
                    if (!cw_nvss_start_hidden(&sink, &api, geometry->width, geometry->height, 79, 0,
                                              message, size)) {
                        fputs("CARPLAY_SOURCE_FAILED stage=nvss-start-hidden\n", stderr);
                        goto done;
                    }
#else
                    if (!cw_nvss_start(&sink, &api, geometry->width, geometry->height, LAYER, 0,
                                       message, size))
                        goto done;
#endif
                    memcpy(config, message, size);
                    config_size = size;
                }
            } else if (type == ALT_FRAME_TYPE_VIDEO && sink.handle) {
                int accepted = cw_nvss_frame(&sink, message, size, 0);
                if (accepted < 0) {
                    fputs("CARPLAY_SOURCE_FAILED stage=nvss-frame\n", stderr);
                    goto done;
                }
#ifndef CW_YUV_RENDERER
                if (accepted > 0) {
                    uint32_t lease[] = {generation, now_seconds(), geometry->width,
                                        geometry->height};
                    if (!cw_wire_write(VIDEO_READY, "CWRD1", lease, 4))
                        goto done;
                }
#endif
            }
            sequence = next_sequence(sequence);
        }
#ifdef CW_YUV_RENDERER
        if (cw_yuv_take(&pixels, image, pixels.size, &image_sequence)) {
            if (!generation || !cw_pixels_write(channel, image, pixels.size)) {
                fputs("CARPLAY_SOURCE_FAILED stage=pixel-ipc-write\n", stderr);
                goto done;
            }
            last_pixels = cw_monotonic_ms();
        }
        if (cw_monotonic_ms() - last_pixels > 5000) {
            fputs("CARPLAY_SOURCE_FAILED stage=pixel-timeout\n", stderr);
            break;
        }
#endif
        if (cw_monotonic_ms() - last_data > 5000) {
            fputs("CARPLAY_SOURCE_FAILED stage=data-timeout\n", stderr);
            break;
        }
        pause_ms(5);
    }
    result = 0;
done:
#ifndef CW_YUV_RENDERER
    if (getppid() != parent) {
        unlink(READY);
        restore_context(root, original);
    }
#endif
    unlink(VIDEO_READY);
#ifdef CW_YUV_RENDERER
    alarm(3); /* isolate a hung vendor decoder close to this child */
#endif
    cw_nvss_stop(&sink);
    if (ring)
        munmap(ring, sizeof(*ring));
    if (fd >= 0)
        close(fd);
    free(message);
    free(config);
    if (library)
        dlclose(library);
#ifdef CW_YUV_RENDERER
    cw_yuv_capture_close();
    cw_yuv_close(&pixels);
    free(image);
#endif
    return result;
}

static void stop_child(pid_t *child) {
    unsigned i;
    int status;
    if (*child <= 0) {
        unlink(READY);
        unlink(VIDEO_READY);
        return;
    }
    kill(*child, SIGTERM);
    for (i = 0; i < 15; ++i) {
        if (waitpid(*child, &status, WNOHANG) == *child) {
            *child = -1;
            unlink(READY);
            unlink(VIDEO_READY);
            return;
        }
        pause_ms(50);
    }
    kill(*child, SIGKILL);
    waitpid(*child, &status, 0);
    *child = -1;
    unlink(READY);
    unlink(VIDEO_READY);
}
#ifdef CW_YUV_RENDERER
static int decode_worker(const cw_geometry *geometry, const char *root, unsigned original,
                         pid_t parent) {
    cw_pixels channel = {0};
    cw_yuv_gl renderer = {0};
    cw_window window;
    cw_window_libraries windows;
    uint8_t *image = NULL;
    size_t bytes = (size_t)geometry->width * geometry->height * 3 / 2;
    uint32_t sequence = 0;
    uint64_t last_pixels = cw_monotonic_ms();
    pid_t decoder = -1, renderer_pid = getpid();
    char report[16384];
    int result = 1;
    memset(&window, 0, sizeof(window));
    memset(&windows, 0, sizeof(windows));
    if (original != 72) {
        fprintf(stderr, "CARPLAY_RENDERER_FAILED stage=original-context value=%u\n", original);
        goto done;
    }
    if (!cw_dm_query(root, "gd", report, sizeof(report))) {
        fputs("CARPLAY_RENDERER_FAILED stage=displayables-query\n", stderr);
        goto done;
    }
    if (!cw_dm_layer(report, 79, geometry->width, geometry->height, 0)) {
        fputs("CARPLAY_RENDERER_FAILED stage=hidden-layer-conflict\n", stderr);
        goto done;
    }
    if (!cw_pixels_open(&channel, geometry->width, geometry->height)) {
        fputs("CARPLAY_RENDERER_FAILED stage=pixel-channel\n", stderr);
        goto done;
    }
    /* Fork BEFORE either process loads its GPU libraries. NvSS close terminates
     * its KD connection; it must never share a process with the EGL window. */
    decoder = fork();
    if (decoder == 0) {
        int status = source_worker(geometry, root, original, renderer_pid, &channel);
        cw_pixels_close(&channel);
        _exit(status);
    }
    if (decoder < 0) {
        fprintf(stderr, "CARPLAY_RENDERER_FAILED stage=decoder-fork errno=%d\n", errno);
        goto done;
    }
    if (!cw_window_load(&windows)) {
        fputs("CARPLAY_RENDERER_FAILED stage=window-libraries\n", stderr);
        goto done;
    }
    if (!cw_window_start(&window, &windows.api, geometry->width, geometry->height, 78)) {
        fputs("CARPLAY_RENDERER_FAILED stage=window-start\n", stderr);
        goto done;
    }
    if (!cw_yuv_gl_start(&renderer, &window, windows.gles_library)) {
        fputs("CARPLAY_RENDERER_FAILED stage=gles-start\n", stderr);
        goto done;
    }
    image = malloc(bytes);
    if (!image) {
        fputs("CARPLAY_RENDERER_FAILED stage=image-allocation\n", stderr);
        goto done;
    }
    while (!stopped && getppid() == parent) {
        cw_geometry current;
        int status;
        if (waitpid(decoder, &status, WNOHANG) == decoder) {
            decoder = -1;
            break;
        }
        if (!cw_geometry_read(GEOMETRY, now_seconds(), &current) || !current.active ||
            current.width != geometry->width || current.height != geometry->height)
            break;
        if (cw_pixels_read(&channel, image, bytes, &sequence)) {
            uint32_t lease[] = {sequence, now_seconds(), geometry->width, geometry->height};
            if (cw_i420_has_picture(image, bytes, geometry->width, geometry->height)) {
                if (!cw_yuv_gl_draw(&renderer, image, bytes) ||
                    !cw_wire_write(VIDEO_READY, "CWRD1", lease, 4))
                    goto done;
                last_pixels = cw_monotonic_ms();
            } else {
                /* Do not make context 70 eligible for a blank Google Maps
                 * stream. An earlier useful lease expires and the supervisor
                 * restores the OEM map through its existing watchdog. */
                lease[0] = 0;
                if (!cw_wire_write(VIDEO_READY, "CWRD1", lease, 4))
                    goto done;
            }
        }
        if (cw_monotonic_ms() - last_pixels > 5000)
            break;
        pause_ms(5);
    }
    result = 0;
done:
    if (getppid() != parent)
        restore_context(root, original);
    stop_child(&decoder);
    free(image);
    cw_yuv_gl_stop(&renderer);
    cw_window_stop(&window);
    cw_window_unload(&windows);
    cw_pixels_close(&channel);
    return result;
}
#endif

static void restore_context(const char *root, unsigned original) {
    char text[16384];
    cw_display display;
    /* Respect a different cluster page selected by the driver in the meantime. */
    if (original <= 157 && cw_dm_query(root, "gs", text, sizeof(text)) &&
        cw_dm_display(text, &display) && display.context == 70)
        (void)cw_dm_switch(root, display.id, original);
}
static int supervisor(const char *root, pid_t owner, int bounded_test) {
    pid_t child = -1, supervisor_pid = getpid();
    unsigned original = UINT32_MAX;
    int lock = -1, active = 0;
    uint64_t retry_at = 0;
    uint64_t geometry_at = 0;
    cw_session session;
    cw_session_init(&session);
    cw_geometry negotiated;
    unsigned tries;
    int previous_alive = -1, previous_valid = -1;
    for (tries = 0; tries < 30; ++tries) {
        lock = open(LOCK, O_CREAT | O_EXCL | O_WRONLY, 0600);
        if (lock >= 0)
            break;
        if (errno != EEXIST)
            return 1;
        {
            long old = 0;
            FILE *f = fopen(LOCK, "rb");
            if (f) {
                (void)fscanf(f, "%ld", &old);
                fclose(f);
            }
            if (old > 1 && kill((pid_t)old, 0) == 0) {
                pause_ms(100);
                continue;
            }
            unlink(LOCK);
        }
    }
    if (lock < 0)
        return 1;
    {
        char pid[32];
        int n = snprintf(pid, sizeof(pid), "%ld\n", (long)getpid());
        if (write(lock, pid, (size_t)n) != n) {
            close(lock);
            unlink(LOCK);
            return 1;
        }
        close(lock);
    }
    unlink(READY);
    fprintf(stderr, "CARPLAY_SUPERVISOR_STARTED owner=%ld\n", (long)owner);
    while (!stopped && (bounded_test || kill(owner, 0) == 0)) {
        cw_display observed;
        if (cw_monotonic_ms() >= geometry_at) {
            geometry_at = cw_monotonic_ms() + 1000;
            if (publish_geometry(root, &observed) && active &&
                cw_map_context((unsigned)observed.context)) {
                uint32_t lease[4];
                unsigned now = now_seconds();
                if (cw_wire_read(VIDEO_READY, "CWRD1", lease, 4) && lease[0] > 0 &&
                    lease[1] <= now &&
                    now - lease[1] <= 3)
                    (void)cw_dm_switch(root, observed.id, 70);
            }
        }
        struct stat log_stat;
        if (!fstat(STDERR_FILENO, &log_stat) && S_ISREG(log_stat.st_mode) &&
            log_stat.st_size > 128 * 1024)
            (void)ftruncate(STDERR_FILENO, 0);
        cw_geometry geometry;
        uint32_t ready[4], context[3];
        uint32_t now = now_seconds();
        char enabled[512];
        unsigned actions;
        int alive = source_ready(owner), valid = cw_geometry_read(GEOMETRY, now, &geometry);
        if (snprintf(enabled, sizeof(enabled), "%s/enabled", root) >= (int)sizeof(enabled) ||
            access(enabled, F_OK) != 0)
            alive = 0;
        /* A verified video stream is authoritative even if the HMI leaves its
         * foreground CarPlay page. Manager activity is only an observation. */
        if (valid)
            geometry.carplay_active = alive ? 1 : 0;
        if (alive != previous_alive || valid != previous_valid) {
            fprintf(stderr, "CARPLAY_SOURCE_STATE alive=%d valid=%d owner=%ld\n",
                    alive, valid, (long)owner);
            previous_alive = alive;
            previous_valid = valid;
        }
        actions = child > 0 ? cw_session_update(&session, valid ? &geometry : NULL, now,
                                                alive ? (uint32_t)owner : 0, 1)
                            : CW_NONE;
        if (actions & CW_STOP_VIDEO) {
            unlink(READY);
            restore_context(root, original);
            stop_child(&child);
            active = 0;
            retry_at = cw_monotonic_ms() + 2000;
        }
        if (child > 0) {
            int status;
            if (waitpid(child, &status, WNOHANG) == child) {
                child = -1;
                unlink(READY);
                restore_context(root, original);
                cw_session_stop(&session);
                active = 0;
                retry_at = cw_monotonic_ms() + 2000;
            }
        }
        if (child <= 0 && alive && valid && geometry.active && cw_monotonic_ms() >= retry_at) {
            char text[16384];
            cw_display display;
            if (cw_dm_query(root, "gs", text, sizeof(text)) && cw_dm_display(text, &display) &&
                cw_dm_query(root, "gd", text, sizeof(text)) &&
                cw_dm_layer(text, LAYER, geometry.width, geometry.height, 0)) {
                if (cw_map_context((unsigned)display.context))
                    original = (unsigned)display.context;
                else if ((display.context == 70 || display.context == 149) &&
                         cw_wire_read(CONTEXT, "CWCT1", context, 3) && cw_map_context(context[2]))
                    original = context[2];
                else {
                    retry_at = cw_monotonic_ms() + 2000;
                    pause_ms(100);
                    continue;
                }
                if (!prepare_context(root)) {
                    fputs("CARPLAY_CONTEXT_NOT_AVAILABLE\n", stderr);
                    retry_at = cw_monotonic_ms() + 2000;
                    pause_ms(100);
                    continue;
                }
                {
                    uint32_t snapshot[3] = {now_seconds(), original, original};
                    if (!cw_wire_write(CONTEXT, "CWCT1", snapshot, 3))
                        break;
                }
                negotiated = geometry;
                child = fork();
                if (child == 0) {
                    stopped = 0;
                    _exit(decode_worker(&negotiated, root, original, supervisor_pid));
                }
                if (child < 0) {
                    fprintf(stderr, "CARPLAY_WORKER_FORK_FAILED errno=%d\n", errno);
                    child = -1;
                    retry_at = cw_monotonic_ms() + 2000;
                } else {
                    fprintf(stderr, "CARPLAY_WORKER_STARTED pid=%ld original=%u size=%ux%u\n",
                            (long)child, original, negotiated.width, negotiated.height);
                    now = now_seconds();
                    cw_session_stop(&session);
                    (void)cw_session_update(&session, &negotiated, now, (uint32_t)owner, 1);
                }
            } else {
                fputs("CARPLAY_DISPLAY_PREFLIGHT_FAILED\n", stderr);
                retry_at = cw_monotonic_ms() + 2000;
            }
        }
        now = now_seconds();
        if (child > 0 && cw_wire_read(VIDEO_READY, "CWRD1", ready, 4) && ready[0] == 0 &&
            ready[1] <= now && now - ready[1] <= 3) {
            /* Keep decoding in case useful pixels return, but never leave a
             * blank Google Maps stream in control of the instrument screen. */
            unlink(READY);
            if (active) {
                restore_context(root, original);
                fprintf(stderr, "CARPLAY_BLANK_RESTORED_OEM display-context=%u\n", original);
            }
            active = 0;
            (void)cw_session_stop(&session);
        }
        if (child > 0 && cw_wire_read(VIDEO_READY, "CWRD1", ready, 4) && ready[0] > 0 &&
            ready[1] <= now && now - ready[1] <= 3) {
            int output_ok = 1;
            if (!active) {
                char text[16384];
                output_ok = cw_dm_query(root, "gd", text, sizeof(text)) &&
                            cw_dm_layer(text, LAYER, ready[2], ready[3], 1);
#ifdef CW_YUV_RENDERER
                /* Declare only after the real window exists, including on a
                 * freshly booted unit with no previous diagnostic context. */
                if (output_ok)
                    output_ok = cw_dm_declare_overlay(root);
#endif
            }
            now = now_seconds();
            if (ready[1] > now || now - ready[1] > 3)
                output_ok = 0;
            if (output_ok && !cw_wire_write(READY, "CWRD1", ready, 4))
                output_ok = 0;
            actions =
                cw_session_frame(&session, session.epoch, now, ready[2], ready[3], 1, output_ok);
            if (actions & CW_SHOW_CARPLAY) {
                char text[16384];
                cw_display display;
                unsigned own = 70;
                cw_display target;
                if (cw_dm_query(root, "gs", text, sizeof(text)) && cw_dm_display(text, &target) &&
                    (cw_map_context((unsigned)target.context) || target.context == 70) &&
                    cw_dm_switch(root, target.id, own) &&
                    cw_dm_query(root, "gs", text, sizeof(text)) && cw_dm_display(text, &display) &&
                    display.context == (int)own) {
                    active = 1;
                    fprintf(stderr, "CARPLAY_ACTIVE display=%u context=%u size=%ux%u\n", target.id,
                            own, ready[2], ready[3]);
                } else {
                    unlink(READY);
                    restore_context(root, original);
                    stop_child(&child);
                    cw_session_stop(&session);
                    retry_at = cw_monotonic_ms() + 2000;
                }
            }
            if (actions & CW_STOP_VIDEO) {
                unlink(READY);
                restore_context(root, original);
                stop_child(&child);
                active = 0;
                retry_at = cw_monotonic_ms() + 2000;
            }
        }
        pause_ms(100);
    }
    unlink(READY);
    restore_context(root, original);
    stop_child(&child);
    unlink(LOCK);
    fprintf(stderr, "CARPLAY_SUPERVISOR_STOPPED bounded=%d owner_alive=%d\n",
            bounded_test, kill(owner, 0) == 0);
    return 0;
}

int main(int argc, char **argv) {
    /* Diagnostics must be visible during a session, not only when a redirected
     * stdout buffer is flushed at program exit. */
    setvbuf(stdout, NULL, _IOLBF, 0);
    setvbuf(stderr, NULL, _IOLBF, 0);
    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    if (argc == 2 && !strcmp(argv[1], "--inspect-ring-config")) {
        int fd = open(RING, O_RDONLY);
        struct stat st;
        AltFrameRing *ring;
        uint32_t available, offset;
        if (fd < 0 || fstat(fd, &st) || st.st_size != (off_t)sizeof(*ring)) {
            if (fd >= 0) close(fd);
            return 1;
        }
        ring = mmap(NULL, sizeof(*ring), PROT_READ, MAP_SHARED, fd, 0);
        close(fd);
        if (ring == MAP_FAILED || ring->magic != ALT_FRAME_RING_MAGIC ||
            ring->version != ALT_FRAME_RING_VERSION) {
            if (ring != MAP_FAILED) munmap(ring, sizeof(*ring));
            return 1;
        }
        __sync_synchronize();
        available = ring->write_sequence;
        for (offset = 0; offset < ALT_FRAME_RING_SLOT_COUNT && available > offset; ++offset) {
            uint32_t sequence = available - offset;
            AltFrameRingSlot *slot = &ring->slots[(sequence - 1U) % ALT_FRAME_RING_SLOT_COUNT];
            uint32_t committed = slot->committed_sequence;
            size_t i;
            if (committed != sequence || slot->type != ALT_FRAME_TYPE_CONFIG ||
                !slot->size || slot->size > ALT_FRAME_RING_SLOT_DATA_MAX)
                continue;
            __sync_synchronize();
            printf("CARPLAY_CONFIG sequence=%u size=%u hex=", sequence, slot->size);
            for (i = 0; i < slot->size && i < 256; ++i)
                printf("%02x", slot->data[i]);
            putchar('\n');
            munmap(ring, sizeof(*ring));
            return 0;
        }
        munmap(ring, sizeof(*ring));
        return 1;
    }
    if (argc == 3 && !strcmp(argv[1], "--inspect")) {
        char text[65536];
        cw_display display;
        if (!cw_dm_query(argv[2], "gs", text, sizeof(text)) || !cw_dm_display(text, &display))
            return 1;
        printf("CLUSTER id=%u terminal=2nd_lvds size=%ux%u context=%d\n", display.id, display.width,
               display.height, display.context);
        if (!cw_dm_query(argv[2], "gc", text, sizeof(text)))
            return 1;
        printf("CONTEXT_70 state=%d\n", cw_dm_context_state(text, 70, LAYER));
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "--hash")) {
        char sum[65];
        if (!cw_sha256_file(argv[2], sum))
            return 1;
        puts(sum);
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "--check-jar"))
        return cw_jar_compatible(argv[2]) ? 0 : 1;
    if (argc == 2 && !strcmp(argv[1], "--check-firmware"))
        return firmware_check() ? 0 : 1;
    if (argc == 3 && !strcmp(argv[1], "--prime-geometry")) {
        cw_display display;
        if (!firmware_check() || !publish_geometry(argv[2], &display) || display.context != 72)
            return 1;
        puts("CARPLAY_GEOMETRY_PRIMED");
        return 0;
    }
    if (argc == 5 && !strcmp(argv[1], "--run-test")) {
        char *end = NULL;
        long owner, seconds;
        errno = 0;
        owner = strtol(argv[3], &end, 10);
        if (errno || !end || *end || owner <= 1 || owner > 2147483647L)
            return 2;
        errno = 0;
        seconds = strtol(argv[4], &end, 10);
        if (errno || !end || *end || seconds < 5 || seconds > 120 || !firmware_check())
            return 2;
        signal(SIGALRM, on_signal);
        alarm((unsigned)seconds);
        return supervisor(argv[2], (pid_t)owner, 1);
    }
    if (argc == 4 && !strcmp(argv[1], "--run")) {
        char *end = NULL;
        long owner = strtol(argv[3], &end, 10);
        if (!end || *end || owner <= 1)
            return 2;
        return supervisor(argv[2], (pid_t)owner, 0);
    }
    fputs("Usage: porsche-carplay --check-firmware | --hash FILE | --run INSTALL_ROOT DIO_PID\n",
          stderr);
    return 2;
}
