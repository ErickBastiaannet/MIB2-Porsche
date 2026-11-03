#include "porsche_geometry.h"
#include <stdio.h>

/* A reader of our own volatile observation only; never opens an OEM device. */
int cw_geometry_read(const char *path, uint32_t now, cw_geometry *out) {
    char bytes[257];
    size_t length;
    int status;
    FILE *file = fopen(path, "rb");
    if (!file)
        return 0;
    length = fread(bytes, 1, sizeof(bytes), file);
    status = ferror(file);
    fclose(file);
    if (status || length == sizeof(bytes))
        return 0;
    return cw_geometry_parse(bytes, length, now, out);
}
