#ifndef CW_PORSCHE_PIXELS_H
#define CW_PORSCHE_PIXELS_H
#include <stddef.h>
#include <stdint.h>
typedef struct { void *mapping; size_t size; } cw_pixels;
/* Anonymous shared memory, created BEFORE forking either GPU user. One writer,
 * one reader, fixed-size I420. No persistent file and no process-shared lock. */
int cw_pixels_open(cw_pixels *, unsigned width, unsigned height);
int cw_pixels_write(cw_pixels *, const uint8_t *, size_t);
/* Never waits for the writer. A writer dying halfway through a frame cannot
 * hang the renderer. A false return means the output must not be displayed. */
int cw_pixels_read(cw_pixels *, uint8_t *, size_t, uint32_t *sequence);
void cw_pixels_close(cw_pixels *);
#endif
