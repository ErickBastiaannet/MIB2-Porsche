#include "porsche_wire.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

uint32_t cw_crc32(const char *data, size_t length) {
    uint32_t crc = 0xffffffffU;
    size_t i;
    unsigned bit;
    for (i = 0; i < length; ++i) {
        crc ^= (unsigned char)data[i];
        for (bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320U : 0);
    }
    return crc ^ 0xffffffffU;
}
int cw_wire_read(const char *path, const char *magic, uint32_t *v, unsigned count) {
    char data[256];
    size_t n, at, prefix = strlen(magic);
    unsigned i, j;
    uint32_t sum = 0;
    FILE *file = fopen(path, "rb");
    if (!file)
        return 0;
    n = fread(data, 1, sizeof(data), file);
    i = (unsigned)ferror(file);
    fclose(file);
    if (i || n >= sizeof(data) || n < prefix + 11 || memcmp(data, magic, prefix) ||
        data[prefix] != ' ' || count > 12)
        return 0;
    at = prefix + 1;
    for (i = 0; i < count; ++i) {
        size_t start = at;
        v[i] = 0;
        while (at < n && data[at] >= '0' && data[at] <= '9') {
            unsigned d = (unsigned)(data[at++] - '0');
            if (v[i] > (UINT32_MAX - d) / 10)
                return 0;
            v[i] = v[i] * 10 + d;
        }
        if (start == at || at >= n || data[at++] != ' ')
            return 0;
    }
    if (n != at + 9 || data[n - 1] != '\n')
        return 0;
    for (j = 0; j < 8; ++j) {
        unsigned char c = (unsigned char)data[at + j];
        unsigned d;
        if (c >= '0' && c <= '9')
            d = c - '0';
        else if (c >= 'a' && c <= 'f')
            d = c - 'a' + 10;
        else
            return 0;
        sum = (sum << 4) | d;
    }
    return cw_crc32(data, at) == sum;
}
int cw_wire_write(const char *path, const char *magic, const uint32_t *values, unsigned count) {
    char body[256], temporary[512];
    size_t used;
    unsigned i;
    int n;
    FILE *file;
    if (count > 12)
        return 0;
    n = snprintf(body, sizeof(body), "%s ", magic);
    if (n < 0 || (size_t)n >= sizeof(body))
        return 0;
    used = (size_t)n;
    for (i = 0; i < count; ++i) {
        n = snprintf(body + used, sizeof(body) - used, "%u ", values[i]);
        if (n < 0 || (size_t)n >= sizeof(body) - used)
            return 0;
        used += (size_t)n;
    }
    n = snprintf(body + used, sizeof(body) - used, "%08x\n", cw_crc32(body, used));
    if (n != 9 || used + 9 >= sizeof(body))
        return 0;
    used += 9;
    n = snprintf(temporary, sizeof(temporary), "%s.tmp.%ld", path, (long)getpid());
    if (n < 0 || (size_t)n >= sizeof(temporary))
        return 0;
    file = fopen(temporary, "wb");
    if (!file)
        return 0;
    (void)fchmod(fileno(file), 0600);
    i = fwrite(body, 1, used, file) == used;
    if (fclose(file))
        i = 0;
    if (!i || rename(temporary, path)) {
        unlink(temporary);
        return 0;
    }
    return 1;
}
