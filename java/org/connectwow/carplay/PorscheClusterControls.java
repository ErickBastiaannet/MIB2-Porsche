package org.connectwow.carplay;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

/** Forwards Porsche cluster map-scale steps to the active CarPlay map. */
public final class PorscheClusterControls {
    private static final int PORT = 7032;
    private static final int MAX_PENDING = 8;
    private static final long INTERVAL_MS = 50L;
    private static final long TAIL_MS = 250L;
    private static final Object LOCK = new Object();
    private static int pendingDirection, pendingCount;
    private static long lastInputMs, nextSendMs, revision, activeEpoch;
    private static boolean started;

    private PorscheClusterControls() { }

    /** Consumes MapScale only while CarPlay owns the cluster; OEM otherwise stays stock. */
    public static boolean consumeMapScale(int steps) {
        // Zoom must also work in the isolated zoom profile, where the display
        // routing hook is deliberately absent. The native renderer's short
        // lived, checksummed lease is the authoritative ownership signal.
        if (!PorscheCluster.carPlayReady()) return false;
        if (steps == 0) return true;
        synchronized (LOCK) {
            startLocked();
            int direction = steps > 0 ? 1 : -1;
            int repeats = Math.abs(steps);
            if (repeats > MAX_PENDING) repeats = MAX_PENDING;
            long now = System.currentTimeMillis();
            if (pendingDirection != 0 && pendingDirection != direction) {
                // A reversal supersedes unsent intent and is immediately eligible.
                pendingCount = 0;
                nextSendMs = now;
                ++revision;
            }
            pendingDirection = direction;
            pendingCount += repeats;
            if (pendingCount > MAX_PENDING) pendingCount = MAX_PENDING;
            lastInputMs = now;
            LOCK.notifyAll();
        }
        return true;
    }

    private static void startLocked() {
        if (started) return;
        Thread worker = new Thread(new Runnable() {
            public void run() { runCommands(); }
        }, "cw-porsche-cluster-controls");
        worker.setDaemon(true);
        started = true;
        worker.start();
    }

    private static void clearLocked() {
        pendingDirection = 0;
        pendingCount = 0;
        lastInputMs = 0;
        ++revision;
    }

    private static void runCommands() {
        DatagramSocket socket = null;
        InetAddress loopback = null;
        for (;;) {
            int direction;
            long selectedRevision, selectedInput;
            synchronized (LOCK) {
                while (pendingCount == 0) {
                    try { LOCK.wait(); } catch (InterruptedException ignored) { }
                }
                long now = System.currentTimeMillis();
                if (now - lastInputMs > TAIL_MS) {
                    clearLocked();
                    continue;
                }
                long delay = nextSendMs - now;
                if (delay > 0) {
                    try { LOCK.wait(delay); } catch (InterruptedException ignored) { }
                    continue;
                }
                direction = pendingDirection;
                selectedRevision = revision;
                selectedInput = lastInputMs;
            }
            try {
                // Never replay input across an OEM fallback or a renderer generation change.
                long epoch = PorscheCluster.carPlayEpoch();
                synchronized (LOCK) {
                    if (epoch <= 0) {
                        activeEpoch = 0;
                        clearLocked();
                        continue;
                    }
                    if (activeEpoch == 0) activeEpoch = epoch;
                    else if (activeEpoch != epoch) {
                        activeEpoch = epoch;
                        clearLocked();
                        continue;
                    }
                    long now = System.currentTimeMillis();
                    if (selectedRevision != revision || direction != pendingDirection
                            || selectedInput != lastInputMs || now - selectedInput > TAIL_MS) continue;
                    --pendingCount;
                    if (pendingCount == 0) pendingDirection = 0;
                }
                String command = direction > 0 ? "zoom-out" : "zoom-in";
                byte[] bytes = command.getBytes("US-ASCII");
                if (socket == null) socket = new DatagramSocket();
                if (loopback == null) loopback = InetAddress.getByName("127.0.0.1");
                socket.send(new DatagramPacket(bytes, bytes.length, loopback, PORT));
            } catch (Throwable ignored) {
                if (socket != null) socket.close();
                socket = null;
                loopback = null;
            } finally {
                synchronized (LOCK) { nextSendMs = System.currentTimeMillis() + INTERVAL_MS; }
            }
        }
    }
}
