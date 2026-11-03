#ifndef CW_PORSCHE_WIRE_H
#define CW_PORSCHE_WIRE_H
#include <stddef.h>
#include <stdint.h>
uint32_t cw_crc32(const char *data, size_t length);
int cw_wire_read(const char *path, const char *magic, uint32_t *values, unsigned count);
int cw_wire_write(const char *path, const char *magic, const uint32_t *values, unsigned count);
#endif
