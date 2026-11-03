#ifndef CONNECTWOW_PORSCHE_GEOMETRY_H
#define CONNECTWOW_PORSCHE_GEOMETRY_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t generation, timestamp, active, visible, carplay_active, transport;
    uint32_t width, height, x, y, area_width, area_height;
} cw_geometry;

/* Parse one complete, CRC-checked HMI observation. No fallback dimensions. */
int cw_geometry_parse(const char *data, size_t length, uint32_t now, cw_geometry *out);
/* 1: matches the negotiated display; 0: inactive/invalid; -1: renegotiate. */
int cw_geometry_session(const cw_geometry *negotiated, const cw_geometry *current);
int cw_geometry_read(const char *path, uint32_t now, cw_geometry *out);
#endif
