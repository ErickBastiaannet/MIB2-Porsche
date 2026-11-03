#include "porsche_yuv_capture.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int cw_parser_start(void (*surface)(void *)) { assert(surface); return 1; }
void cw_parser_stop(void) {}
static int bad_hash, missing_symbol, render_result, lock_result, locks, unlocks, renders, libraries;
static unsigned char y[4096], u[1024], v[1024];
static int fixture_hash(const char *path, char digest[65]) {
    assert(path);
    strcpy(digest,
           bad_hash ? "bad" : "69f1555d5f6de4ebf9ee3bc30dbc73df2fc82bcba32456d0df48bb0f0e30da52");
    return 1;
}
static void *fixture_open(const char *path, int flags) {
    assert(path && flags);
    ++libraries;
    return (void *)1;
}
static int fixture_close(void *p) {
    assert(p == (void *)1 && libraries == 1);
    --libraries;
    return 0;
}
static int32_t original_render(void *m, uint32_t output, void *bg, void *desc, void *a4, void *a5,
                               void *a6, void *a7, void *a8) {
    assert(m == (void *)2 && output == 1 && bg == (void *)3 && desc && a4 == (void *)4 &&
           a5 == (void *)5 && a6 == (void *)6 && a7 == (void *)7 && a8 == (void *)8);
    ++renders;
    return render_result;
}
static int32_t original_lock(void *surface, cw_yuv_map *map) {
    assert(surface == (void *)9);
    ++locks;
    if (lock_result)
        return lock_result;
    /* Exercise writes beyond the planar prefix, as the vendor can do. */
    memset(map->other_formats, 0xab, sizeof(map->other_formats));
    map->width = map->height = 64;
    map->y = y;
    map->u = u;
    map->v = v;
    map->pitch_y = 64;
    map->pitch_u = map->pitch_v = 32;
    return 0;
}
static void original_unlock(void *surface) {
    assert(surface == (void *)9);
    ++unlocks;
}
static void *fixture_symbol(void *library, const char *name) {
    assert(library == (void *)1);
    if (missing_symbol)
        return NULL;
    if (!strcmp(name, "NvMediaVideoMixerRender"))
        return (void *)original_render;
    if (!strcmp(name, "NvMediaVideoSurfaceLock"))
        return (void *)original_lock;
    if (!strcmp(name, "NvMediaVideoSurfaceUnlock"))
        return (void *)original_unlock;
    assert(0);
    return NULL;
}
#define cw_sha256_file fixture_hash
#define dlopen fixture_open
#define dlclose fixture_close
#define dlsym fixture_symbol
#include "../native/porsche_yuv_capture.c"
#undef cw_sha256_file
#undef dlopen
#undef dlclose
#undef dlsym
static int call(video_desc *desc) {
    return NvMediaVideoMixerRender((void *)2, 1, (void *)3, desc, (void *)4, (void *)5, (void *)6,
                                   (void *)7, (void *)8);
}
int main(void) {
    cw_yuv_mailbox box;
    video_desc desc;
    unsigned char image[6144];
    uint64_t sequence = 0;
    memset(&box, 0, sizeof(box));
    memset(&desc, 0, sizeof(desc));
    desc.current = (void *)9;
    memset(y, 60, sizeof(y));
    memset(u, 120, sizeof(u));
    memset(v, 180, sizeof(v));
    assert(cw_yuv_open(&box, 64, 64));
    bad_hash = 1;
    assert(!cw_yuv_capture_open(&box, "fixture") && !libraries);
    bad_hash = 0;
    missing_symbol = 1;
    assert(!cw_yuv_capture_open(&box, "fixture") && !libraries);
    missing_symbol = 0;
    assert(cw_yuv_capture_open(&box, "fixture"));
    assert(!cw_yuv_capture_open(&box, "fixture"));
    assert(call(&desc) == 0 && renders == 1 && locks == 1 && unlocks == 1);
    assert(cw_yuv_take(&box, image, sizeof(image), &sequence));
    assert(image[0] == 60 && image[4096] == 120 && image[5120] == 180);
    render_result = 7;
    assert(call(&desc) == 7 && locks == 1 && unlocks == 1);
    render_result = 0;
    lock_result = 7;
    assert(call(&desc) == 0 && locks == 2 && unlocks == 1);
    assert(!cw_yuv_take(&box, image, sizeof(image), &sequence));
    lock_result = 0;
    desc.current = NULL;
    assert(call(&desc) == 0 && locks == 2);
    cw_yuv_capture_close();
    cw_yuv_capture_close();
    assert(!libraries);
    cw_yuv_close(&box);
    puts("YUV_CAPTURE_PASS firmware gate, ABI forwarding, full map allocation, synchronous copy, "
         "lock/render errors, release, cleanup");
    return 0;
}
