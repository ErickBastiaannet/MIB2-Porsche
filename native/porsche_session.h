#ifndef CONNECTWOW_PORSCHE_SESSION_H
#define CONNECTWOW_PORSCHE_SESSION_H
#include "porsche_geometry.h"

/* Actions describe requests to an adapter; this library never opens a display
 * or MOST device. Negotiation is allowed only after transport verification. */
enum cw_action {
    CW_NONE = 0,
    CW_NEGOTIATE = 1,
    CW_STOP_VIDEO = 2,
    CW_RESTORE_OEM = 4,
    CW_SHOW_CARPLAY = 8
};
enum cw_phase { CW_OEM = 0, CW_WAIT_VIDEO = 1, CW_CARPLAY = 2 };
typedef struct {
    cw_geometry negotiated;
    uint32_t epoch, phone_session, phase, started_at, last_frame_at;
} cw_session;

void cw_session_init(cw_session *session);
/* now is epoch seconds, like the observation. A new phone_session identifies
 * every new native AirPlay session. Zero means disconnected. */
unsigned cw_session_update(cw_session *session, const cw_geometry *current, uint32_t now,
                           uint32_t phone_session, int transport_verified);
/* Call only for a successfully decoded/written frame of this stream epoch.
 * A new stream must first supply an IDR. Failed or old stream acknowledgements
 * never take display ownership. */
unsigned cw_session_frame(cw_session *session, uint32_t epoch, uint32_t now, uint32_t width,
                          uint32_t height, int idr, int output_ready);
unsigned cw_session_stop(cw_session *session);
#endif
