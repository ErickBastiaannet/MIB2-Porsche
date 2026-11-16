package de.audi.tghu.navi.app.cluster;

import org.connectwow.carplay.PorscheCluster;
import de.audi.atip.interapp.combi.bap.navi.CombiBAPServiceNavi;

/** Optional, isolated BAP presentation probe. Never changes OEM map setup/state. */
public final class PorscheSatelliteLogo {
    private static final Object LOCK = new Object();
    private static CombiBAPServiceNavi target;
    private static int requested, supplementary, delivered;
    private static boolean known, started, rendererActive;
    private static int diagnosticLines;
    private PorscheSatelliteLogo() { }

    private static boolean enabled() {
        try { return "hide-during-carplay".equals(System.getProperty("connectwow.carplay.satelliteLogo")); }
        catch (Throwable unavailable) { return false; }
    }

    /** Replaces only the existing outgoing BAP updateMapView call. */
    public static void send(CombiBAPServiceNavi service, int view, int extra) {
        synchronized (LOCK) {
            target = service;
            requested = view;
            supplementary = extra;
            known = false;
            int effective = effective(view, enabled() && rendererActive);
            service.updateMapView(effective, extra);
            delivered = effective;
            known = true;
            if (enabled() && !started) {
                Thread worker = new Thread(new Runnable() {
                    public void run() {
                        for (;;) {
                            try { Thread.sleep(500); } catch (InterruptedException ignored) { }
                            try { refresh(PorscheCluster.carPlayReady()); } catch (Throwable unavailable) { }
                        }
                    }
                }, "cw-satellite-logo");
                try { worker.setDaemon(true); worker.start(); started = true; }
                catch (Throwable unavailable) { /* OEM output already succeeded; retry on next OEM call. */ }
            }
        }
    }

    /** MapView 1 is the exact OEM satellite-logo notification; other views pass through. */
    static int effective(int view, boolean active) { return active && view == 1 ? 0 : view; }

    /** Restores the latest OEM request when the valid renderer lease expires. */
    static void refresh(boolean active) {
        synchronized (LOCK) {
            rendererActive = active;
            if (target == null) return;
            int next = effective(requested, enabled() && active);
            if (!known || next != delivered) {
                target.updateMapView(next, supplementary);
                delivered = next;
                known = true;
                logTransition(next, supplementary, rendererActive);
            }
        }
    }

    private static void logTransition(int view, int extra, boolean active) {
        if (diagnosticLines++ >= 64) return;
        try {
            StringBuffer body = new StringBuffer("SATELLITE_LOGO view=");
            body.append(view).append(" extra=").append(extra).append(" carplay=").append(active).append('\n');
            java.io.FileOutputStream out = new java.io.FileOutputStream("/ramdisk/cw-satellite-logo.log", true);
            try { out.write(body.toString().getBytes("US-ASCII")); } finally { out.close(); }
        } catch (Throwable unavailable) { }
    }
}
