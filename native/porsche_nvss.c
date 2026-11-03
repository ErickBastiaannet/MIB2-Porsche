#include "porsche_nvss.h"
#include <stdlib.h>
#include <string.h>

#define CW_ACCESS_UNIT_MAX (1024U * 1024U)

/* ABI measured against MU1417 NvssVideoImpl::start/decode. Host tests may
 * have 64-bit pointers; these target checks apply to the actual ARM build. */
typedef char cw_open_size_check[sizeof(cw_nvss_open) == 24 ? 1 : -1];
typedef char cw_stream_size_check[sizeof(cw_nvss_stream) == 12 ? 1 : -1];
#if UINTPTR_MAX == UINT32_MAX
typedef char cw_unit_pts_check[offsetof(cw_nvss_unit, pts) == 8 ? 1 : -1];
typedef char cw_unit_marker_check[offsetof(cw_nvss_unit, append_markers) == 16 ? 1 : -1];
#endif

static int append_nal(cw_nvss *s, size_t *used, const uint8_t *bytes, size_t size) {
    static const uint8_t prefix[] = {0, 0, 0, 1};
    if (!size || size > s->capacity || *used > s->capacity - size ||
        s->capacity - *used - size < sizeof(prefix))
        return 0;
    memcpy(s->buffer + *used, prefix, sizeof(prefix));
    memcpy(s->buffer + *used + sizeof(prefix), bytes, size);
    *used += sizeof(prefix) + size;
    return 1;
}

void cw_nvss_stop(cw_nvss *s) {
    if (s->handle && s->api.close)
        (void)s->api.close(s->handle);
    free(s->buffer);
    memset(s, 0, sizeof(*s));
}

static int start(cw_nvss *s, const cw_nvss_api *api, uint32_t width, uint32_t height,
                 unsigned layer, unsigned output, const uint8_t *data, size_t size,
                 unsigned visible) {
    cw_nvss_open open;
    cw_nvss_stream stream;
    cw_nvss_unit unit;
    size_t at = 6, used = 0, length;
    unsigned count, i, group;
    /* Caller must initialise the object to zero, and stop before restarting. */
    if (!s || s->handle || s->buffer || !api || !api->open || !api->configure || !api->decode ||
        !api->close || !data || size < 7 || size > CW_ACCESS_UNIT_MAX || data[0] != 1 ||
        width < 64 || height < 64 || width > 1920 || height > 1080 || layer < 64 || layer > 99 ||
        output > 1)
        return 0;
    s->length_size = (data[4] & 3) + 1;
    if (s->length_size == 3)
        return 0;
    s->api = *api;
    s->capacity = CW_ACCESS_UNIT_MAX;
    s->buffer = (uint8_t *)malloc(s->capacity);
    if (!s->buffer)
        return 0;
    count = data[5] & 31;
    if (!count)
        goto invalid;
    for (group = 0; group < 2; ++group) {
        for (i = 0; i < count; ++i) {
            if (at + 2 > size)
                goto invalid;
            length = ((size_t)data[at] << 8) | data[at + 1];
            at += 2;
            if (!length || length > size - at || (data[at] & 31) != (group ? 8 : 7) ||
                !append_nal(s, &used, data + at, length))
                goto invalid;
            at += length;
        }
        if (!group) {
            if (at == size)
                goto invalid;
            count = data[at++];
            if (!count)
                goto invalid;
        }
    }
    if (at < size) {
        /* The iPhone's AirPlay Screen stream appends a four-byte display
         * extension (02 00 00 00) after an otherwise complete avcC record.
         * It is not the ISO high-profile extension: the upstream MHI2 bridge
         * deliberately stops parsing after PPS as well. Accept only the exact
         * physically observed suffix; arbitrary trailing bytes remain invalid. */
        if (size - at == 4 && data[at] == 2 && data[at + 1] == 0 &&
            data[at + 2] == 0 && data[at + 3] == 0) {
            at = size;
        } else {
            /* ISO/IEC 14496-15 high-profile extension: chroma format, bit
             * depths and optional SPS extension list. */
            if (data[1] != 100 && data[1] != 110 && data[1] != 122 && data[1] != 144)
                goto invalid;
            if (size - at < 4 || (data[at] & 0xfc) != 0xfc ||
                (data[at + 1] & 0xf8) != 0xf8 || (data[at + 2] & 0xf8) != 0xf8)
                goto invalid;
            at += 3;
            count = data[at++];
            for (i = 0; i < count; ++i) {
                if (size - at < 2)
                    goto invalid;
                length = ((size_t)data[at] << 8) | data[at + 1];
                at += 2;
                if (!length || length > size - at || (data[at] & 31) != 13 ||
                    !append_nal(s, &used, data + at, length))
                    goto invalid;
                at += length;
            }
        }
    }
    if (at != size)
        goto invalid;
    memset(&open, 0, sizeof(open));
    open.output_device = output;
    open.priority = 100;
    open.visible = (uint8_t)visible;
    open.layer_id = (uint8_t)layer;
    open.queue_depth = 8;
    if (api->open(&s->handle, &open) || !s->handle)
        goto invalid;
    stream.width = width;
    stream.height = height;
    stream.fps = 25.0f;
    if (api->configure(s->handle, &stream))
        goto invalid;
    memset(&unit, 0, sizeof(unit));
    unit.data = s->buffer;
    unit.size = (uint32_t)used;
    if (api->decode(s->handle, &unit, 40))
        goto invalid;
    return 1;
invalid:
    cw_nvss_stop(s);
    return 0;
}

int cw_nvss_start(cw_nvss *s, const cw_nvss_api *api, uint32_t width, uint32_t height,
                  unsigned layer, unsigned output, const uint8_t *data, size_t size) {
    return start(s, api, width, height, layer, output, data, size, 1);
}

int cw_nvss_start_hidden(cw_nvss *s, const cw_nvss_api *api, uint32_t width, uint32_t height,
                         unsigned layer, unsigned output, const uint8_t *data, size_t size) {
    return start(s, api, width, height, layer, output, data, size, 0);
}

int cw_nvss_frame(cw_nvss *s, const uint8_t *data, size_t size, uint64_t pts) {
    size_t at = 0, used = 0, length;
    unsigned i, idr = 0;
    cw_nvss_unit unit;
    if (!s || !s->handle || !data || !size || size > CW_ACCESS_UNIT_MAX)
        return -1;
    while (at < size) {
        if (size - at < s->length_size)
            return -1;
        length = 0;
        for (i = 0; i < s->length_size; ++i)
            length = (length << 8) | data[at++];
        if (!length || length > size - at || !append_nal(s, &used, data + at, length))
            return -1;
        if ((data[at] & 31) == 5)
            idr = 1;
        at += length;
    }
    if (!s->have_idr && !idr)
        return 0;
    memset(&unit, 0, sizeof(unit));
    unit.data = s->buffer;
    unit.size = (uint32_t)used;
    unit.pts = pts;
    if (s->api.decode(s->handle, &unit, 40))
        return -1;
    if (idr)
        s->have_idr = 1;
    return 1;
}
