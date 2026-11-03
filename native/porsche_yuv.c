#include "porsche_yuv.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#if UINTPTR_MAX == UINT32_MAX
typedef char cw_yuv_map_size[sizeof(cw_yuv_map) == 64 ? 1 : -1];
typedef char cw_yuv_map_u[offsetof(cw_yuv_map, u) == 16 ? 1 : -1];
typedef char cw_yuv_map_v[offsetof(cw_yuv_map, v) == 24 ? 1 : -1];
#endif

int cw_yuv_open(cw_yuv_mailbox *s, unsigned w, unsigned h) {
    size_t size;
    if (!s || s->initialized || s->pixels || w < 64 || h < 64 || w > 1920 || h > 1080 || (w & 1) ||
        (h & 1))
        return 0;
    size = (size_t)w * h * 3 / 2;
    s->pixels = malloc(size);
    if (!s->pixels)
        return 0;
    if (pthread_mutex_init(&s->mutex, NULL)) {
        free(s->pixels);
        s->pixels = NULL;
        return 0;
    }
    s->width = w;
    s->height = h;
    s->size = size;
    s->sequence = 0;
    s->initialized = 1;
    return 1;
}

static int plane_valid(const uint8_t *p, unsigned pitch, unsigned w, unsigned h) {
    size_t last;
    if (!p || pitch < w || pitch > 16384)
        return 0;
    last = (size_t)(h - 1) * pitch + w;
    return (uintptr_t)p <= UINTPTR_MAX - last;
}

int cw_yuv_publish(cw_yuv_mailbox *s, const cw_yuv_map *map) {
    unsigned row, w, h;
    uint8_t *dst;
    if (!s || !s->initialized || !map || map->width != s->width || map->height != s->height)
        return 0;
    w = s->width;
    h = s->height;
    if (!plane_valid(map->y, map->pitch_y, w, h) ||
        !plane_valid(map->u, map->pitch_u, w / 2, h / 2) ||
        !plane_valid(map->v, map->pitch_v, w / 2, h / 2))
        return 0;
    pthread_mutex_lock(&s->mutex);
    dst = s->pixels;
    for (row = 0; row < h; ++row)
        memcpy(dst + (size_t)row * w, map->y + (size_t)row * map->pitch_y, w);
    dst += (size_t)w * h;
    for (row = 0; row < h / 2; ++row)
        memcpy(dst + (size_t)row * (w / 2), map->u + (size_t)row * map->pitch_u, w / 2);
    dst += (size_t)w * h / 4;
    for (row = 0; row < h / 2; ++row)
        memcpy(dst + (size_t)row * (w / 2), map->v + (size_t)row * map->pitch_v, w / 2);
    s->sequence = s->sequence == UINT64_MAX ? 1 : s->sequence + 1;
    pthread_mutex_unlock(&s->mutex);
    return 1;
}

int cw_yuv_take(cw_yuv_mailbox *s, uint8_t *out, size_t capacity, uint64_t *sequence) {
    int copied = 0;
    if (!s || !s->initialized || !out || !sequence || capacity < s->size)
        return 0;
    pthread_mutex_lock(&s->mutex);
    if (s->sequence && s->sequence != *sequence) {
        memcpy(out, s->pixels, s->size);
        *sequence = s->sequence;
        copied = 1;
    }
    pthread_mutex_unlock(&s->mutex);
    return copied;
}

void cw_yuv_close(cw_yuv_mailbox *s) {
    if (!s)
        return;
    if (s->initialized)
        pthread_mutex_destroy(&s->mutex);
    free(s->pixels);
    memset(s, 0, sizeof(*s));
}
