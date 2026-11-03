#ifndef CW_PORSCHE_YUV_H
#define CW_PORSCHE_YUV_H
#include <stddef.h>
#include <stdint.h>
#include <pthread.h>

/* NvMediaVideoSurfaceLock, MU1417 ARM ABI: offsets 0..31 describe planar
 * YUV. The vendor also writes offsets 32..63 for other surface types.
 * Allocate the complete structure even when those formats are rejected. */
typedef struct {
    uint32_t width, height;
    uint8_t *y;
    uint32_t pitch_y;
    uint8_t *u;
    uint32_t pitch_u;
    uint8_t *v;
    uint32_t pitch_v;
    uint8_t other_formats[32];
} cw_yuv_map;

typedef struct {
    pthread_mutex_t mutex;
    uint8_t *pixels;
    unsigned width, height;
    size_t size;
    uint64_t sequence;
    int initialized;
} cw_yuv_mailbox;

/* Exactly one decoder producer. Copies while the NvMedia surface is locked;
 * no surface pointer survives its callback. Consumer owns its output buffer.
 * Close only after the decoder and all its callbacks have stopped. */
int cw_yuv_open(cw_yuv_mailbox *, unsigned width, unsigned height);
int cw_yuv_publish(cw_yuv_mailbox *, const cw_yuv_map *);
int cw_yuv_take(cw_yuv_mailbox *, uint8_t *, size_t capacity, uint64_t *sequence);
void cw_yuv_close(cw_yuv_mailbox *);
#endif
