/* Reuse the already checked EGL test-double ABI, never shipped to the car. */
#define main cw_window_unused_fixture_main
#include "test_window.c"
#undef main
#include "porsche_window_loader.h"
#include <unistd.h>

static int allocate(void *d,void *cfg,int w,int h,int layer,void **native,int *window){
    FILE *f;int ok=create_window(d,cfg,w,h,layer,native,window);
    if(!ok)return 0;
    f=fopen("/tmp/cw-runtime/window","wb");if(!f)return 0;fclose(f);return 1;
}
static void release(int w){destroy_window(w);unlink("/tmp/cw-runtime/window");}
int cw_window_load(cw_window_libraries *l){
    memset(l,0,sizeof(*l));l->api=api;l->api.create_window=allocate;l->api.destroy_window=release;return 1;
}
void cw_window_unload(cw_window_libraries *l){memset(l,0,sizeof(*l));}
