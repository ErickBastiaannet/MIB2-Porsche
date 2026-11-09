package org.connectwow.carplay;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

/** Forwards Porsche cluster map-scale steps to the active CarPlay map. */
public final class PorscheClusterControls {
    private static final int PORT = 7032;
    /* Match the public MHI2 CarPlayClusterControls transport: a bounded FIFO
     * drained by one daemon thread, without an invented debounce or pacing
     * layer. One Porsche MapScale detent produces exactly one command. */
    private static final int QUEUE_SIZE = 16;
    private static final int[] QUEUE = new int[QUEUE_SIZE];
    private static final Object LOCK = new Object();
    private static int queueHead, queueTail, queueCount;
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
            int magnitude = Math.abs(steps);
            if (magnitude > QUEUE_SIZE) magnitude = QUEUE_SIZE;
            for (int i = 0; i < magnitude; ++i) enqueueLocked(direction);
            LOCK.notifyAll();
        }
        return true;
    }

    /** No public reference proves a CarPlay auto-zoom command; keep this OEM. */
    public static boolean consumeMapScaleSetting(int setting) {
        return false;
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

    private static void enqueueLocked(int direction) {
        if (queueCount == QUEUE_SIZE) {
            queueHead = (queueHead + 1) % QUEUE_SIZE;
            --queueCount;
        }
        QUEUE[queueTail] = direction;
        queueTail = (queueTail + 1) % QUEUE_SIZE;
        ++queueCount;
    }

    private static int dequeueLocked() {
        int direction = QUEUE[queueHead];
        queueHead = (queueHead + 1) % QUEUE_SIZE;
        --queueCount;
        return direction;
    }

    private static void clearLocked() {
        queueHead = queueTail = queueCount = 0;
    }

    private static void runCommands() {
        DatagramSocket socket = null;
        InetAddress loopback = null;
        for (;;) {
            int direction;
            synchronized (LOCK) {
                while (queueCount == 0) {
                    try { LOCK.wait(); } catch (InterruptedException ignored) { }
                }
                direction = dequeueLocked();
            }
            try {
                if (!PorscheCluster.carPlayReady()) {
                    synchronized (LOCK) { clearLocked(); }
                    continue;
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
            }
        }
    }
}
