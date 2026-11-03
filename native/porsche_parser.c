#include "porsche_parser.h"
#include "porsche_sha256.h"
#include <stdint.h>
#include <string.h>
#include <dlfcn.h>

/* MU1417 video_parser_create reads bytes 0..23. NvSS installs seven callbacks,
 * with DisplayPicture in slot 2. Verified at NvSS 0x5960..0x5a04 and nvparser
 * 0x16118..0x161a8. These are firmware-specific, not a generic NvMedia ABI. */
typedef struct {
    void *callbacks[7];
} callbacks;
typedef struct {
    callbacks *functions;
    void *user;
    int32_t clock_rate, buffering;
    uint32_t codec;
    void *extended_sequence;
} parameters;
#if UINTPTR_MAX == UINT32_MAX
typedef char parameter_size[sizeof(parameters) == 24 ? 1 : -1];
#endif
static void *library, *owned_parser;
static void *(*real_create)(const parameters *);
static void (*real_destroy)(void *);
static void (*publish)(void *);
static callbacks custom_callbacks;

static int verified(const char *path, const char *expected) {
    char digest[65];
    return cw_sha256_file(path, digest) && !strcmp(digest, expected);
}

int cw_parser_start(void (*surface)(void *)) {
    if (library || !surface ||
        !verified("/mnt/app/root/lib-target/libnvparser.so",
                  "56b7f7195984ad76223f94c24b954c2bcc79a8f6125d30aa9265470d83bd2e94") ||
        !verified("/mnt/app/armle/lib/libnvss_video.so",
                  "b57f3eb1697c6846d06a1c546ad8b06834c630ccfac88c6ea6787dd5ccc41475"))
        return 0;
    library = dlopen("/mnt/app/root/lib-target/libnvparser.so", RTLD_NOW | RTLD_LOCAL);
    if (!library)
        return 0;
    real_create = (void *(*)(const parameters *))dlsym(library, "video_parser_create");
    real_destroy = (void (*)(void *))dlsym(library, "video_parser_destroy");
    if (!real_create || !real_destroy) {
        cw_parser_stop();
        return 0;
    }
    publish = surface;
    return 1;
}

void cw_parser_stop(void) {
    /* Caller must close NvSS first, which destroys the parser and its threads.
     * Retain handles on misuse rather than unload code still in use. */
    if (owned_parser)
        return;
    publish = NULL;
    real_create = NULL;
    real_destroy = NULL;
    if (library)
        dlclose(library);
    library = NULL;
    memset(&custom_callbacks, 0, sizeof(custom_callbacks));
}

static int display_picture(void *user, void *picture, uint64_t pts) {
    void *data = NULL, *surface = NULL;
    (void)user;
    (void)pts;
    if (!publish || !picture)
        return 0;
    /* NvSS BufferGetData at 0x9dc4 reads picture+12. DisplayPicture 0x4e14
     * and DecodePicture 0x506c use that data; the surface is at data+8.
     * memcpy avoids alignment assumptions for the firmware's opaque objects. */
    memcpy(&data, (const uint8_t *)picture + 12, sizeof(data));
    if (!data)
        return 0;
    memcpy(&surface, (const uint8_t *)data + 8, sizeof(surface));
    if (!surface)
        return 0;
    publish(surface);
    /* No AddRef and no enqueue: the vendor parser retains ownership throughout
     * this callback and its normal Release callback returns the buffer. */
    return 1;
}

void *video_parser_create(const parameters *original) {
    parameters custom;
    unsigned i;
    if (!real_create || !publish || owned_parser || !original ||
        !original->functions || original->codec != 4)
        return NULL;
    for (i = 0; i < 7; ++i)
        if (!original->functions->callbacks[i])
            return NULL;
    custom = *original;
    custom_callbacks = *original->functions;
    custom_callbacks.callbacks[2] = (void *)display_picture;
    custom.functions = &custom_callbacks;
    owned_parser = real_create(&custom);
    return owned_parser;
}

void video_parser_destroy(void *parser) {
    if (real_destroy && parser == owned_parser && parser) {
        real_destroy(parser);
        owned_parser = NULL;
    }
}
