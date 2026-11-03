#include "porsche_window.h"
#include <string.h>

/* Khronos EGL 1.4 / GLES2 constants, also present in the QNX 6.5 SDK. */
enum {
    EGL_NONE_VALUE = 0x3038,
    EGL_SURFACE_TYPE_VALUE = 0x3033,
    EGL_WINDOW_BIT_VALUE = 4,
    EGL_RED_SIZE_VALUE = 0x3024,
    EGL_GREEN_SIZE_VALUE = 0x3023,
    EGL_BLUE_SIZE_VALUE = 0x3022,
    EGL_ALPHA_SIZE_VALUE = 0x3021,
    EGL_RENDERABLE_TYPE_VALUE = 0x3040,
    EGL_ES2_BIT_VALUE = 4,
    EGL_ES_API_VALUE = 0x30a0,
    EGL_CLIENT_VERSION_VALUE = 0x3098,
    EGL_WIDTH_VALUE = 0x3057,
    EGL_HEIGHT_VALUE = 0x3056,
    GL_SCISSOR_VALUE = 0x0c11,
    GL_COLOR_BUFFER_VALUE = 0x4000
};

void cw_window_stop(cw_window *s) {
    if (!s)
        return;
    if (s->egl_started && s->api.make_current)
        (void)s->api.make_current(s->display, 0, 0, 0);
    if (s->context && s->api.destroy_context)
        (void)s->api.destroy_context(s->display, s->context);
    if (s->surface && s->api.destroy_surface)
        (void)s->api.destroy_surface(s->display, s->surface);
    if (s->kd_window && s->api.destroy_window)
        s->api.destroy_window(s->kd_window);
    if (s->egl_started && s->api.terminate)
        (void)s->api.terminate(s->display);
    if (s->display_started && s->api.display_deinit)
        s->api.display_deinit();
    memset(s, 0, sizeof(*s));
}

static int complete(const cw_window_api *a) {
    return a && a->display_init && a->display_deinit && a->create_window && a->destroy_window &&
           a->window_size && a->get_display && a->initialize && a->choose_config && a->bind_api &&
           a->create_surface && a->create_context && a->make_current && a->query_surface &&
           a->swap_buffers && a->destroy_context && a->destroy_surface && a->terminate &&
           a->viewport && a->scissor && a->enable && a->disable && a->clear_color && a->clear &&
           a->gl_error;
}

int cw_window_start(cw_window *s, const cw_window_api *a, unsigned w, unsigned h, unsigned layer) {
    static const int config_attributes[] = {EGL_SURFACE_TYPE_VALUE,
                                            EGL_WINDOW_BIT_VALUE,
                                            EGL_RED_SIZE_VALUE,
                                            1,
                                            EGL_GREEN_SIZE_VALUE,
                                            1,
                                            EGL_BLUE_SIZE_VALUE,
                                            1,
                                            EGL_ALPHA_SIZE_VALUE,
                                            1,
                                            EGL_RENDERABLE_TYPE_VALUE,
                                            EGL_ES2_BIT_VALUE,
                                            EGL_NONE_VALUE};
    static const int context_attributes[] = {EGL_CLIENT_VERSION_VALUE, 2, EGL_NONE_VALUE};
    void *config = 0, *native_window = 0;
    int count = 0, size[2] = {0, 0}, sw = 0, sh = 0;
    if (!s || s->display_started || s->display || s->surface || s->context || s->kd_window ||
        !complete(a) || w < 64 || h < 64 || w > 1920 || h > 1080 || layer != 78)
        return 0;
    s->api = *a;
    s->width = w;
    s->height = h;
    a->display_init(0, 0);
    s->display_started = 1;
    s->display = a->get_display(0);
    if (!s->display)
        goto failed;
    if (!a->initialize(s->display, 0, 0))
        goto failed;
    s->egl_started = 1;
    if (!a->choose_config(s->display, config_attributes, &config, 1, &count) || count != 1 ||
        !config)
        goto failed;
    if (a->create_window(s->display, config, (int)w, (int)h, (int)layer, &native_window,
                         &s->kd_window) != 1 ||
        !native_window || !s->kd_window)
        goto failed;
    /* Firmware libdisplayinit uses KD property 66 for the native window size. */
    if (a->window_size(s->kd_window, 66, size) || size[0] != (int)w || size[1] != (int)h)
        goto failed;
    s->surface = a->create_surface(s->display, config, native_window, 0);
    if (!s->surface || !a->bind_api(EGL_ES_API_VALUE))
        goto failed;
    s->context = a->create_context(s->display, config, 0, context_attributes);
    if (!s->context || !a->make_current(s->display, s->surface, s->surface, s->context))
        goto failed;
    if (!a->query_surface(s->display, s->surface, EGL_WIDTH_VALUE, &sw) ||
        !a->query_surface(s->display, s->surface, EGL_HEIGHT_VALUE, &sh) || sw != (int)w ||
        sh != (int)h)
        goto failed;
    a->viewport(0, 0, (int)w, (int)h);
    if (!cw_window_bars(s))
        goto failed;
    return 1;
failed:
    cw_window_stop(s);
    return 0;
}

int cw_window_bars(cw_window *s) {
    static const float colors[8][3] = {{1, 1, 1}, {1, 1, 0}, {0, 1, 1}, {0, 1, 0},
                                       {1, 0, 1}, {1, 0, 0}, {0, 0, 1}, {0, 0, 0}};
    unsigned i;
    if (!s || !s->context || !s->surface || !s->width || !s->height)
        return 0;
    s->api.enable(GL_SCISSOR_VALUE);
    for (i = 0; i < 8; ++i) {
        unsigned x = i * s->width / 8, end = (i + 1) * s->width / 8;
        s->api.scissor((int)x, 0, (int)(end - x), (int)s->height);
        s->api.clear_color(colors[i][0], colors[i][1], colors[i][2], 1);
        s->api.clear(GL_COLOR_BUFFER_VALUE);
    }
    s->api.disable(GL_SCISSOR_VALUE);
    return !s->api.gl_error() && s->api.swap_buffers(s->display, s->surface);
}
