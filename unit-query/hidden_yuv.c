/* Separate, bounded hardware diagnostic. Never declares or switches a context. */
#include "porsche_nvss.h"
#include "porsche_dm.h"
#include "porsche_yuv_capture.h"
#include "porsche_pixels.h"

#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

static unsigned be32(const unsigned char *p) {
    return ((unsigned)p[0] << 24) | ((unsigned)p[1] << 16) | ((unsigned)p[2] << 8) | p[3];
}
int cw_hidden_yuv(int argc, char **argv, cw_pixels *output) {
    cw_yuv_mailbox mailbox;

    unsigned char *pixels = NULL;
    uint64_t sequence = 0;
    unsigned attempt;
    cw_nvss sink;
    cw_nvss_api api;
    cw_display before, after;
    void *library = NULL;
    FILE *file = NULL;
    unsigned char header[20], *config = NULL, *frame = NULL;
    unsigned w, h, cs, fs;
    int result = 1;
    char report[8192];
    memset(&sink, 0, sizeof(sink));
    memset(&mailbox, 0, sizeof(mailbox));
    alarm(12);
    if (argc != 3)
        return 2;
    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &before))
        goto done;
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 79, before.width, before.height, 0))
        goto done;

    file = fopen(argv[2], "rb");
    if (!file || fread(header, 1, sizeof(header), file) != sizeof(header) ||
        memcmp(header, "CWNV", 4))
        goto done;
    w = be32(header + 4);
    h = be32(header + 8);
    cs = be32(header + 12);
    fs = be32(header + 16);
    if (w != before.width || h != before.height || cs > 4096 || !cs || fs > 1024 * 1024 || !fs)
        goto done;
    config = malloc(cs);
    frame = malloc(fs);
    if (!config || !frame)
        goto done;
    if (fread(config, 1, cs, file) != cs || fread(frame, 1, fs, file) != fs || fgetc(file) != EOF)
        goto done;

    if (!cw_yuv_open(&mailbox, w, h) ||
        !cw_yuv_capture_open_parser(&mailbox, "/mnt/app/armle/usr/lib/libnvmedia.so")) {
        puts("YUV_CAPTURE_LIBRARY_REJECTED");
        goto done;
    }
    pixels = malloc(mailbox.size);
    if (!pixels)
        goto done;
    library = dlopen("libnvss_video.so", RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        printf("NVSS_LIBRARY_UNAVAILABLE: %s\n", dlerror());
        goto done;
    }
    api.open = (int32_t (*)(void **, const cw_nvss_open *))dlsym(library, "NvSSVideoOpen");
    api.configure =
        (int32_t (*)(void *, const cw_nvss_stream *))dlsym(library, "NvSSVideoStreamConfigure");
    api.decode =
        (int32_t (*)(void *, const cw_nvss_unit *, uint32_t))dlsym(library, "NvSSVideoDecode");
    api.close = (int32_t (*)(void *))dlsym(library, "NvSSVideoClose");
    puts("HIDDEN_DECODE_BEGIN");
    fflush(stdout);
    if (!cw_nvss_start_hidden(&sink, &api, w, h, 79, 0, config, cs)) {
        puts("HIDDEN_START_REJECTED");
        goto done;
    }
    for (attempt = 0; attempt < 20 && !sequence; ++attempt) {
        struct timespec delay = {0, 50000000};
        if (cw_nvss_frame(&sink, frame, fs, attempt * 40000ULL) != 1)
            goto done;
        nanosleep(&delay, NULL);
        (void)cw_yuv_take(&mailbox, pixels, mailbox.size, &sequence);
    }
    if (!sequence) {
        puts("YUV_NO_DECODED_PIXELS");
        goto done;
    }
    {
        size_t i;
        uint32_t checksum = 2166136261U;
        unsigned minimum = 255, maximum = 0;
        for (i = 0; i < mailbox.size; ++i)
            checksum = (checksum ^ pixels[i]) * 16777619U;
        for (i = 0; i < (size_t)w * h; ++i) {
            if (pixels[i] < minimum)
                minimum = pixels[i];
            if (pixels[i] > maximum)
                maximum = pixels[i];
        }
        printf("YUV_DECODED_PIXELS %ux%u bytes=%lu checksum=%08x luma=%u..%u\n", w, h,
               (unsigned long)mailbox.size, checksum, minimum, maximum);
    }
    if (output && !cw_pixels_write(output, pixels, mailbox.size))
        goto done;
    cw_nvss_stop(&sink);

    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &after) ||
        before.id != after.id || before.context != after.context || before.width != after.width ||
        before.height != after.height)
        goto done;
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) || !cw_dm_layer(report, 79, w, h, 0)) {
        puts("HIDDEN_LAYER_REMAINS");
        goto done;
    }
    puts("HIDDEN_YUV_PASS_CONTEXT_UNCHANGED");
    result = 0;
done:
    cw_nvss_stop(&sink);
    if (library)
        dlclose(library);

    cw_yuv_capture_close();
    cw_yuv_close(&mailbox);
    free(pixels);
    if (file)
        fclose(file);
    free(config);
    free(frame);
    return result;
}

#ifndef CW_HIDDEN_YUV_LIBRARY
int main(int argc, char **argv) { return cw_hidden_yuv(argc, argv, NULL); }
#endif
