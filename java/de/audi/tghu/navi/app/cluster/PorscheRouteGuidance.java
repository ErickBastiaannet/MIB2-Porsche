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
    private static final Object LOCK = new Object();
    private static CombiBAPListener listener;
    private static boolean started;
    private static long appliedEpoch = -1;
    private static boolean active;

    private PorscheRouteGuidance() { }

    public static void attach(CombiBAPListener value) {
        if (value == null) return;
        synchronized (LOCK) {
            listener = value;
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
            try { update(read()); }
            catch (Throwable unavailable) { clearIfNeeded(); }
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
        if (fields.countTokens() < 10 || !fields.nextToken().equals("CWRG1"))
            throw new IOException("invalid guidance version");
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
        if (fields.countTokens() != lanes) throw new IOException("invalid lane count");
        state.lanes = new NavLaneGuidanceData[lanes];
        for (int i = 0; i < lanes; ++i) state.lanes[i] = lane(fields.nextToken());
        long now = System.currentTimeMillis() / 1000L;
        if (state.epoch <= 0 || state.timestamp > now || now - state.timestamp > 3)
            throw new IOException("stale guidance state");
        return state;
    }

    private static int bounded(String text, int minimum, int maximum) throws IOException {
        int value;
        try { value = Integer.parseInt(text); }
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
            else { if (!expectValue || index == parsed.length) throw new IOException("invalid lane value"); parsed[index++] = bounded(value, 0, 255); expectValue = false; }
        }
        if (index != parsed.length || expectValue) throw new IOException("incomplete lane value");
        return new NavLaneGuidanceData((short)parsed[0], (short)parsed[1], new byte[0],
            (short)parsed[2], (byte)parsed[3], (byte)parsed[4], (byte)parsed[5], (byte)parsed[6]);
    }

    private static void update(State state) {
        CombiBAPListener target;
        synchronized (LOCK) { target = listener; }
        if (target == null || state.epoch == appliedEpoch) return;
        if (!state.active) { clear(target); appliedEpoch = state.epoch; return; }
        target.setGALState(true);
        target.setDistanceToNextManeuver(state.distance, true, state.bargraph);
        target.setManeuverDescriptor(new BapManeuverDescriptor[]{
            new BapManeuverDescriptor(state.main, state.direction, state.z, new byte[0])
        });
        target.setLaneGuidance(state.lanes, state.lanes.length != 0);
        active = true;
        appliedEpoch = state.epoch;
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
            target.setGALState(false);
        } catch (Throwable ignored) { }
        active = false;
    }

    private static final class State {
        long epoch, timestamp;
        boolean active;
        int distance, bargraph, main, direction, z;
        NavLaneGuidanceData[] lanes;
    }
}
