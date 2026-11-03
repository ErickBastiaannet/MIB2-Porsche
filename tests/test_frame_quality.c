#include "porsche_frame_quality.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    unsigned char frame[8 * 8 * 3 / 2];
    unsigned i;

    memset(frame, 16, sizeof(frame));
    assert(!cw_i420_has_picture(frame, sizeof(frame), 8, 8));
    for (i = 0; i < 64; ++i)
        frame[i] = (unsigned char)(15 + (i % 4));
    assert(!cw_i420_has_picture(frame, sizeof(frame), 8, 8));

    memset(frame, 16, sizeof(frame));
    for (i = 0; i < 8; ++i)
        frame[i * 8 + i] = 180;
    assert(cw_i420_has_picture(frame, sizeof(frame), 8, 8));

    memset(frame, 200, sizeof(frame));
    assert(!cw_i420_has_picture(frame, sizeof(frame), 8, 8));
    assert(!cw_i420_has_picture(frame, sizeof(frame) - 1, 8, 8));
    assert(!cw_i420_has_picture(NULL, sizeof(frame), 8, 8));
    puts("FRAME_QUALITY_PASS black/noise rejected, contrasted picture accepted, bounds checked");
    return 0;
}
