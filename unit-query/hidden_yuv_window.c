/* Full decoder -> shared memory -> EGL path; never switches a display. */
#define _POSIX_C_SOURCE 200809L
#include "porsche_pixels.h"
#include "porsche_yuv_gl.h"
#include "porsche_window_loader.h"
#include "porsche_dm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>
int cw_hidden_yuv(int, char **, cw_pixels *);

int main(int argc, char **argv) {
    cw_pixels channel = {0};
    cw_window window;
    cw_window_libraries libraries;
    cw_yuv_gl renderer = {0};
    cw_display before, after;
    char report[16384];
    uint8_t *pixels = NULL, rgba[4];
    uint32_t sequence = 0;
    size_t bytes;
    pid_t decoder = -1;
    int status, result = 1;
    memset(&window, 0, sizeof(window));
    memset(&libraries, 0, sizeof(libraries));
    alarm(25);
    if (argc != 3)
        return 2;
    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &before) ||
        !cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 0) ||
        !cw_pixels_open(&channel, before.width, before.height))
        goto done;
    bytes = (size_t)before.width * before.height * 3 / 2;
    pixels = malloc(bytes);
    if (!pixels)
        goto done;
    fflush(NULL);
    decoder = fork(); /* no GPU library has been loaded in this process */
    if (decoder == 0) {
        int code = cw_hidden_yuv(argc, argv, &channel);
        fflush(NULL);
        cw_pixels_close(&channel);
        _exit(code);
    }
    if (decoder < 0)
        goto done;
    if (waitpid(decoder, &status, 0) != decoder)
        goto done;
    decoder = -1;
    if (!WIFEXITED(status) || WEXITSTATUS(status) ||
        !cw_pixels_read(&channel, pixels, bytes, &sequence))
        goto done;
    if (!cw_window_load(&libraries) ||
        !cw_window_start(&window, &libraries.api, before.width, before.height, 78) ||
        !cw_yuv_gl_start(&renderer, &window, libraries.gles_library) ||
        !cw_yuv_gl_draw_sample(&renderer, pixels, bytes, rgba))
        goto done;
    printf("YUV_WINDOW_RENDERED_RGBA %u %u %u %u\n", rgba[0], rgba[1], rgba[2], rgba[3]);
    if (!cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 1))
        goto done;
    cw_yuv_gl_stop(&renderer);
    cw_window_stop(&window);
    cw_window_unload(&libraries);
    if (!cw_dm_query(argv[1], "gs", report, sizeof(report)) || !cw_dm_display(report, &after) ||
        before.id != after.id || before.context != after.context ||
        before.width != after.width || before.height != after.height ||
        !cw_dm_query(argv[1], "gd", report, sizeof(report)) ||
        !cw_dm_layer(report, 78, before.width, before.height, 0) ||
        !cw_dm_layer(report, 79, before.width, before.height, 0))
        goto done;
    puts("HIDDEN_YUV_WINDOW_PASS_CONTEXT_UNCHANGED");
    result = 0;
done:
    if (decoder > 0) {
        kill(decoder, SIGKILL);
        waitpid(decoder, NULL, 0);
    }
    cw_yuv_gl_stop(&renderer);
    cw_window_stop(&window);
    cw_window_unload(&libraries);
    cw_pixels_close(&channel);
    free(pixels);
    return result;
}
