#ifndef CONNECTWOW_PORSCHE_FRAME_QUALITY_H
#define CONNECTWOW_PORSCHE_FRAME_QUALITY_H

#include <stddef.h>
#include <stdint.h>

/* A blank AirPlay frame must never take the cluster away from the OEM map. */
int cw_i420_has_picture(const uint8_t *i420, size_t bytes, unsigned width, unsigned height);

#endif
