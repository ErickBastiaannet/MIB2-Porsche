#ifndef CW_PORSCHE_WINDOW_LOADER_H
#define CW_PORSCHE_WINDOW_LOADER_H
#include "porsche_window.h"
typedef struct {
    cw_window_api api;
    void *native_library, *egl_library, *gles_library;
} cw_window_libraries;
int cw_window_load(cw_window_libraries *);
void cw_window_unload(cw_window_libraries *);
#endif
