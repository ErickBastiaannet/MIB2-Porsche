#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#ifndef _QNX_SOURCE
#define _QNX_SOURCE
#endif
#include "porsche_pixels.h"
#include <sys/mman.h>
#include <string.h>
typedef struct {
    volatile uint32_t sequence;
    uint32_t bytes, width, height;
    uint8_t pixels[];
} shared_pixels;

int cw_pixels_open(cw_pixels *channel, unsigned w, unsigned h) {
    shared_pixels *p;
    size_t bytes;
    if (!channel || channel->mapping || w < 64 || h < 64 || w > 1920 || h > 1080 ||
        (w & 1) || (h & 1))
        return 0;
    bytes = (size_t)w * h * 3 / 2;
    p = mmap(NULL, sizeof(*p) + bytes, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANON, -1, 0);
    if (p == MAP_FAILED)
        return 0;
    memset(p, 0, sizeof(*p));
    p->bytes = (uint32_t)bytes;
    p->width = w;
    p->height = h;
    channel->mapping = p;
    channel->size = sizeof(*p) + bytes;
    return 1;
}

int cw_pixels_write(cw_pixels *channel, const uint8_t *data, size_t bytes) {
    shared_pixels *p;
    uint32_t sequence;
    if (!channel || !(p = channel->mapping) || !data || channel->size < sizeof(*p) ||
        bytes != channel->size - sizeof(*p) || p->bytes != bytes)
        return 0;
    sequence = p->sequence;
    if (sequence & 1)
        return 0; /* no second writer may take over an unfinished frame */
    if (sequence >= UINT32_MAX - 2)
        sequence = 0;
    p->sequence = sequence + 1;
    __sync_synchronize();
    memcpy(p->pixels, data, bytes);
    __sync_synchronize();
    p->sequence = sequence + 2;
    return 1;
}

int cw_pixels_read(cw_pixels *channel, uint8_t *out, size_t bytes, uint32_t *previous) {
    shared_pixels *p;
    unsigned attempt;
    if (!channel || !(p = channel->mapping) || !out || !previous ||
        channel->size < sizeof(*p) || bytes != channel->size - sizeof(*p) || p->bytes != bytes)
        return 0;
    for (attempt = 0; attempt < 3; ++attempt) {
        uint32_t sequence = p->sequence;
        if (!sequence || sequence == *previous || (sequence & 1))
            return 0;
        __sync_synchronize();
        memcpy(out, p->pixels, bytes);
        __sync_synchronize();
        if (p->sequence == sequence) {
            *previous = sequence;
            return 1;
        }
    }
    return 0;
}

void cw_pixels_close(cw_pixels *channel) {
    if (!channel)
        return;
    if (channel->mapping)
        munmap(channel->mapping, channel->size);
    memset(channel, 0, sizeof(*channel));
}
