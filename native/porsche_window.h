#ifndef CW_PORSCHE_WINDOW_H
#define CW_PORSCHE_WINDOW_H

/* Opaque EGL/KD handles. QNX EGLNativeDisplayType is int; the remaining
 * native handles are pointers. No foreign-platform graphics headers required. */
typedef struct {
    void (*display_init)(int *, int *);
    void (*display_deinit)(void);
    int (*create_window)(void *, void *, int, int, int, void **, int *);
    void (*destroy_window)(int);
    int (*window_size)(int, int, int *);
    void *(*get_display)(int);
    unsigned (*initialize)(void *, int *, int *);
    unsigned (*choose_config)(void *, const int *, void **, int, int *);
    unsigned (*bind_api)(unsigned);
    void *(*create_surface)(void *, void *, void *, const int *);
    void *(*create_context)(void *, void *, void *, const int *);
    unsigned (*make_current)(void *, void *, void *, void *);
    unsigned (*query_surface)(void *, void *, int, int *);
    unsigned (*swap_buffers)(void *, void *);
    unsigned (*destroy_context)(void *, void *);
    unsigned (*destroy_surface)(void *, void *);
    unsigned (*terminate)(void *);
    void (*viewport)(int, int, int, int);
    void (*scissor)(int, int, int, int);
    void (*enable)(unsigned);
    void (*disable)(unsigned);
    void (*clear_color)(float, float, float, float);
    void (*clear)(unsigned);
    unsigned (*gl_error)(void);
} cw_window_api;

typedef struct {
    cw_window_api api;
    void *display, *surface, *context;
    int kd_window;
    unsigned width, height;
    unsigned display_started, egl_started;
} cw_window;

/* Creates a compositor-owned window. Never opens a hardware video output,
 * switches a display, declares a context, or changes any persistent setting. */
int cw_window_start(cw_window *, const cw_window_api *, unsigned width, unsigned height,
                    unsigned layer);
int cw_window_bars(cw_window *);
void cw_window_stop(cw_window *);
#endif
