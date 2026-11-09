package de.audi.tghu.navi.app.cluster;

import java.io.*;
import java.util.StringTokenizer;
import java.util.zip.CRC32;
import org.dsi.ifc.navigation.BapManeuverDescriptor;
import org.dsi.ifc.navigation.NavLaneGuidanceData;

/**
 * Bridges validated iAP2 route-guidance state to Porsche's existing BAP
 * navigation output.  Keeping this class in the OEM package deliberately
 * permits use of the package-private conversion methods without reflection.
 */
public final class PorscheRouteGuidance {
    private static final long HEARTBEAT_MILLIS = setting("connectwow.carplay.guidanceHeartbeatMillis", 2000L, 500L, 10000L);
    private static final long READ_FAILURE_GRACE_MILLIS = setting("connectwow.carplay.guidanceReadGraceMillis", 4000L, 1000L, 15000L);
    private static final long STATE_MAX_AGE_SECONDS = setting("connectwow.carplay.guidanceStateMaxAgeSeconds", 6L, 3L, 30L);
    private static final long ARRIVAL_HOLD_MILLIS = setting("connectwow.carplay.guidanceArrivalHoldMillis", 5000L, 0L, 15000L);
    private static final String LOG_PATH = System.getProperty("connectwow.carplay.guidanceLog", "/ramdisk/cw-porsche-rgi-java.log");
    private static final Object LOCK = new Object();
    private static CombiBAPListener listener;
    private static boolean started;
    private static long appliedEpoch = -1;
    private static long lastAppliedAt;
    private static long lastValidReadAt;
    private static long arrivalHoldUntil;
    private static int lastDistance = -1;
    private static int lastMain = -1;
    private static String lastSemanticKey = "";
    private static boolean active;
    private static long lastFailureLog;

    private PorscheRouteGuidance() { }

    private static long setting(String name, long fallback, long minimum, long maximum) {
        try {
            long value = Long.parseLong(System.getProperty(name, Long.toString(fallback)));
            return Math.max(minimum, Math.min(maximum, value));
        } catch (Throwable ignored) { return fallback; }
    }

    public static void attach(CombiBAPListener value) {
        if (value == null) return;
        synchronized (LOCK) {
            listener = value;
            // A replacement listener represents a freshly-created OEM BAP
            // service.  Replay the complete state instead of assuming the
            // previous instance's cluster state survived.
            appliedEpoch = -1;
            lastAppliedAt = 0L;
            lastSemanticKey = "";
            if (started) return;
            Thread worker = new Thread(new Runnable() {
                public void run() { poll(); }
            }, "cw-porsche-route-guidance");
            worker.setDaemon(true);
            started = true;
            worker.start();
        }
    }

    private static void poll() {
        for (;;) {
            try {
                State state = read();
                lastValidReadAt = System.currentTimeMillis();
                update(state);
            }
            catch (Throwable unavailable) {
                // Atomic rename normally prevents partial reads, but the
                // native publisher and Java bundle do not start in lockstep.
                // Keep the last valid guidance briefly instead of flashing
                // back to OEM navigation on one transient read failure.
                long now = System.currentTimeMillis();
                if (now - lastFailureLog >= 5000L) {
                    log("guidance failure: ".concat(unavailable.toString()));
                    lastFailureLog = now;
                }
                if (lastValidReadAt == 0L || now - lastValidReadAt >= READ_FAILURE_GRACE_MILLIS)
                    clearIfNeeded();
            }
            try { Thread.sleep(250L); }
            catch (InterruptedException ignored) { }
        }
    }

    private static State read() throws Exception {
        String path = System.getProperty("connectwow.carplay.guidanceFile", "/ramdisk/cw-carplay-guidance.v1");
        FileInputStream stream = new FileInputStream(path);
        byte[] data = new byte[4096]; int count = 0, next;
        try {
            while (count < data.length && (next = stream.read()) != -1) data[count++] = (byte)next;
            if (count == data.length) throw new IOException("guidance state too large");
        } finally { stream.close(); }
        String line = new String(data, 0, count, "US-ASCII");
        if (!line.endsWith("\n")) throw new IOException("incomplete guidance state");
        int split = line.lastIndexOf(' ');
        if (split < 0 || line.length() != split + 10) throw new IOException("invalid guidance checksum");
        byte[] prefix = line.substring(0, split + 1).getBytes("US-ASCII");
        CRC32 crc = new CRC32(); crc.update(prefix);
        if (Long.parseLong(line.substring(split + 1, line.length() - 1), 16) != crc.getValue())
            throw new IOException("guidance checksum mismatch");
        StringTokenizer fields = new StringTokenizer(line.substring(0, split), " ");
        if (fields.countTokens() < 12)
            throw new IOException("invalid guidance version");
        String version = fields.nextToken();
        boolean extended = version.equals("CWRG2");
        if (!extended && !version.equals("CWRG1")) throw new IOException("invalid guidance version");
        State state = new State();
        state.epoch = Long.parseLong(fields.nextToken());
        state.timestamp = Long.parseLong(fields.nextToken());
        state.active = Integer.parseInt(fields.nextToken()) == 1;
        state.distance = bounded(fields.nextToken(), 0, 2000000);
        state.bargraph = bounded(fields.nextToken(), 0, 255);
        state.main = bounded(fields.nextToken(), 0, 255);
        state.direction = bounded(fields.nextToken(), 0, 255);
        state.z = bounded(fields.nextToken(), -16, 16);
        int lanes = bounded(fields.nextToken(), 0, 12);
        if (extended) {
            state.distanceRemaining = bounded(fields.nextToken(), 0, 50000000);
            state.timeRemaining = boundedLong(fields.nextToken(), 0L, 604800L);
            state.laneVisibility = bounded(fields.nextToken(), 0, 2);
        }
        if (fields.countTokens() != lanes + (extended ? 3 : 2)) throw new IOException("invalid guidance field count");
        state.lanes = new NavLaneGuidanceData[lanes];
        StringBuffer laneSignature = new StringBuffer();
        for (int i = 0; i < lanes; ++i) {
            String laneToken = fields.nextToken();
            if (i != 0) laneSignature.append('|');
            laneSignature.append(laneToken);
            state.lanes[i] = lane(laneToken);
        }
        state.laneSignature = laneSignature.toString();
        state.currentRoad = text(fields.nextToken());
        state.turnTo = text(fields.nextToken());
        state.destination = extended ? text(fields.nextToken()) : "";
        long now = System.currentTimeMillis() / 1000L;
        if (state.epoch <= 0 || state.timestamp > now || now - state.timestamp > STATE_MAX_AGE_SECONDS)
            throw new IOException("stale guidance state");
        return state;
    }

    private static String text(String hex) throws IOException {
        if (hex.equals("-")) return "";
        if ((hex.length() & 1) != 0 || hex.length() > 384) throw new IOException("invalid guidance text");
        byte[] value = new byte[hex.length() / 2];
        for (int i = 0; i < value.length; ++i) {
            int high = Character.digit(hex.charAt(i * 2), 16);
            int low = Character.digit(hex.charAt(i * 2 + 1), 16);
            if (high < 0 || low < 0) throw new IOException("invalid guidance text hex");
            value[i] = (byte)((high << 4) | low);
        }
        return new String(value, "UTF-8");
    }

    private static int bounded(String text, int minimum, int maximum) throws IOException {
        int value;
        try { value = Integer.parseInt(text); }
        catch (NumberFormatException invalid) { throw new IOException("invalid guidance number"); }
        if (value < minimum || value > maximum) throw new IOException("guidance number out of range");
        return value;
    }

    private static long boundedLong(String text, long minimum, long maximum) throws IOException {
        long value;
        try { value = Long.parseLong(text); }
        catch (NumberFormatException invalid) { throw new IOException("invalid guidance number"); }
        if (value < minimum || value > maximum) throw new IOException("guidance number out of range");
        return value;
    }

    private static NavLaneGuidanceData lane(String token) throws IOException {
        StringTokenizer values = new StringTokenizer(token, ",", true);
        int[] parsed = new int[7]; int index = 0; boolean expectValue = true;
        while (values.hasMoreTokens()) {
            String value = values.nextToken();
            if (value.equals(",")) { if (expectValue) throw new IOException("empty lane value"); expectValue = true; }
            else {
                if (!expectValue || index == parsed.length) throw new IOException("invalid lane value");
                // Native carries the complete uint16 wire value; the DSI
                // constructor below restores its signed short (-45 = 65491).
                parsed[index] = bounded(value, 0, index == 1 ? 65535 : 255);
                ++index;
                expectValue = false;
            }
        }
        if (index != parsed.length || expectValue) throw new IOException("incomplete lane value");
        return new NavLaneGuidanceData((short)parsed[0], (short)parsed[1], new byte[0],
            (short)parsed[2], (byte)parsed[3], (byte)parsed[4], (byte)parsed[5], (byte)parsed[6]);
    }

    private static void update(State state) {
        CombiBAPListener target;
        synchronized (LOCK) { target = listener; }
        long now = System.currentTimeMillis();
        if (target == null) return;
        // The Porsche cluster expires navigation fields even if their value
        // has not changed.  Re-publish the complete descriptor every two
        // seconds, matching the proven PCM5 behaviour while retaining the
        // K5137-specific package-private BAP interface.
        if (!state.active) {
            if (active && lastMain == 3 && arrivalHoldUntil == 0L)
                arrivalHoldUntil = now + ARRIVAL_HOLD_MILLIS;
            if (arrivalHoldUntil > now) return;
            if (active) clear(target);
            appliedEpoch = state.epoch;
            return;
        }
        arrivalHoldUntil = 0L;
        String semanticKey = semanticKey(state);
        boolean semanticChanged = !semanticKey.equals(lastSemanticKey);
        long elapsed = now - lastAppliedAt;
        if (!semanticChanged && elapsed < HEARTBEAT_MILLIS) {
            int delta = lastDistance < 0 ? Integer.MAX_VALUE : Math.abs(state.distance - lastDistance);
            if (state.epoch == appliedEpoch || elapsed < updateInterval(state.distance)
                    || delta < updateThreshold(state.distance)) return;
        }
        target.setGALState(true);
        target.setViewMode(1);
        target.setRgActive(true);
        target.setDistanceToNextManeuver(state.distance, true, state.bargraph);
        target.setManeuverDescriptor(new BapManeuverDescriptor[]{
            new BapManeuverDescriptor(state.main, state.direction, state.z, new byte[0])
        });
        boolean showLanes = state.laneVisibility != 1 && state.lanes.length != 0;
        target.setLaneGuidance(showLanes ? state.lanes : new NavLaneGuidanceData[0], showLanes);
        // MU1417 exposes this exact package-private BAP path. The cluster's
        // position line shows the next road when available, otherwise the
        // road currently being driven.
        if (state.currentRoad.length() != 0) target.setCurrentStreet(state.currentRoad);
        target.setRgDistanceToNextDestination(state.distanceRemaining, state.distanceRemaining > 0);
        target.setRgTimeToNextDestination(state.timeRemaining * 1000L, false, state.timeRemaining > 0);
        active = true;
        appliedEpoch = state.epoch;
        lastAppliedAt = now;
        lastDistance = state.distance;
        lastMain = state.main;
        lastSemanticKey = semanticKey;
        StringBuffer trace = new StringBuffer("apply epoch=");
        trace.append(state.epoch).append(" maneuver=").append(state.main).append('/').append(state.direction)
             .append(" next_m=").append(state.distance).append(" remaining_m=").append(state.distanceRemaining)
             .append(" remaining_s=").append(state.timeRemaining).append(" lanes=").append(state.lanes.length);
        log(trace.toString());
    }

    private static void clearIfNeeded() {
        CombiBAPListener target;
        synchronized (LOCK) { target = listener; }
        if (target != null && active) clear(target);
    }

    private static void clear(CombiBAPListener target) {
        try {
            target.setLaneGuidance(new NavLaneGuidanceData[0], false);
            target.setManeuverDescriptor(new BapManeuverDescriptor[0]);
            target.setDistanceToNextManeuver(0, false, 0);
            target.setRgDistanceToNextDestination(0, false);
            target.setRgTimeToNextDestination(0L, false, false);
            target.setGALState(false);
            target.setRgActive(false);
        } catch (Throwable ignored) { }
        active = false;
        lastAppliedAt = 0L;
        lastDistance = -1;
        lastMain = -1;
        lastSemanticKey = "";
        arrivalHoldUntil = 0L;
        log("clear");
    }

    private static void log(String message) {
        File file = new File(LOG_PATH);
        try {
            if (file.exists() && file.length() > 65536L) {
                File old = new File(LOG_PATH.concat(".old"));
                if (old.exists()) old.delete();
                file.renameTo(old);
            }
            FileOutputStream stream = new FileOutputStream(file, true);
            try {
                StringBuffer line = new StringBuffer();
                line.append(System.currentTimeMillis()).append(' ').append(message).append('\n');
                stream.write(line.toString().getBytes("UTF-8"));
            } finally { stream.close(); }
        } catch (Throwable ignored) { }
    }

    private static long updateInterval(int distance) {
        if (distance > 5000) return 2000L;
        if (distance > 1000) return 1000L;
        if (distance > 500) return 750L;
        if (distance > 200) return 500L;
        if (distance > 100) return 350L;
        return 250L;
    }

    private static int updateThreshold(int distance) {
        if (distance > 5000) return 100;
        if (distance > 1000) return 50;
        if (distance > 500) return 25;
        if (distance > 200) return 10;
        if (distance > 100) return 5;
        return 1;
    }

    private static String semanticKey(State state) {
        StringBuffer key = new StringBuffer();
        key.append(state.main).append(':').append(state.direction).append(':').append(state.z)
           .append(':').append(state.laneVisibility).append(':').append(state.currentRoad)
           .append(':').append(state.turnTo).append(':').append(state.destination);
        key.append(':').append(state.laneSignature);
        return key.toString();
    }

    private static final class State {
        long epoch, timestamp;
        boolean active;
        int distance, distanceRemaining, bargraph, main, direction, z, laneVisibility;
        long timeRemaining;
        NavLaneGuidanceData[] lanes;
        String currentRoad, turnTo, destination, laneSignature;
    }
}
