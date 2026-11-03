#ifndef CW_PORSCHE_YUV_CAPTURE_H
#define CW_PORSCHE_YUV_CAPTURE_H
#include "porsche_yuv.h"

/* Only for our standalone decoder executable, exported with -Wl,-E.
 * Never preload this into DIO, HMI or the primary CarPlay process.
 * Stop/close NvSS before closing the capture object. */
int cw_yuv_capture_open(cw_yuv_mailbox *, const char *nvmedia_path);
/* Diagnostic only: obtain decode-order pixels before the vendor output mixer.
 * Does not establish presentation order. Do not use for a general H264 stream. */
int cw_yuv_capture_open_decoder(cw_yuv_mailbox *, const char *nvmedia_path);
int cw_yuv_capture_open_parser(cw_yuv_mailbox *, const char *nvmedia_path);
void cw_yuv_capture_close(void);
#endif
