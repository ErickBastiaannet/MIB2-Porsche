#include "porsche_session.h"
#include <string.h>

void cw_session_init(cw_session *s) { memset(s, 0, sizeof(*s)); }

unsigned cw_session_stop(cw_session *s) {
    unsigned actions = s->phase == CW_OEM ? CW_NONE : CW_STOP_VIDEO;
    if (s->phase == CW_CARPLAY)
        actions |= CW_RESTORE_OEM;
    s->phase = CW_OEM;
    s->phone_session = 0;
    return actions;
}

static int fresh(const cw_geometry *g, uint32_t now) {
    return g && g->timestamp <= now && now - g->timestamp <= 5;
}

unsigned cw_session_update(cw_session *s, const cw_geometry *g, uint32_t now, uint32_t phone,
                           int verified) {
    unsigned actions = CW_NONE;
    if (!fresh(g, now) || !g->active || !g->carplay_active || !phone || !verified)
        return cw_session_stop(s);
    if (s->phase != CW_OEM &&
        (s->phone_session != phone || cw_geometry_session(&s->negotiated, g) != 1))
        actions |= cw_session_stop(s);
    if (s->phase != CW_OEM) {
        /* While waiting for the first useful pixel, worker liveness and the
         * fresh source/geometry leases are authoritative.  MU1417 can keep
         * delivering valid compressed frames while its NvSS output surface
         * is not available yet.  A time-only stop here repeatedly destroyed
         * a healthy decoder during cold boot.  Once pixels have appeared,
         * retain the strict five-second fail-safe. */
        if (s->phase == CW_CARPLAY &&
            (now < s->last_frame_at || now - s->last_frame_at > 5U)) {
            return actions | cw_session_stop(s);
        }
        return actions;
    }
    s->negotiated = *g;
    if (++s->epoch == 0)
        ++s->epoch;
    s->phone_session = phone;
    s->phase = CW_WAIT_VIDEO;
    s->started_at = now;
    s->last_frame_at = now;
    return actions | CW_NEGOTIATE;
}

unsigned cw_session_frame(cw_session *s, uint32_t epoch, uint32_t now, uint32_t width,
                          uint32_t height, int idr, int output_ready) {
    if (s->phase == CW_OEM || epoch != s->epoch)
        return CW_NONE;
    if (!output_ready || width != s->negotiated.width || height != s->negotiated.height)
        return cw_session_stop(s);
    if (now < s->last_frame_at || now - s->last_frame_at > 5)
        return cw_session_stop(s);
    if (s->phase == CW_WAIT_VIDEO && !idr)
        return CW_NONE;
    s->last_frame_at = now;
    if (s->phase == CW_WAIT_VIDEO) {
        s->phase = CW_CARPLAY;
        return CW_SHOW_CARPLAY;
    }
    return CW_NONE;
}
