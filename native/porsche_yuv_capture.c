#include "porsche_yuv_capture.h"
#include "porsche_sha256.h"
#include "porsche_parser.h"
#include <dlfcn.h>
#include <string.h>

typedef struct {
    uint32_t picture_structure;
    void *next, *current, *previous, *previous2, *src_rect, *dst_rect;
} video_desc;
typedef int32_t (*render_fn)(void *, uint32_t, void *, void *, void *, void *, void *, void *,
                             void *);
static void *library;
static cw_yuv_mailbox *mailbox;
static render_fn real_render;
static int32_t (*real_decode)(void *, void *, void *, uint32_t, void *);
static int decoder_capture;
static int32_t (*surface_lock)(void *, cw_yuv_map *);
static void (*surface_unlock)(void *);

int cw_yuv_capture_open(cw_yuv_mailbox *target, const char *path) {
    char digest[65];
    if (library || !target || !target->initialized || !path || !cw_sha256_file(path, digest) ||
        strcmp(digest, "69f1555d5f6de4ebf9ee3bc30dbc73df2fc82bcba32456d0df48bb0f0e30da52"))
        return 0;
    library = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!library)
        return 0;
    real_render = (render_fn)dlsym(library, "NvMediaVideoMixerRender");
    surface_lock = (int32_t (*)(void *, cw_yuv_map *))dlsym(library, "NvMediaVideoSurfaceLock");
    surface_unlock = (void (*)(void *))dlsym(library, "NvMediaVideoSurfaceUnlock");
    if (!real_render || !surface_lock || !surface_unlock) {
        cw_yuv_capture_close();
        return 0;
    }
    mailbox = target;
    return 1;
}

void cw_yuv_capture_close(void) {
    cw_parser_stop();
    mailbox = NULL;
    real_render = NULL;
    real_decode = NULL;
    decoder_capture = 0;
    surface_lock = NULL;
    surface_unlock = NULL;
    if (library)
        dlclose(library);
    library = NULL;
}

int cw_yuv_capture_open_decoder(cw_yuv_mailbox *target, const char *path) {
    if (!cw_yuv_capture_open(target, path))
        return 0;
    real_decode = (int32_t (*)(void *, void *, void *, uint32_t, void *))
        dlsym(library, "NvMediaVideoDecoderRender");
    if (!real_decode) {
        cw_yuv_capture_close();
        return 0;
    }
    decoder_capture = 1;
    return 1;
}

static void copy_surface(void *surface) {
    cw_yuv_map map;
    memset(&map, 0, sizeof(map));
    if (!surface_lock(surface, &map)) {
        (void)cw_yuv_publish(mailbox, &map);
        surface_unlock(surface);
    }
}

int cw_yuv_capture_open_parser(cw_yuv_mailbox *target, const char *path) {
    if (!cw_yuv_capture_open(target, path))
        return 0;
    if (!cw_parser_start(copy_surface)) {
        cw_yuv_capture_close();
        return 0;
    }
    decoder_capture = 2; /* parser presentation order, not decoder order */
    return 1;
}

int32_t NvMediaVideoDecoderRender(void *decoder, void *surface, void *picture,
                                 uint32_t count, void *buffers) {
    int32_t result;
    if (!real_decode) {
        /* Mixer mode still needs a transparent original decoder call. */
        if (library)
            real_decode = (int32_t (*)(void *, void *, void *, uint32_t, void *))
                dlsym(library, "NvMediaVideoDecoderRender");
        if (!real_decode)
            return -1;
    }
    result = real_decode(decoder, surface, picture, count, buffers);
    if (!result && decoder_capture == 1 && mailbox && surface)
        copy_surface(surface);
    return result;
}

/* Nine arguments match this firmware's imported NvMedia ABI and the pinned
 * upstream tap. Preserve the original call, including its release-list output.
 * Copy synchronously while the callback still owns its decoded surface. The
 * upstream asynchronous raw-surface queue is deliberately not used here. */
int32_t NvMediaVideoMixerRender(void *mixer, uint32_t output, void *background, void *description,
                                void *a4, void *a5, void *a6, void *a7, void *a8) {
    int32_t result;
    video_desc *video = description;
    if (!real_render)
        return -1;
    result = real_render(mixer, output, background, description, a4, a5, a6, a7, a8);
    if (result || decoder_capture || !mailbox || !video || !video->current)
        return result;
    copy_surface(video->current);
    return result;
}
