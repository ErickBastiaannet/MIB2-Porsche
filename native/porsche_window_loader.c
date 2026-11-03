#include "porsche_window_loader.h"
#include <dlfcn.h>
#include <string.h>

void cw_window_unload(cw_window_libraries *l) {
    if (!l)
        return;
    if (l->gles_library)
        dlclose(l->gles_library);
    if (l->egl_library)
        dlclose(l->egl_library);
    if (l->native_library)
        dlclose(l->native_library);
    memset(l, 0, sizeof(*l));
}

int cw_window_load(cw_window_libraries *l) {
    if (!l || l->native_library || l->egl_library || l->gles_library)
        return 0;
    /* Keep the vendor platform loader global: EGL resolves its KD symbols. */
    l->native_library = dlopen("libdisplayinit.so", RTLD_NOW | RTLD_GLOBAL);
    if (!l->native_library)
        goto failed;
    l->egl_library = dlopen("libEGL.so", RTLD_NOW | RTLD_LOCAL);
    if (!l->egl_library)
        goto failed;
    l->gles_library = dlopen("libGLESv2.so", RTLD_NOW | RTLD_LOCAL);
    if (!l->gles_library)
        goto failed;
#define LOAD(field, library, symbol)                                                               \
    do {                                                                                           \
        l->api.field = (__typeof__(l->api.field))dlsym(l->library, symbol);                        \
        if (!l->api.field)                                                                         \
            goto failed;                                                                           \
    } while (0)
    LOAD(display_init, native_library, "display_init");
    LOAD(display_deinit, native_library, "display_deinit");
    LOAD(create_window, native_library, "display_create_window");
    LOAD(destroy_window, native_library, "display_destroy_window");
    LOAD(window_size, native_library, "kdGetWindowPropertyiv");
    LOAD(get_display, egl_library, "eglGetDisplay");
    LOAD(initialize, egl_library, "eglInitialize");
    LOAD(choose_config, egl_library, "eglChooseConfig");
    LOAD(bind_api, egl_library, "eglBindAPI");
    LOAD(create_surface, egl_library, "eglCreateWindowSurface");
    LOAD(create_context, egl_library, "eglCreateContext");
    LOAD(make_current, egl_library, "eglMakeCurrent");
    LOAD(query_surface, egl_library, "eglQuerySurface");
    LOAD(swap_buffers, egl_library, "eglSwapBuffers");
    LOAD(destroy_context, egl_library, "eglDestroyContext");
    LOAD(destroy_surface, egl_library, "eglDestroySurface");
    LOAD(terminate, egl_library, "eglTerminate");
    LOAD(viewport, gles_library, "glViewport");
    LOAD(scissor, gles_library, "glScissor");
    LOAD(enable, gles_library, "glEnable");
    LOAD(disable, gles_library, "glDisable");
    LOAD(clear_color, gles_library, "glClearColor");
    LOAD(clear, gles_library, "glClear");
    LOAD(gl_error, gles_library, "glGetError");
#undef LOAD
    return 1;
failed:
    cw_window_unload(l);
    return 0;
}
