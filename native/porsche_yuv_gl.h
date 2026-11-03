#ifndef CW_PORSCHE_YUV_GL_H
#define CW_PORSCHE_YUV_GL_H
#include "porsche_window.h"
#include <stddef.h>

/* Private GLES state; must be stopped while its window context is current. */
typedef struct {
    void *implementation;
} cw_yuv_gl;
int cw_yuv_gl_start(cw_yuv_gl *, cw_window *, void *gles_library);
/* Packed I420: full Y plane, then U, then V; dimensions equal the window. */
int cw_yuv_gl_draw(cw_yuv_gl *, const unsigned char *, size_t size);
/* Diagnostic: read one rendered centre pixel before swap. Normal draws do not
 * perform a GPU readback. The caller supplies four bytes of RGBA storage. */
int cw_yuv_gl_draw_sample(cw_yuv_gl *, const unsigned char *, size_t, unsigned char rgba[4]);
void cw_yuv_gl_stop(cw_yuv_gl *);
#endif
