/* SPDX-License-Identifier: GPL-3.0-or-later
 * Included in the pinned upstream handshake source by prepare_native.py.
 * Shared display descriptor for the probe and verified-layout receiver build.
 */
#if !defined(CW_PORSCHE_CAPTURE) &&                                                                \
    (defined(ALTSCREEN_PASSIVE_CAPTURE) || defined(ALTSCREEN_AES_CTR_DECRYPT) ||                   \
     defined(ALTSCREEN_FORWARD_SHM_RING))
#error Porsche video receiver/output is not yet verified; do not reuse VW offsets
#endif
#include "porsche_geometry.h"

#ifdef CW_PORSCHE_CAPTURE
static cw_geometry cw_advertised_geometry;
static pthread_mutex_t cw_geometry_mutex = PTHREAD_MUTEX_INITIALIZER;
static int cw_copy_advertised_geometry(cw_geometry *out) {
    int valid;
    pthread_mutex_lock(&cw_geometry_mutex);
    *out = cw_advertised_geometry;
    valid = out->width != 0 && out->height != 0;
    pthread_mutex_unlock(&cw_geometry_mutex);
    return valid;
}
#endif

#ifdef CW_PORSCHE_CAPTURE
static void cw_add_extended_features(void *result) {
    const void *existing = get_object(result, "extendedFeatures");
    void *extensions = create_array();
    CFArrayGetCountFn count = (CFArrayGetCountFn)resolve("CFArrayGetCount");
    CFArrayGetValueAtIndexFn value = (CFArrayGetValueAtIndexFn)resolve("CFArrayGetValueAtIndex");
    CFArrayAppendValueFn append = (CFArrayAppendValueFn)resolve("CFArrayAppendValue");
    OSStatus error = 0;
    long i, length = 0;
    if (!extensions) return;
    if (existing) {
        if (!count || !value || !append) { release_cf(extensions); return; }
        length = count(existing);
        if (length < 0 || length > 64) { release_cf(extensions); return; }
        for (i = 0; i < length; ++i) append(extensions, value(existing, i));
    }
    error = append_string(extensions, "altScreen");
    if (!error) error = append_string(extensions, "viewAreas");
    if (!error) (void)set_object(result, "extendedFeatures", extensions);
    release_cf(extensions);
}
#endif

static void *create_alt_display(void) {
    const char *path = getenv("CONNECTWOW_PORSCHE_GEOMETRY");
    cw_geometry geometry;
    void *display, *view = NULL, *safe = NULL, *views = NULL, *properties = NULL;
    void *stream = NULL, *streams = NULL, *adjacent = NULL, *limited = NULL;
    CFArrayAppendValueFn append = (CFArrayAppendValueFn)resolve("CFArrayAppendValue");
    OSStatus status;
    if (!path)
        path = "/ramdisk/cw-carplay-geometry.v3";
    if (!cw_geometry_read(path, (uint32_t)time(NULL), &geometry) || !geometry.active)
        return NULL;
    display = create_dictionary();
    status = display && append ? 0 : -1;
    if (!status)
        status = set_cstring(display, "name", "Instrument Cluster");
    if (!status)
        status = set_cstring(display, "uid", ALT_UUID);
    if (!status)
        status = set_cstring(display, "uuid", ALT_UUID);
    if (!status)
        status = set_int(display, "type", 111);
    if (!status)
        status = set_int(display, "maxFPS", 25);
    if (!status)
        status = set_int(display, "widthPixels", geometry.width);
    if (!status)
        status = set_int(display, "heightPixels", geometry.height);
    /* Preserve the measured Porsche panel aspect ratio. CarKit's physical-panel
     * parser requires a non-zero physical size on recent iOS versions. */
    if (!status)
        status = set_int(display, "widthPhysical", 162);
    if (!status)
        status = set_int(display, "heightPhysical", 97);
    if (!status)
        status = set_int(display, "features", 10);
    if (!status)
        status = set_int(display, "primaryInputDevice", 3);
    if (!status)
        status = set_int(display, "initialViewArea", 0);
    if (!status)
        status = set_cstring(display, "initialURL", "maps:/car/instrumentcluster/map");
    if (!status) {
        properties = create_array();
        if (!properties)
            status = -1;
    }
    if (!status)
        status = append_string(properties, "Instrument Cluster");
    if (!status)
        status = set_object(display, "properties", properties);
    if (!status) {
        view = create_area(0, 0, geometry.width, geometry.height);
        safe = create_area(geometry.x, geometry.y, geometry.area_width, geometry.area_height);
        views = create_array();
        if (!view || !safe || !views)
            status = -1;
    }
    if (!status)
        status = set_object(view, "safeArea", safe);
    if (!status)
        append(views, view);
    if (!status)
        status = set_object(display, "viewAreas", views);
    if (!status) {
        adjacent = create_array();
        limited = create_array();
        stream = create_dictionary();
        streams = create_array();
        if (!adjacent || !limited || !stream || !streams)
            status = -1;
    }
    if (!status)
        status = set_int(display, "cornerMasks", 0);
    if (!status)
        status = set_int(display, "nightMode", 0);
    if (!status)
        status = set_int(display, "limitedUI", 0);
    if (!status)
        status = set_object(display, "limitedUIElements", limited);
    if (!status)
        status = set_object(display, "adjacentViewAreas", adjacent);
    if (!status)
        status = set_int(stream, "originXPixels", 0);
    if (!status)
        status = set_int(stream, "originYPixels", 0);
    if (!status)
        status = set_cstring(stream, "uuid", ALT_UUID);
    if (!status)
        status = set_int(stream, "zIndex", 0);
    if (!status)
        append(streams, stream);
    if (!status)
        status = set_object(display, "initialVideoStreams", streams);
    release_cf(limited);
    release_cf(adjacent);
    release_cf(streams);
    release_cf(stream);
    release_cf(properties);
    release_cf(views);
    release_cf(safe);
    release_cf(view);
    if (status) {
        release_cf(display);
        return NULL;
    }
#ifdef CW_PORSCHE_CAPTURE
    pthread_mutex_lock(&cw_geometry_mutex);
    cw_advertised_geometry = geometry;
    pthread_mutex_unlock(&cw_geometry_mutex);
#endif
    return display;
}
