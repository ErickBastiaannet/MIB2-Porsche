#define _POSIX_C_SOURCE 200809L
#include "porsche_dm.h"
#include "porsche_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/select.h>
#include <time.h>
#include <errno.h>
#include <spawn.h>

#ifndef CW_DMDT
#define CW_DMDT "/eso/bin/apps/dmdt"
#endif

extern char **environ;

static int spawn_query(const char *root, char *const argv[], int read_fd, int write_fd,
                       pid_t *child) {
    posix_spawn_file_actions_t actions;
    char preload[600];
    char **environment;
    size_t n = 0, used = 0, i;
    int status;
    if (!root || snprintf(preload, sizeof(preload), "LD_PRELOAD=%s/libcw-query-stdio.so", root) >=
                     (int)sizeof(preload))
        return 0;
    while (environ[n]) {
        if (++n > 4096)
            return 0;
    }
    environment = calloc(n + 4, sizeof(*environment));
    if (!environment)
        return 0;
    for (i = 0; i < n; ++i) {
        if (strncmp(environ[i], "LD_PRELOAD=", 11) && strncmp(environ[i], "LD_LIBRARY_PATH=", 16) &&
            strncmp(environ[i], "IPL_CONFIG_DIR=", 15))
            environment[used++] = environ[i];
    }
    environment[used++] = preload;
    environment[used++] = "LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/"
                          "lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib";
    environment[used++] = "IPL_CONFIG_DIR=/etc/eso/production";
    status = posix_spawn_file_actions_init(&actions);
    if (status) {
        free(environment);
        return 0;
    }
    status = posix_spawn_file_actions_addclose(&actions, read_fd);
    if (!status)
        status = posix_spawn_file_actions_adddup2(&actions, write_fd, 1);
    if (!status)
        status = posix_spawn_file_actions_adddup2(&actions, write_fd, 2);
    if (!status)
        status = posix_spawn_file_actions_addclose(&actions, write_fd);
    /* Do not fork a graphics process and run libc allocation/setenv in the
     * child: vendor EGL/decoder libraries can already have worker threads. */
    if (!status)
        status = posix_spawn(child, CW_DMDT, &actions, NULL, argv, environment);
    posix_spawn_file_actions_destroy(&actions);
    free(environment);
    return status == 0;
}

#ifndef CW_DISPLAY_CONFIG
#define CW_DISPLAY_CONFIG "/etc/eso/production/displaymanager.json"
#endif
#ifndef CW_DISPLAY_CONFIG_SHA
#define CW_DISPLAY_CONFIG_SHA "115df2ffd860a6adccd4dd10c643a13b575a439922b272942025df8c7c246202"
#endif

int cw_dm_backend_id(unsigned report_index, unsigned *backend_id) {
    char digest[65];
    /* Never infer an ID from the loop counter printed by getSystemInformation.
     * This exact unit-verified profile declares extended.2_lvds display ID 4.
     * Changed/unknown configurations need their own verified profile. */
    if (!backend_id || report_index != 1 || !cw_sha256_file(CW_DISPLAY_CONFIG, digest) ||
        strcmp(digest, CW_DISPLAY_CONFIG_SHA))
        return 0;
    *backend_id = 4;
    return 1;
}
static int copy_line(const char *source, char *target, size_t capacity) {
    const char *end = strchr(source, '\n');
    size_t size = end ? (size_t)(end - source) : strlen(source);
    if (size >= capacity)
        return 0;
    memcpy(target, source, size);
    target[size] = 0;
    return 1;
}
uint64_t cw_monotonic_ms(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now))
        return 0;
    return (uint64_t)now.tv_sec * 1000 + (uint64_t)now.tv_nsec / 1000000;
}
static int execute(const char *root, char *const argv[], char *text, size_t capacity) {
    int fd[2], status = 0, done = 0, eof = 0;
    pid_t child;
    size_t used = 0;
    uint64_t deadline;
    if (!text || capacity < 2 || pipe(fd))
        return 0;
    if (!spawn_query(root, argv, fd[0], fd[1], &child)) {
        close(fd[0]);
        close(fd[1]);
        return 0;
    }
    close(fd[1]);
    if (fcntl(fd[0], F_SETFL, O_NONBLOCK) < 0 || !cw_monotonic_ms()) {
        close(fd[0]);
        kill(child, SIGKILL);
        waitpid(child, &status, 0);
        return 0;
    }
    deadline = cw_monotonic_ms() + 4000;
    while (cw_monotonic_ms() < deadline && (!done || !eof)) {
        ssize_t count = read(fd[0], text + used, capacity - 1 - used);
        if (count > 0)
            used += (size_t)count;
        else if (count == 0)
            eof = 1;
        else if (errno != EAGAIN && errno != EINTR)
            break;
        if (!done)
            done = waitpid(child, &status, WNOHANG) == child;
        if (used == capacity - 1)
            break;
        if (!done || !eof) {
            struct timespec pause = {0, 10000000};
            nanosleep(&pause, NULL);
        }
    }
    close(fd[0]);
    text[used] = 0;
    if (!done) {
        kill(child, SIGKILL);
        waitpid(child, &status, 0);
        return 0;
    }
    return eof && WIFEXITED(status) && WEXITSTATUS(status) == 0;
}
int cw_dm_query(const char *root, const char *command, char *text, size_t capacity) {
    char *args[] = {"dmdt", (char *)command, NULL};
    if (strcmp(command, "gd") && strcmp(command, "gc") && strcmp(command, "gs"))
        return 0;
    return execute(root, args, text, capacity);
}
int cw_dm_display(const char *text, cw_display *out) {
    const char *line = text;
    unsigned selected = 0, matches = 0, w = 0, h = 0, got_size = 0, got_context = 0, id = 0;
    unsigned chosen_id = 0;
    int context = -1;
    if (!text || !strstr(text, "displaymanager reports the following system information:"))
        return 0;
    while (line && *line) {
        char terminal[64], bounded[512];
        if (!copy_line(line, bounded, sizeof(bounded)))
            return 0;
        if (sscanf(bounded, "display %u:", &id) == 1) {
            selected = 0;
        } else if (sscanf(bounded, " terminal: %63s", terminal) == 1) {
            selected = strcmp(terminal, "2nd_lvds") == 0;
            if (selected) {
                ++matches;
                chosen_id = id;
            }
        } else if (selected) {
            unsigned a, b;
            int c;
            if (sscanf(bounded, " size: %u x %u", &a, &b) == 2) {
                w = a;
                h = b;
                ++got_size;
            } else if (sscanf(bounded, " context id: %d", &c) == 1) {
                context = c;
                ++got_context;
            }
        }
        line = strchr(line, '\n');
        if (line)
            ++line;
    }
    if (matches != 1 || got_size != 1 || got_context != 1 || w < 64 || h < 64 || w > 8192 ||
        h > 8192 || chosen_id == 0 || context < 0 || context > 157)
        return 0;
    out->width = w;
    out->height = h;
    out->id = chosen_id;
    out->context = context;
    return 1;
}
int cw_dm_layer(const char *text, unsigned id, unsigned width, unsigned height, int present) {
    const char *line = text;
    unsigned matches = 0, valid = 0;
    if (!text || !strstr(text, "displaymanager knows") || !strstr(text, "displayables:"))
        return 0;
    while (line && *line) {
        unsigned i, w, h;
        char kind[16], bounded[512];
        if (!copy_line(line, bounded, sizeof(bounded)))
            return 0;
        if (sscanf(bounded, " %u %15s %u x %u", &i, kind, &w, &h) == 4 && i == id) {
            ++matches;
            /* Direct NvSS streams decode but do not provide a composited map
             * window on this Porsche. Require a real window of the right size. */
            if (!strcmp(kind, "window") && w == width && h == height)
                ++valid;
        }
        line = strchr(line, '\n');
        if (line)
            ++line;
    }
    return present ? (matches == 1 && valid == 1) : matches == 0;
}
int cw_dm_switch(const char *root, unsigned display_id, unsigned context) {
    char id[16], target[16], text[16384];
    cw_display actual;
    unsigned backend_id;
    char *args[] = {"dmdt", "sc", target, id, NULL};
    if (context > 157 || display_id == 0 || !cw_dm_query(root, "gs", text, sizeof(text)) ||
        !cw_dm_display(text, &actual) || actual.id != display_id ||
        !cw_dm_backend_id(display_id, &backend_id))
        return 0;
    snprintf(target, sizeof(target), "%u", backend_id);
    snprintf(id, sizeof(id), "%u", context);
    return execute(root, args, text, sizeof(text));
}
int cw_map_context(unsigned context) {
    unsigned n = context % 79;
    return context <= 157 && (n == 72 || n == 74 || n == 76 || n == 77);
}

int cw_dm_context_layers(const char *text, unsigned context, const unsigned *layers, size_t layer_count) {
    const char *line = text;
    unsigned expected = 0, rows = 0, found = 0, count = 0, items = 0, match = 0;
    unsigned selected = 0, seen[8192] = {0};
    size_t i,j;
    if(!layers||!layer_count||layer_count>16)return -1;
    for(i=0;i<layer_count;++i){
        if(layers[i]>4095)return -1;
        for(j=0;j<i;++j)if(layers[j]==layers[i])return -1;
    }
    if (!text || sscanf(text, "displaymanager knows %u contexts:", &expected) != 1 ||
        expected > 4096)
        return -1;
    while (line && *line) {
        int id;
        unsigned n;
        char bounded[512];
        if (!copy_line(line, bounded, sizeof(bounded)))
            return -1;
        if (sscanf(bounded, " %d | %u |", &id, &n) == 2) {
            if (id < -4096 || id >= 4096 || seen[id + 4096]++ || n > 64)
                return -1;
            ++rows;
            selected = id >= 0 && (unsigned)id == context;
            if (selected) {
                ++found;
                count = n;
            }
        } else if (selected && sscanf(bounded, " %d", &id) == 1) {
            if (items < layer_count && id >= 0 && (unsigned)id == layers[items])
                ++match;
            ++items;
        }
        line = strchr(line, '\n');
        if (line)
            ++line;
    }
    if (rows != expected || found > 1 || (found && items != count))
        return -1;
    if (!found || !count)
        return 0;
    return count == layer_count && match == layer_count ? 1 : 2;
}

int cw_dm_context_state(const char *text,unsigned context,unsigned layer) {
    return cw_dm_context_layers(text,context,&layer,1);
}

int cw_dm_declare(const char *root, unsigned context, unsigned layer) {
    char id[16], window[16], text[65536];
    char *args[] = {"dmdt", "dc", id, window, NULL};
    if (context != 70 || layer != 78 || !cw_dm_query(root, "gc", text, sizeof(text)) ||
        cw_dm_context_state(text, context, layer) != 0)
        return 0;
    snprintf(id, sizeof(id), "%u", context);
    snprintf(window, sizeof(window), "%u", layer);
    if (!execute(root, args, text, sizeof(text)))
        return 0;
    return cw_dm_query(root, "gc", text, sizeof(text)) &&
           cw_dm_context_state(text, context, layer) == 1;
}

int cw_dm_declare_overlay(const char *root) {
    static const unsigned layers[] = {78, 33};
    char text[65536];
    char *args[] = {"dmdt", "dc", "70", "78", "33", NULL};
    if (!execute(root, args, text, sizeof(text)))
        return 0;
    return cw_dm_query(root, "gc", text, sizeof(text)) &&
           cw_dm_context_layers(text, 70, layers, 2) == 1;
}
