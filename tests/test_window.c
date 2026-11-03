#include "porsche_window.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int failure, display_live, egl_live, window_live, surface_live, context_live;
static unsigned width, height, init_calls, scissors, clears, swaps, last_end;
#define HANDLE(n) ((void *)(uintptr_t)(n))
static void display_init(int *a, int *b) {
    assert(!a && !b && !display_live);
    display_live = 1;
    ++init_calls;
}
static void display_deinit(void) {
    assert(display_live && !egl_live && !window_live);
    display_live = 0;
}
static void *get_display(int d) {
    assert(d == 0 && display_live);
    return failure == 1 ? 0 : HANDLE(1);
}
static unsigned initialize(void *d, int *a, int *b) {
    assert(d == HANDLE(1) && !a && !b);
    if (failure == 2)
        return 0;
    egl_live = 1;
    return 1;
}
static unsigned choose_config(void *d, const int *attrs, void **cfg, int cap, int *count) {
    assert(d == HANDLE(1) && attrs && cap == 1 && egl_live);
    if (failure == 3)
        return 0;
    *cfg = HANDLE(2);
    *count = 1;
    return 1;
}
static int create_window(void *d, void *cfg, int w, int h, int layer, void **native, int *window) {
    assert(d == HANDLE(1) && cfg == HANDLE(2) && layer == 78 && w >= 64 && h >= 64);
    width = (unsigned)w;
    height = (unsigned)h;
    *native = HANDLE(3);
    *window = 7;
    window_live = 1;
    return failure == 4 ? 0 : 1; /* a partial allocation must also be cleaned */
}
static void destroy_window(int w) {
    assert(w == 7 && window_live && !surface_live);
    window_live = 0;
}
static int window_size(int w, int property, int *size) {
    assert(w == 7 && property == 66 && window_live);
    size[0] = (int)width;
    size[1] = (int)height + (failure == 5);
    return 0;
}
static void *create_surface(void *d, void *cfg, void *native, const int *attrs) {
    assert(d == HANDLE(1) && cfg == HANDLE(2) && native == HANDLE(3) && !attrs && window_live);
    if (failure == 6)
        return 0;
    surface_live = 1;
    return HANDLE(4);
}
static unsigned bind_api(unsigned api) {
    assert(api == 0x30a0 && surface_live);
    return failure != 7;
}
static void *create_context(void *d, void *cfg, void *shared, const int *attrs) {
    assert(d == HANDLE(1) && cfg == HANDLE(2) && !shared && attrs[0] == 0x3098 && attrs[1] == 2);
    if (failure == 8)
        return 0;
    context_live = 1;
    return HANDLE(5);
}
static unsigned make_current(void *d, void *draw, void *read, void *ctx) {
    assert(d == HANDLE(1) && egl_live);
    if (!ctx) {
        assert(!draw && !read);
        return 1;
    }
    assert(draw == HANDLE(4) && read == HANDLE(4) && ctx == HANDLE(5));
    return failure != 9;
}
static unsigned query_surface(void *d, void *surface, int attr, int *value) {
    assert(d == HANDLE(1) && surface == HANDLE(4) && surface_live);
    if (attr == 0x3057) {
        *value = (int)width;
        return failure != 10;
    }
    assert(attr == 0x3056);
    *value = (int)height + (failure == 11);
    return 1;
}
static unsigned swap_buffers(void *d, void *surface) {
    assert(d == HANDLE(1) && surface == HANDLE(4) && context_live);
    ++swaps;
    return failure != 13;
}
static unsigned destroy_context(void *d, void *ctx) {
    assert(d == HANDLE(1) && ctx == HANDLE(5) && context_live);
    context_live = 0;
    return 1;
}
static unsigned destroy_surface(void *d, void *surface) {
    assert(d == HANDLE(1) && surface == HANDLE(4) && surface_live && !context_live);
    surface_live = 0;
    return 1;
}
static unsigned terminate(void *d) {
    assert(d == HANDLE(1) && egl_live && !window_live && !surface_live && !context_live);
    egl_live = 0;
    return 1;
}
static void viewport(int x, int y, int w, int h) {
    assert(!x && !y && w == (int)width && h == (int)height);
}
static void enable(unsigned what) {
    assert(what == 0x0c11);
    last_end = 0;
}
static void disable(unsigned what) { assert(what == 0x0c11 && last_end == width); }
static void scissor(int x, int y, int w, int h) {
    assert(x == (int)last_end && !y && w > 0 && h == (int)height);
    last_end += (unsigned)w;
    ++scissors;
}
static void clear_color(float r, float g, float b, float a) {
    assert((r == 0 || r == 1) && (g == 0 || g == 1) && (b == 0 || b == 1) && a == 1);
}
static void clear(unsigned mask) {
    assert(mask == 0x4000);
    ++clears;
}
static unsigned gl_error(void) { return failure == 12 ? 0x502 : 0; }
static const cw_window_api api = {
    display_init,  display_deinit, create_window,   destroy_window,  window_size,    get_display,
    initialize,    choose_config,  bind_api,        create_surface,  create_context, make_current,
    query_surface, swap_buffers,   destroy_context, destroy_surface, terminate,      viewport,
    scissor,       enable,         disable,         clear_color,     clear,          gl_error};
static void empty(void) {
    assert(!display_live && !egl_live && !window_live && !surface_live && !context_live);
}
int main(void) {
    cw_window sink;
    cw_window_api missing;
    int stage;
    memset(&sink, 0, sizeof(sink));
    missing = api;
    missing.swap_buffers = 0;
    assert(!cw_window_start(&sink, &missing, 800, 480, 78));
    assert(!cw_window_start(&sink, &api, 800, 480, 59));
    assert(!cw_window_start(&sink, &api, 0, 480, 78));
    assert(!init_calls);
    for (stage = 1; stage <= 13; ++stage) {
        failure = stage;
        assert(!cw_window_start(&sink, &api, 803, 480, 78));
        empty();
        assert(!sink.display && !sink.kd_window && !sink.context && !sink.display_started);
        cw_window_stop(&sink);
        empty();
    }
    failure = 0;
    scissors = clears = swaps = 0;
    assert(cw_window_start(&sink, &api, 803, 480, 78));
    assert(scissors == 8 && clears == 8 && swaps == 1 && last_end == 803);
    assert(!cw_window_start(&sink, &api, 800, 480, 78));
    assert(cw_window_bars(&sink));
    assert(scissors == 16 && clears == 16 && swaps == 2);
    cw_window_stop(&sink);
    empty();
    cw_window_stop(&sink);
    empty();
    puts("PORSCHE_WINDOW_PASS 13 failure stages, exact KD/EGL geometry, compositor window, "
         "odd-width coverage, cleanup");
    return 0;
}
