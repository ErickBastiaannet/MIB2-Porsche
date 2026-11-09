package org.connectwow.tests;

import java.io.*;
import java.net.*;
import java.util.zip.CRC32;
import org.connectwow.carplay.PorscheCluster;
import org.connectwow.carplay.PorscheClusterControls;

/** End-to-end regression for signed Porsche MapScale -> semantic CarPlay zoom. */
public final class ControlsFixture {
    private static File ready;
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    private static void lease(long epoch) throws Exception {
        String prefix = "CWRD1 " + epoch + " " + (System.currentTimeMillis()/1000L) + " 800 480 ";
        CRC32 crc = new CRC32(); crc.update(prefix.getBytes("US-ASCII"));
        String sum = Long.toHexString(crc.getValue()); while (sum.length() < 8) sum = "0" + sum;
        FileOutputStream out = new FileOutputStream(ready);
        try { out.write((prefix + sum + "\n").getBytes("US-ASCII")); } finally { out.close(); }
    }
    private static String receive(DatagramSocket socket) throws Exception {
        byte[] data = new byte[32]; DatagramPacket packet = new DatagramPacket(data, data.length);
        socket.receive(packet); return new String(data, 0, packet.getLength(), "US-ASCII");
    }
    public static void main(String[] args) throws Exception {
        ready = new File(args[0] + ".controls-ready"); ready.delete();
        System.setProperty("connectwow.carplay.readyFile", ready.getAbsolutePath());
        System.setProperty("connectwow.carplay.contextFile", new File(args[0] + ".controls-context").getAbsolutePath());
        DatagramSocket socket = new DatagramSocket(7032, InetAddress.getByName("127.0.0.1"));
        socket.setSoTimeout(700);
        try {
            lease(41);
            check(PorscheCluster.carPlayEpoch() == 41, "native renderer lease not accepted");
            check(PorscheClusterControls.consumeMapScale(1), "leased zoom not consumed");
            check("zoom-out".equals(receive(socket)), "positive MapScale must zoom out");
            // MU1417 renews the first lease value on every heartbeat. It is a
            // freshness token, not a stable renderer-session identifier.
            lease(42);
            check(PorscheClusterControls.consumeMapScale(-1), "owned zoom not consumed");
            check("zoom-in".equals(receive(socket)), "heartbeat renewal dropped negative MapScale");
            check(!PorscheClusterControls.consumeMapScaleSetting(1),
                    "unproven CarPlay auto zoom must remain OEM");

            // Preserve every detent in FIFO order, including a quick reversal.
            PorscheClusterControls.consumeMapScale(2);
            PorscheClusterControls.consumeMapScale(-1);
            check("zoom-out".equals(receive(socket)), "first burst step missing");
            check("zoom-out".equals(receive(socket)), "second burst step missing");
            check("zoom-in".equals(receive(socket)), "reverse detent order changed");

            // No renderer lease means no phone-map command.
            ready.delete(); socket.setSoTimeout(320);
            check(!PorscheClusterControls.consumeMapScale(1), "OEM zoom was consumed");
            try { throw new AssertionError("zoom escaped during OEM fallback: " + receive(socket)); }
            catch (SocketTimeoutException expected) { }
        } finally { socket.close(); ready.delete(); }
        System.out.println("PORSCHE_ZOOM_PASS signed meters-scale steps, FIFO reversal, fallback guard");
    }
}
