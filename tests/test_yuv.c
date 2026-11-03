#include "porsche_yuv.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    cw_yuv_mailbox box = {0};
    cw_yuv_map map = {0};
    uint8_t y[64 * 80], u[32 * 40], v[32 * 48], out[64 * 64 * 3 / 2];
    uint64_t sequence = 0;
    unsigned i;
    assert(!cw_yuv_open(&box, 63, 64));
    assert(!cw_yuv_open(&box, 65, 64));
    assert(!cw_yuv_open(&box, 1922, 64));
    assert(cw_yuv_open(&box, 64, 64));
    assert(!cw_yuv_open(&box, 64, 64));
    assert(!cw_yuv_take(&box, out, sizeof(out), &sequence));
    memset(y, 99, sizeof(y));
    memset(u, 111, sizeof(u));
    memset(v, 222, sizeof(v));
    for (i = 0; i < 64; ++i)
        memset(y + i * 80, (int)i, 64);
    map.width = map.height = 64;
    map.y = y;
    map.pitch_y = 80;
    map.u = u;
    map.pitch_u = 40;
    map.v = v;
    map.pitch_v = 48;
    assert(cw_yuv_publish(&box, &map));
    assert(!cw_yuv_take(&box, out, sizeof(out) - 1, &sequence));
    assert(cw_yuv_take(&box, out, sizeof(out), &sequence) && sequence == 1);
    for (i = 0; i < 4096; ++i)
        assert(out[i] == i / 64);
    for (i = 4096; i < 5120; ++i)
        assert(out[i] == 111);
    for (i = 5120; i < sizeof(out); ++i)
        assert(out[i] == 222);
    assert(!cw_yuv_take(&box, out, sizeof(out), &sequence));
    memset(y, 17, sizeof(y));
    assert(cw_yuv_publish(&box, &map));
    memset(y, 22, sizeof(y));
    assert(cw_yuv_publish(&box, &map)); /* latest frame wins; no growing queue */
    memset(y, 55, sizeof(y));           /* surface may be reused after callback */
    assert(cw_yuv_take(&box, out, sizeof(out), &sequence) && sequence == 3);
    assert(out[0] == 22 && out[4095] == 22);
    map.pitch_u = 31;
    assert(!cw_yuv_publish(&box, &map));
    map.pitch_u = 40;
    map.height = 66;
    assert(!cw_yuv_publish(&box, &map));
    map.height = 64;
    map.v = NULL;
    assert(!cw_yuv_publish(&box, &map));
    map.v = (uint8_t *)(uintptr_t)(UINTPTR_MAX - 10);
    assert(!cw_yuv_publish(&box, &map));
    cw_yuv_close(&box);
    cw_yuv_close(&box);
    assert(!cw_yuv_take(&box, out, sizeof(out), &sequence));
    puts("YUV_MAILBOX_PASS padded planes, exact dimensions, owned pixels, latest frame, bounds, "
         "cleanup");
    return 0;
}
