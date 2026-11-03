#include "porsche_geometry.h"

static uint32_t crc32(const char *data, size_t length) {
    uint32_t crc = UINT32_C(0xffffffff);
    size_t i;
    unsigned bit;
    for (i = 0; i < length; i++) {
        crc ^= (unsigned char)data[i];
        for (bit = 0; bit < 8; bit++)
            crc = (crc >> 1) ^ ((crc & 1) ? UINT32_C(0xedb88320) : 0);
    }
    return crc ^ UINT32_C(0xffffffff);
}

int cw_geometry_parse(const char *data, size_t length, uint32_t now, cw_geometry *out) {
    uint32_t v[12], checksum = 0;
    size_t at = 6, start, i, j;
    cw_geometry parsed;
    if (!data || !out || length < 40 || length > 256)
        return 0;
    if (data[0] != 'C' || data[1] != 'W' || data[2] != 'C' || data[3] != 'P' || data[4] != '3' ||
        data[5] != ' ')
        return 0;
    for (i = 0; i < 12; i++) {
        v[i] = 0;
        start = at;
        while (at < length && data[at] >= '0' && data[at] <= '9') {
            unsigned digit = (unsigned)(data[at++] - '0');
            if (v[i] > (UINT32_MAX - digit) / 10)
                return 0;
            v[i] = v[i] * 10 + digit;
        }
        if (at == start || at >= length || data[at++] != ' ')
            return 0;
    }
    start = at;
    if (length != at + 9 || data[length - 1] != '\n')
        return 0;
    for (j = 0; j < 8; j++) {
        unsigned char c = (unsigned char)data[at++];
        unsigned digit;
        if (c >= '0' && c <= '9')
            digit = c - '0';
        else if (c >= 'a' && c <= 'f')
            digit = c - 'a' + 10;
        else
            return 0;
        checksum = (checksum << 4) | digit;
    }
    if (crc32(data, start) != checksum || !v[0] || v[2] > 1 || v[3] > 1 || v[4] > 1 ||
        (v[5] != 2 && v[5] != 3))
        return 0;
    if (v[1] > now || now - v[1] > 5)
        return 0;
    if (v[6] < 64 || v[6] > 8192 || v[7] < 64 || v[7] > 8192)
        return 0;
    if (!v[10] || !v[11] || v[10] > v[6] || v[11] > v[7] || v[8] > v[6] - v[10] ||
        v[9] > v[7] - v[11])
        return 0;
    parsed.generation = v[0];
    parsed.timestamp = v[1];
    parsed.active = v[2];
    parsed.visible = v[3];
    parsed.carplay_active = v[4];
    parsed.transport = v[5];
    parsed.width = v[6];
    parsed.height = v[7];
    parsed.x = v[8];
    parsed.y = v[9];
    parsed.area_width = v[10];
    parsed.area_height = v[11];
    *out = parsed;
    return 1;
}

int cw_geometry_session(const cw_geometry *negotiated, const cw_geometry *current) {
    if (!negotiated || !current || !current->active || !current->carplay_active)
        return 0;
    if (negotiated->transport != current->transport || negotiated->width != current->width ||
        negotiated->height != current->height || negotiated->x != current->x ||
        negotiated->y != current->y || negotiated->area_width != current->area_width ||
        negotiated->area_height != current->area_height)
        return -1;
    return 1;
}
