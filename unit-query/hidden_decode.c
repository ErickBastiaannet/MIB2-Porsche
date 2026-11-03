/* Separate, bounded hardware diagnostic. Never declares or switches a context. */
#include "porsche_nvss.h"
#include "porsche_dm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

static unsigned be32(const unsigned char *p) {
    return ((unsigned)p[0] << 24) | ((unsigned)p[1] << 16) | ((unsigned)p[2] << 8) | p[3];
}
int main(int argc, char **argv) {
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
    alarm(8);
    if (argc != 3)
        return 2;
    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &before))
        goto done;
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 0))
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
    if (!cw_nvss_start_hidden(&sink, &api, w, h, 78, 0, config, cs)) {
        puts("HIDDEN_START_REJECTED");
        goto done;
    }
    if (cw_nvss_frame(&sink, frame, fs, 0) != 1) {
        puts("HIDDEN_FRAME_REJECTED");
        goto done;
    }
    puts("HIDDEN_FRAME_ACCEPTED");
    cw_nvss_stop(&sink);
    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &after) ||
        before.id != after.id || before.context != after.context || before.width != after.width ||
        before.height != after.height)
        goto done;
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) || !cw_dm_layer(report, 78, w, h, 0)) {
        puts("HIDDEN_LAYER_REMAINS");
        goto done;
    }
    puts("HIDDEN_DECODE_PASS_CONTEXT_UNCHANGED");
    result = 0;
done:
    cw_nvss_stop(&sink);
    if (library)
        dlclose(library);
    if (file)
        fclose(file);
    free(config);
    free(frame);
    return result;
}
