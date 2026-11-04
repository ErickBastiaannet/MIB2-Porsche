package de.audi.tghu.navi.app.cluster;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.zip.CRC32;

/** Host-only contract test for the native CWRG1 street-text envelope. */
public final class RouteGuidanceTextFixture {
    private static String hex(String value) throws Exception {
        byte[] raw = value.getBytes("UTF-8");
        StringBuilder result = new StringBuilder();
        for (byte item : raw) result.append(String.format("%02x", item & 255));
        return result.toString();
    }

    public static void main(String[] args) throws Exception {
        File stateFile = new File(args[0]);
        long now = System.currentTimeMillis() / 1000L;
        String body = "CWRG2 7 " + now + " 1 350 89 13 64 0 0 12345 3600 2 "
            + hex("Nieuwe Erpseweg") + " " + hex("N279") + " " + hex("Uden") + " ";
        CRC32 crc = new CRC32();
        crc.update(body.getBytes(StandardCharsets.US_ASCII));
        String line = body + String.format("%08x\n", crc.getValue());
        try (FileOutputStream stream = new FileOutputStream(stateFile)) {
            stream.write(line.getBytes(StandardCharsets.US_ASCII));
        }
        System.setProperty("connectwow.carplay.guidanceFile", stateFile.getAbsolutePath());
        Method read = PorscheRouteGuidance.class.getDeclaredMethod("read");
        read.setAccessible(true);
        Object state = read.invoke(null);
        Field current = state.getClass().getDeclaredField("currentRoad");
        Field turn = state.getClass().getDeclaredField("turnTo");
        current.setAccessible(true); turn.setAccessible(true);
        if (!"Nieuwe Erpseweg".equals(current.get(state)) || !"N279".equals(turn.get(state)))
            throw new AssertionError("street fields did not survive CWRG1 transport");

        Field listenerField = PorscheRouteGuidance.class.getDeclaredField("listener");
        Field appliedAt = PorscheRouteGuidance.class.getDeclaredField("lastAppliedAt");
        listenerField.setAccessible(true); appliedAt.setAccessible(true);
        CombiBAPListener listener = new CombiBAPListener();
        listenerField.set(null, listener);
        Method update = PorscheRouteGuidance.class.getDeclaredMethod("update", state.getClass());
        update.setAccessible(true);
        update.invoke(null, state);
        if (listener.distanceCalls != 1) throw new AssertionError("first guidance update missing");
        if (listener.destinationDistance != 12345 || listener.destinationTime != 3600)
            throw new AssertionError("destination distance/time missing");
        update.invoke(null, state);
        if (listener.distanceCalls != 1) throw new AssertionError("guidance update was not rate limited");
        appliedAt.setLong(null, System.currentTimeMillis() - 2100L);
        update.invoke(null, state);
        if (listener.distanceCalls != 2) throw new AssertionError("guidance heartbeat missing");
        Method interval = PorscheRouteGuidance.class.getDeclaredMethod("updateInterval", int.class);
        Method threshold = PorscheRouteGuidance.class.getDeclaredMethod("updateThreshold", int.class);
        interval.setAccessible(true); threshold.setAccessible(true);
        if (((Long)interval.invoke(null, 6000)).longValue() != 2000L
                || ((Integer)threshold.invoke(null, 6000)).intValue() != 100
                || ((Long)interval.invoke(null, 50)).longValue() != 250L
                || ((Integer)threshold.invoke(null, 50)).intValue() != 1)
            throw new AssertionError("dynamic distance pacing mismatch");
        System.out.println("PORSCHE_GUIDANCE_TEXT_PASS street, destination, heartbeat and distance pacing");
    }
}
