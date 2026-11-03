#include "porsche_frame_quality.h"

int cw_i420_has_picture(const uint8_t *i420, size_t bytes, unsigned width, unsigned height) {
    size_t pixels, step, i, samples = 0, lit = 0;
    unsigned low = 255, high = 0;

    if (!i420 || !width || !height || width > 8192 || height > 8192)
        return 0;
    pixels = (size_t)width * height;
    if (pixels / width != height || pixels > (SIZE_MAX / 3) * 2 || bytes < pixels * 3 / 2)
        return 0;

    /* At most 4096 evenly distributed luma samples. These conservative
     * thresholds reject nominal video black (Y=16), decoder noise and blank
     * dark frames. Real map output contains highlights and spatial contrast. */
    step = pixels > 4096 ? pixels / 4096 : 1;
    for (i = 0; i < pixels; i += step) {
        unsigned y = i420[i];
        if (y < low)
            low = y;
        if (y > high)
            high = y;
        if (y >= 32)
            ++lit;
        ++samples;
    }
    return samples >= 16 && high - low >= 16 && lit * 100 >= samples;
}
