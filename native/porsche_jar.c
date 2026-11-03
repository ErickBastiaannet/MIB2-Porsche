#include "porsche_jar.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned little16(const unsigned char *p) { return p[0] | ((unsigned)p[1] << 8); }
static unsigned long little32(const unsigned char *p) {
    return little16(p) | ((unsigned long)little16(p + 2) << 16);
}
int cw_jar_compatible(const char *path) {
    static const char *conflicts[] = {
        "de/audi/tghu/navi/app/map/gui/layout/LayoutProviderG22Kombi.class",
        "de/audi/tghu/navi/app/cluster/ClusterService.class",
        "de/audi/app/terminalmode/smartphone/carplay/CarPlayDSIManager.class",
        "de/audi/tghu/fwhmi/DisplayManagerMIB2High.class",
        "org/connectwow/carplay/PorscheCluster.class",
        "org/connectwow/carplay/PorscheGeometry.class"};
    FILE *file = fopen(path, "rb");
    unsigned char *tail = NULL, header[46];
    long length, start, end;
    unsigned count, i, j;
    int result = 0;
    if (!file)
        return 0;
    if (fseek(file, 0, SEEK_END) || (length = ftell(file)) < 22 || length > 256L * 1024 * 1024)
        goto done;
    start = length > 65557 ? length - 65557 : 0;
    tail = malloc((size_t)(length - start));
    if (!tail || fseek(file, start, SEEK_SET) ||
        fread(tail, 1, (size_t)(length - start), file) != (size_t)(length - start))
        goto done;
    end = length - start - 22;
    for (; end >= 0; --end) {
        if (!memcmp(tail + end, "PK\005\006", 4) &&
            end + 22 + (long)little16(tail + end + 20) == length - start)
            break;
    }
    if (end < 0 || little16(tail + end + 4) || little16(tail + end + 6))
        goto done;
    count = little16(tail + end + 10);
    if (count == 65535 || little16(tail + end + 8) != count ||
        little32(tail + end + 16) + little32(tail + end + 12) != (unsigned long)(start + end))
        goto done;
    if (fseek(file, (long)little32(tail + end + 16), SEEK_SET))
        goto done;
    for (i = 0; i < count; ++i) {
        char name[512];
        unsigned size, extra, comment;
        if (fread(header, 1, 46, file) != 46 || memcmp(header, "PK\001\002", 4))
            goto done;
        size = little16(header + 28);
        extra = little16(header + 30);
        comment = little16(header + 32);
        if (!size || size >= sizeof(name) || fread(name, 1, size, file) != size)
            goto done;
        name[size] = 0;
        if (memchr(name, 0, size))
            goto done;
        for (j = 0; j < sizeof(conflicts) / sizeof(*conflicts); ++j) {
            if (!strcmp(name, conflicts[j])) {
                fprintf(stderr, "Conflicting HMI class: %s in %s\n", name, path);
                goto done;
            }
        }
        if (fseek(file, (long)(extra + comment), SEEK_CUR))
            goto done;
    }
    result = ftell(file) == start + end;
done:
    free(tail);
    fclose(file);
    return result;
}
