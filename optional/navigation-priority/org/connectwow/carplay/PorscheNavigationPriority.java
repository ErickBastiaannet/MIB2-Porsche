package org.connectwow.carplay;

/** Pure ownership policy; no OEM calls, files, threads or display changes.
 * Integration must serialize transition effects before acknowledge().
 */
public final class PorscheNavigationPriority {
    public static final int OEM_UNKNOWN = -1;
    public static final int OEM_IDLE = 0;
    public static final int OEM_ROUTE = 1;
    public static final int OEM_ARRIVAL = 2;
    public static final int NONE = 0, PORSCHE = 1, CARPLAY = 2;
    // A fresh helper does not prove the physical screen is already OEM.
    // Its first decision must be reconciled and acknowledged by the adapter.
    private int appliedMap = NONE, appliedGuidance = NONE;
    private long generation, requestedPhoneSession, appliedPhoneSession;
    private Decision current = new Decision(0L, PORSCHE, PORSCHE, true, false, false, false);

    /** OEM_UNKNOWN is deliberately Porsche-owned, never permission for CarPlay.
     * OEM_ARRIVAL lasts until the original arrival presentation has finished;
     * this module does not invent a timeout or stop the iPhone route.
     */
    public synchronized Decision request(int oemState, boolean validVideo, boolean freshGuidance, long phoneSession) {
        // Invalid adapter input must withdraw CarPlay permission, not leave
        // the last successful CarPlay decision in effect after an exception.
        if (oemState < OEM_UNKNOWN || oemState > OEM_ARRIVAL || phoneSession < 0L) {
            oemState = OEM_UNKNOWN; validVideo = false; freshGuidance = false; phoneSession = 0L;
        }
        int map = oemState == OEM_IDLE && validVideo && phoneSession > 0L ? CARPLAY : PORSCHE;
        int guidance = map == PORSCHE ? PORSCHE : freshGuidance ? CARPLAY : NONE;
        long nextPhoneSession = map == CARPLAY ? phoneSession : 0L;
        // Phone freshness updates while Porsche owns the cluster must not
        // invalidate an otherwise identical pending transition repeatedly.
        if (current.mapSource == map && current.guidanceSource == guidance &&
                requestedPhoneSession == nextPhoneSession) return current;
        requestedPhoneSession = nextPhoneSession;
        boolean sessionChanged = map == CARPLAY && phoneSession != appliedPhoneSession;
        boolean pending = map != appliedMap || guidance != appliedGuidance || sessionChanged;
        current = new Decision(++generation, map, guidance, pending,
            pending && appliedGuidance == CARPLAY && (guidance != CARPLAY || sessionChanged),
            pending && appliedMap != CARPLAY && map == CARPLAY,
            pending && guidance == CARPLAY && (appliedGuidance != CARPLAY || sessionChanged));
        return current;
    }

    /** Reject completion of a transition superseded by a newer route/session event.
     * This does not cancel already-issued OEM calls: adapters must use one writer.
     */
    public synchronized boolean acknowledge(Decision decision) {
        if (!isCurrentTransition(decision))
            return false;
        appliedMap = current.mapSource; appliedGuidance = current.guidanceSource;
        appliedPhoneSession = appliedMap == CARPLAY ? requestedPhoneSession : 0L;
        current = new Decision(current.generation, appliedMap, appliedGuidance,
            false, false, false, false);
        return true;
    }

    /** Adapter must check and execute under synchronized(policy), including
     * clear/publish/ack, to prevent a request changing halfway through writes.
     * Identity also rejects tokens from a different policy instance.
     */
    public synchronized boolean isCurrentTransition(Decision decision) {
        return decision != null && decision == current && current.pending;
    }

    public synchronized boolean mayForwardCarPlayGuidance() {
        return !current.pending && current.mapSource == CARPLAY && current.guidanceSource == CARPLAY;
    }
    public synchronized boolean mayUseCarPlayZoom() {
        // Guidance-only transitions must not blank an already-owned map.
        return current.mapSource == CARPLAY && appliedMap == CARPLAY &&
            requestedPhoneSession > 0L && requestedPhoneSession == appliedPhoneSession;
    }
    public synchronized boolean mayShowCarPlay() { return mayUseCarPlayZoom(); }
    public synchronized boolean shouldSuppressSatelliteLogo() { return mayShowCarPlay(); }

    public static final class Decision {
        public final long generation;
        public final int mapSource, guidanceSource;
        public final boolean pending, clearCarPlayGuidance, releaseOemPresentation, replayCarPlayGuidance;
        private Decision(long epoch, int map, int guidance, boolean waiting,
                         boolean clear, boolean release, boolean replay) {
            generation = epoch; mapSource = map; guidanceSource = guidance;
            pending = waiting; clearCarPlayGuidance = clear;
            releaseOemPresentation = release; replayCarPlayGuidance = replay;
        }
    }
}
