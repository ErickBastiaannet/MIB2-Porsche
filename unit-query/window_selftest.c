/* Hardware registration test only. Never declares/switches a context. */
#include "porsche_window.h"
#include "porsche_window_loader.h"
#include "porsche_dm.h"
#include "porsche_sha256.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    cw_window window;
    cw_window_libraries libraries;
    cw_display before, after;
    char report[16384], digest[65];
    unsigned backend;
    int result = 1, created = 0;
    memset(&window, 0, sizeof(window));
    memset(&libraries, 0, sizeof(libraries));
    if (argc != 3 || strcmp(argv[2], "--window-selftest"))
        return 2;
    alarm(12);
    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &before) ||
        !cw_map_context((unsigned)before.context) || !cw_dm_backend_id(before.id, &backend)) {
        puts("WINDOW_SELFTEST_DISPLAY_PROFILE_REJECTED");
        goto done;
    }
    if (!cw_sha256_file("/eso/lib/libdisplayinit.so", digest) ||
        strcmp(digest, "938efc826f7023869b44db49b1270e6235fe4564a0ca903881a41fe2c7f1a3c7")) {
        puts("WINDOW_SELFTEST_VENDOR_LIBRARY_REJECTED");
        goto done;
    }
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 0)) {
        puts("WINDOW_SELFTEST_LAYER_NOT_FREE");
        goto done;
    }
    if (!cw_window_load(&libraries)) {
        puts("WINDOW_SELFTEST_GRAPHICS_LIBRARY_UNAVAILABLE");
        goto done;
    }
    if (!cw_window_start(&window, &libraries.api, before.width, before.height, 78)) {
        puts("WINDOW_SELFTEST_CREATE_FAILED");
        goto done;
    }
    created = 1;
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 1)) {
        puts("WINDOW_SELFTEST_REGISTRATION_FAILED");
        puts(report);
        goto done;
    }
    printf("WINDOW_REGISTERED report_index=%u backend_id=%u size=%ux%u layer=78\n", before.id,
           backend, before.width, before.height);
    cw_window_stop(&window);
    created = 0;
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 0) ||
        !cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &after) ||
        before.id != after.id || before.context != after.context || before.width != after.width ||
        before.height != after.height) {
        puts("WINDOW_SELFTEST_CLEANUP_OR_CONTEXT_CHECK_FAILED");
        goto done;
    }
    puts("WINDOW_SELFTEST_PASS_CONTEXT_UNCHANGED");
    result = 0;
done:
    if (created)
        cw_window_stop(&window);
    cw_window_unload(&libraries);
    return result;
}
