/* One-shot diagnostic transfer into a fixed RAM directory, never an installer. */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include "porsche_network.h"

static int read_all(int fd, void *data, size_t size) {
    size_t at = 0;
    ssize_t n;
    while (at < size) {
        n = read(fd, (char *)data + at, size - at);
        if (n <= 0)
            return 0;
        at += (size_t)n;
    }
    return 1;
}
int main(int argc, char **argv) {
    int listener = -1, client = -1, out = -1, ok = 0, one = 1;
    unsigned i;
    uint32_t size;
    char token[64], buffer[4096], path[256], temporary[256];
    struct sockaddr_in address;
    if (argc != 3 || strlen(argv[1]) > 60 || strncmp(argv[1], "cw-", 3) || strlen(argv[2]) != 64)
        return 2;
    for (i = 0; argv[1][i]; ++i)
        if (!isalnum((unsigned char)argv[1][i]) && argv[1][i] != '-' && argv[1][i] != '.')
            return 2;
    if (strstr(argv[1], ".."))
        return 2;
    snprintf(path, sizeof(path), "/ramdisk/cw-link-probe-20261102/%s", argv[1]);
    snprintf(temporary, sizeof(temporary), "/ramdisk/cw-link-probe-20261102/.receive-%ld",
             (long)getpid());
    alarm(20);
    listener = socket(AF_INET, SOCK_STREAM, 0);
    if (listener < 0)
        goto done;
    if (setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)))
        goto done;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(CW_DIAGNOSTIC_UPLOAD_PORT);
    address.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) || listen(listener, 1))
        goto done;
    puts("RAM_RECEIVER_READY");
    fflush(stdout);
    client = accept(listener, NULL, NULL);
    if (client < 0)
        goto done;
    if (!read_all(client, token, 64) || memcmp(token, argv[2], 64) || !read_all(client, &size, 4))
        goto done;
    size = ntohl(size);
    if (!size || size > 1024 * 1024)
        goto done;
    out = open(temporary, O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (out < 0)
        goto done;
    while (size) {
        size_t n = size > sizeof(buffer) ? sizeof(buffer) : size;
        size_t at = 0;
        if (!read_all(client, buffer, n))
            goto done;
        while (at < n) {
            ssize_t used = write(out, buffer + at, n - at);
            if (used <= 0)
                goto done;
            at += (size_t)used;
        }
        size -= (uint32_t)n;
    }
    if (close(out)) {
        out = -1;
        goto done;
    }
    out = -1;
    if (rename(temporary, path))
        goto done;
    ok = 1;
    puts("RAM_RECEIVER_COMPLETE");
done:
    if (out >= 0)
        close(out);
    if (client >= 0)
        close(client);
    if (listener >= 0)
        close(listener);
    if (!ok)
        unlink(temporary);
    return ok ? 0 : 1;
}
