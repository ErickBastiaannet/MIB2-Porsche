#include "porsche_session.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned checks;
#define CHECK(expr) do { ++checks; assert(expr); } while (0)

static unsigned crc(const char *data, size_t length) {
    unsigned result = 0xffffffffU, i;
    size_t j;
    for (j = 0; j < length; ++j) {
        result ^= (unsigned char)data[j];
        for (i = 0; i < 8; ++i) result = (result >> 1) ^ ((result & 1) ? 0xedb88320U : 0);
    }
    return result ^ 0xffffffffU;
}

static size_t record(char *out, const char *body) {
    int count = snprintf(out, 256, "%s%08x\n", body, crc(body, strlen(body)));
    assert(count > 0 && count < 256);
    return (size_t)count;
}

int main(int argc, char **argv) {
    cw_geometry g, unchanged;
    cw_session s;
    char line[256], corrupt[256];
    size_t n, i;
    uint32_t epoch;
    /* Synthetic geometry deliberately differs from every upstream profile. */
    n = record(line, "CWCP3 1 1000 1 1 1 2 960 640 40 20 880 600 ");
    CHECK(cw_geometry_parse(line, n, 1000, &g));
    CHECK(g.width == 960 && g.height == 640 && g.x == 40 && g.area_height == 600);
    unchanged = g;
    for (i = 0; i < n; ++i) {
        memcpy(corrupt, line, n); corrupt[i] ^= 1;
        CHECK(!cw_geometry_parse(corrupt, n, 1000, &g));
        CHECK(!memcmp(&g, &unchanged, sizeof(g)));
    }
    CHECK(!cw_geometry_parse(line, n - 1, 1000, &g));
    CHECK(!cw_geometry_parse(line, n, 999, &g));
    CHECK(cw_geometry_parse(line, n, 1005, &g));
    CHECK(!cw_geometry_parse(line, n, 1006, &g));
    n = record(line, "CWCP3 1 1000 1 1 1 2 960 640 4294967295 20 880 600 ");
    CHECK(!cw_geometry_parse(line, n, 1000, &g));
    n = record(line, "CWCP3 4294967296 1000 1 1 1 2 960 640 40 20 880 600 ");
    CHECK(!cw_geometry_parse(line, n, 1000, &g));
    n = record(line, "CWCP3 1 1000 1 1 1 7 960 640 40 20 880 600 ");
    CHECK(!cw_geometry_parse(line, n, 1000, &g));
    g = unchanged;
    cw_session_init(&s);
    CHECK(cw_session_update(&s, &g, 1000, 1, 0) == CW_NONE); /* no verified output */
    CHECK(cw_session_update(&s, &g, 1000, 0, 1) == CW_NONE); /* no phone */
    CHECK(cw_session_update(&s, &g, 1000, 1, 1) == CW_NEGOTIATE);
    epoch = s.epoch;
    CHECK(s.phase == CW_WAIT_VIDEO);
    CHECK(cw_session_frame(&s, epoch - 1, 1000, 960, 640, 1, 1) == CW_NONE);
    CHECK(cw_session_frame(&s, epoch, 1000, 960, 640, 0, 1) == CW_NONE);
    CHECK(cw_session_frame(&s, epoch, 1000, 960, 640, 1, 1) == CW_SHOW_CARPLAY);
    CHECK(cw_session_frame(&s, epoch, 1001, 960, 640, 0, 1) == CW_NONE);
    CHECK(cw_session_update(&s, &g, 1001, 1, 1) == CW_NONE);
    /* New phone session restores OEM before asking for a new stream. */
    CHECK(cw_session_update(&s, &g, 1001, 2, 1) == (CW_STOP_VIDEO | CW_RESTORE_OEM | CW_NEGOTIATE));
    CHECK(cw_session_frame(&s, epoch, 1001, 960, 640, 1, 1) == CW_NONE);
    CHECK(cw_session_frame(&s, s.epoch, 1001, 960, 640, 1, 1) == CW_SHOW_CARPLAY);
    g.x = 50; g.area_width = 870;
    CHECK(cw_session_update(&s, &g, 1001, 2, 1) == (CW_STOP_VIDEO | CW_RESTORE_OEM | CW_NEGOTIATE));
    CHECK(cw_session_frame(&s, s.epoch, 1001, 960, 640, 1, 1) == CW_SHOW_CARPLAY);
    g.carplay_active = 0;
    CHECK(cw_session_update(&s, &g, 1001, 2, 1) == (CW_STOP_VIDEO | CW_RESTORE_OEM));
    CHECK(cw_session_update(&s, &g, 1001, 2, 1) == CW_NONE);
    g.carplay_active = 1;
    CHECK(cw_session_update(&s, &g, 1001, 3, 1) == CW_NEGOTIATE);
    CHECK(cw_session_frame(&s, s.epoch, 1001, 800, 298, 1, 1) == CW_STOP_VIDEO);
    CHECK(cw_session_update(&s, &g, 1001, 3, 1) == CW_NEGOTIATE);
    CHECK(cw_session_frame(&s, s.epoch, 1001, 960, 640, 1, 0) == CW_STOP_VIDEO);
    CHECK(cw_session_update(&s, &g, 1001, 3, 1) == CW_NEGOTIATE);
    CHECK(cw_session_frame(&s, s.epoch, 1001, 960, 640, 1, 1) == CW_SHOW_CARPLAY);
    CHECK(cw_session_update(&s, &g, 1006, 3, 1) == (CW_STOP_VIDEO | CW_RESTORE_OEM));
    g.timestamp = 1006;
    CHECK(cw_session_update(&s, &g, 1006, 3, 1) == CW_NEGOTIATE);
    CHECK(cw_session_frame(&s, s.epoch, 1006, 960, 640, 1, 1) == CW_SHOW_CARPLAY);
    g.timestamp = 1012;
    CHECK(cw_session_update(&s, &g, 1012, 3, 1) == (CW_STOP_VIDEO | CW_RESTORE_OEM));
    CHECK(cw_session_stop(&s) == CW_NONE);
    if (argc == 2) {
        /* Parse a real record produced by the Java observer fixture. */
        CHECK(cw_geometry_read(argv[1], 0xffffffffU, &g) == 0); /* expired */
        FILE *file = fopen(argv[1], "rb");
        unsigned generation, timestamp;
        CHECK(file != NULL);
        CHECK(fscanf(file, "CWCP3 %u %u", &generation, &timestamp) == 2);
        fclose(file);
        CHECK(cw_geometry_read(argv[1], timestamp, &g));
        CHECK(!g.carplay_active && g.width == 960 && g.height == 640);
    }
    printf("PORSCHE_SESSION_PASS checks=%u\n", checks);
    return 0;
}
