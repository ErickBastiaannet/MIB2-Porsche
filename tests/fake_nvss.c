/* Test double only; this library is never included in an SD package. */
#include "porsche_nvss.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int32_t NvSSVideoOpen(void **handle,const cw_nvss_open *settings) {
    FILE *file;
    if(settings->layer_id!=78||settings->output_device>1)return -1;
    file=fopen("/tmp/cw-runtime/window","wb");if(!file)return -1;fclose(file);
    *handle=malloc(1);return *handle?0:-1;
}
int32_t NvSSVideoStreamConfigure(void *handle,const cw_nvss_stream *settings) {
    return handle&&settings->width==960&&settings->height==640?0:-1;
}
int32_t NvSSVideoDecode(void *handle,const cw_nvss_unit *unit,uint32_t timeout) {
    return handle&&unit->data&&unit->size&&timeout==40?0:-1;
}
int32_t NvSSVideoClose(void *handle) {
    free(handle);unlink("/tmp/cw-runtime/window");return 0;
}
