#ifndef CONNECTWOW_PORSCHE_NVSS_H
#define CONNECTWOW_PORSCHE_NVSS_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t output_device, reserved_04;
    uint8_t priority, visible, layer_id, reserved_0b;
    uint32_t queue_depth, reserved_10, reserved_14;
} cw_nvss_open;
typedef struct {
    uint32_t width, height;
    float fps;
} cw_nvss_stream;
typedef struct {
    uint8_t *data;
    uint32_t size;
    uint64_t pts;
    uint8_t append_markers, reserved[3];
} cw_nvss_unit;
typedef struct {
    int32_t (*open)(void **, const cw_nvss_open *);
    int32_t (*configure)(void *, const cw_nvss_stream *);
    int32_t (*decode)(void *, const cw_nvss_unit *, uint32_t);
    int32_t (*close)(void *);
} cw_nvss_api;
typedef struct {
    cw_nvss_api api;
    void *handle;
    uint8_t *buffer;
    size_t capacity;
    unsigned length_size, have_idr;
} cw_nvss;

/* Sink for a separate managed decoder layer, never the main CarPlay layer 59.
 * It does not change DisplayManager contexts or take MOST ownership. */
int cw_nvss_start(cw_nvss *sink, const cw_nvss_api *api, uint32_t width, uint32_t height,
                  unsigned layer, unsigned output_device, const uint8_t *avcc_config, size_t size);
/* Diagnostic only: create an invisible layer without routing a display. */
int cw_nvss_start_hidden(cw_nvss *sink, const cw_nvss_api *api, uint32_t width, uint32_t height,
                         unsigned layer, unsigned output_device, const uint8_t *avcc_config,
                         size_t size);
/* 1: accepted; 0: awaiting IDR; -1: invalid input/decoder failure. */
int cw_nvss_frame(cw_nvss *sink, const uint8_t *avcc, size_t size, uint64_t pts);
void cw_nvss_stop(cw_nvss *sink);
#endif
