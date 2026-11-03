#include "porsche_nvss.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned opens, closes, decodes, configs;
static int failure;
static unsigned expected_visible = 1;
static const unsigned char config[] = {1,66,0,30,255,225,0,2,0x67,0x42,1,0,2,0x68,0x11};
static int32_t mock_open(void **handle, const cw_nvss_open *params) {
    assert(params->layer_id == 78 && params->output_device == 0 && params->queue_depth == 8);
    assert(params->priority == 100 && params->visible == expected_visible);
    ++opens;
    if (failure == 1) return 1;
    *handle = (void *)1;
    return 0;
}
static int32_t mock_configure(void *handle, const cw_nvss_stream *params) {
    assert(handle == (void *)1 && params->width == 960 && params->height == 640 && params->fps == 25.0f);
    ++configs; return failure == 2;
}
static int32_t mock_decode(void *handle, const cw_nvss_unit *unit, uint32_t timeout) {
    static const unsigned char prefix[] = {0,0,0,1};
    assert(handle == (void *)1 && timeout == 40);
    assert(unit->size >= 5 && !memcmp(unit->data, prefix, 4));
    assert(!unit->append_markers);
    ++decodes; return failure == 3;
}
static int32_t mock_close(void *handle) {
    assert(handle == (void *)1); ++closes; return 0;
}
int main(void) {
    cw_nvss sink;
    cw_nvss_api api = {mock_open, mock_configure, mock_decode, mock_close};
    const unsigned char pframe[] = {0,0,0,2,0x41,0xaa};
    const unsigned char idr[] = {0,0,0,2,0x65,0xbb};
    const unsigned char bad[] = {0xff,0xff,0xff,0xff,0x65};
    unsigned old;
    unsigned char high_profile[sizeof(config) + 4];
    static const unsigned char observed_airplay_config[] = {
        0x01,0x64,0x00,0x1f,0xff,0xe1,0x00,0x14,0x27,0x64,0x00,0x1f,0xac,
        0x13,0x14,0x50,0x32,0x0f,0x69,0xb8,0x08,0x68,0x30,0x36,0x82,0x21,
        0x19,0x60,0x01,0x00,0x04,0x28,0xee,0x3c,0xb0,0x02,0x00,0x00,0x00
    };
    unsigned char invalid_airplay_config[sizeof(observed_airplay_config)];
    size_t n;
    memset(&sink, 0, sizeof(sink));
    assert(!cw_nvss_start(&sink, &api, 960, 640, 59, 0, config, sizeof(config))); /* primary display forbidden */
    assert(!opens);
    for (n = 0; n < sizeof(config); ++n) {
        assert(!cw_nvss_start(&sink, &api, 960, 640, 78, 0, config, n));
        assert(!sink.handle && !sink.buffer);
    }
    assert(!opens);
    for (failure = 1; failure <= 3; ++failure) {
        assert(!cw_nvss_start(&sink, &api, 960, 640, 78, 0, config, sizeof(config)));
        assert(!sink.handle && !sink.buffer);
    }
    assert(opens == 3 && closes == 2);
    failure = 0;
    assert(cw_nvss_start(&sink, &api, 960, 640, 78, 0, config, sizeof(config)));
    assert(!cw_nvss_start(&sink, &api, 960, 640, 78, 0, config, sizeof(config)));
    old = decodes;
    assert(cw_nvss_frame(&sink, pframe, sizeof(pframe), 1) == 0 && decodes == old);
    assert(cw_nvss_frame(&sink, bad, sizeof(bad), 1) == -1 && decodes == old);
    assert(cw_nvss_frame(&sink, idr, sizeof(idr), 1) == 1 && decodes == old + 1);
    assert(cw_nvss_frame(&sink, pframe, sizeof(pframe), 2) == 1 && decodes == old + 2);
    assert(idr[3] == 2 && idr[4] == 0x65); /* caller input not altered */
    failure = 3;
    assert(cw_nvss_frame(&sink, idr, sizeof(idr), 3) == -1);
    cw_nvss_stop(&sink); cw_nvss_stop(&sink);
    assert(opens == 4 && closes == 3 && !sink.handle && !sink.buffer);
    failure = 0;
    memcpy(high_profile, config, sizeof(config)); high_profile[1] = 100;
    high_profile[sizeof(config)] = 0xfd;
    high_profile[sizeof(config) + 1] = 0xf8;
    high_profile[sizeof(config) + 2] = 0xf8;
    high_profile[sizeof(config) + 3] = 0;
    assert(cw_nvss_start(&sink, &api, 960, 640, 78, 0, high_profile, sizeof(high_profile)));
    cw_nvss_stop(&sink);
    assert(cw_nvss_start(&sink, &api, 960, 640, 78, 0, observed_airplay_config,
                         sizeof(observed_airplay_config)));
    cw_nvss_stop(&sink);
    memcpy(invalid_airplay_config, observed_airplay_config, sizeof(invalid_airplay_config));
    invalid_airplay_config[sizeof(invalid_airplay_config) - 1] = 1;
    assert(!cw_nvss_start(&sink, &api, 960, 640, 78, 0, invalid_airplay_config,
                          sizeof(invalid_airplay_config)));
    expected_visible = 0;
    assert(cw_nvss_start_hidden(&sink, &api, 960, 640, 78, 0, config, sizeof(config)));
    cw_nvss_stop(&sink);
    puts("PORSCHE_NVSS_PASS config parsing, Annex-B conversion, IDR gate, protected primary layer, hidden diagnostic, decoder failure cleanup");
    return 0;
}
