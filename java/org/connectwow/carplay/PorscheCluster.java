package org.connectwow.carplay;

import java.io.*;
import java.util.StringTokenizer;
import java.util.zip.CRC32;
import org.dsi.ifc.displaymanagement.DisplayContext;

/** Maps only cluster map contexts; main PCM and other instrument pages pass through. */
public final class PorscheCluster {
    public static final int WINDOW = 78;
    private static boolean installed, wideContexts, clusterOwned;
    private static int lastRequested = -1, lastMap = -1;
    private PorscheCluster() { }

    public static synchronized void installContexts(DisplayContext[] contexts) {
        installed = false;
        wideContexts = false;
        try {
            if (contexts == null || contexts.length <= 70 || contexts[70] != null) return;
            if (contexts.length > 149 && contexts[149] != null) return;
            DisplayContext map = new DisplayContext(70, new int[]{WINDOW});
            DisplayContext overlaid = new DisplayContext(149, new int[]{20, WINDOW});
            contexts[70] = map;
            wideContexts = contexts.length > 149;
            if (wideContexts) contexts[149] = overlaid;
            installed = true;
        } catch (Throwable unavailable) { installed = false; }
    }

    public static boolean mapContext(int context) {
        if (context < 0 || context > 157) return false;
        int base = context % 79;
        return base == 72 || base == 74 || base == 76 || base == 77;
    }

    public static synchronized int selectContext(int requested, int terminal) {
        if (terminal != 1 || !installed || requested < 0 || requested > 157) return requested;
        if (requested == 70 || requested == 149) { clusterOwned = true; return requested; }
        try {
            lastRequested = requested;
            if (mapContext(requested)) lastMap = requested;
            saveContext();
            if (!mapContext(requested) || !ready()) { clusterOwned = false; return requested; }
            int base = requested % 79;
            clusterOwned = true;
            return wideContexts && (requested >= 79 || base == 74 || base == 77) ? 149 : 70;
        } catch (Throwable unavailable) { clusterOwned = false; return requested; }
    }

    /** Ownership expires with the native lease so OEM zoom is never swallowed after fallback. */
    public static synchronized boolean carPlayOwnsCluster() {
        return clusterOwned && carPlayReady();
    }

    /** Non-blocking callers must invoke this from a worker, never an HMI callback. */
    public static boolean carPlayReady() {
        return carPlayEpoch() > 0;
    }

    /** Returns the current native-renderer generation, or zero for an invalid/stale lease. */
    public static long carPlayEpoch() {
        try { return readyEpoch(); } catch (Throwable unavailable) { return 0; }
    }

    private static boolean ready() throws Exception { return readyEpoch() > 0; }

    private static long readyEpoch() throws Exception {
        String path = System.getProperty("connectwow.carplay.readyFile", "/ramdisk/cw-carplay-ready.v1");
        FileInputStream stream = new FileInputStream(path);
        byte[] bytes = new byte[192]; int count = 0, next;
        try {
            while (count < bytes.length && (next = stream.read()) != -1) bytes[count++] = (byte)next;
            if (count == bytes.length) return 0;
        } finally { stream.close(); }
        String line = new String(bytes, 0, count, "US-ASCII");
        if (!line.endsWith("\n")) return 0;
        int split = line.lastIndexOf(' ');
        if (split < 0 || line.length() != split + 10) return 0;
        CRC32 crc = new CRC32(); crc.update(line.substring(0, split + 1).getBytes("US-ASCII"));
        if (Long.parseLong(line.substring(split + 1, line.length() - 1), 16) != crc.getValue()) return 0;
        StringTokenizer tokens = new StringTokenizer(line.substring(0, split), " ");
        if (tokens.countTokens() != 5 || !tokens.nextToken().equals("CWRD1")) return 0;
        long epoch = Long.parseLong(tokens.nextToken()), timestamp = Long.parseLong(tokens.nextToken());
        long width = Long.parseLong(tokens.nextToken()), height = Long.parseLong(tokens.nextToken());
        long now = System.currentTimeMillis() / 1000L;
        return epoch > 0 && timestamp <= now && now - timestamp <= 3
            && width >= 64 && height >= 64 && width <= 1920 && height <= 1080 ? epoch : 0;
    }

    private static void saveContext() throws Exception {
        String path = System.getProperty("connectwow.carplay.contextFile", "/ramdisk/cw-carplay-context.v1");
        StringBuffer body = new StringBuffer("CWCT1 ");
        body.append(System.currentTimeMillis() / 1000L).append(' ');
        body.append(lastRequested).append(' ').append(lastMap < 0 ? 0 : lastMap).append(' ');
        byte[] prefix = body.toString().getBytes("US-ASCII");
        CRC32 crc = new CRC32(); crc.update(prefix);
        String checksum = Long.toHexString(crc.getValue());
        while (checksum.length() < 8) checksum = "0".concat(checksum);
        body.append(checksum).append('\n');
        File file = new File(path), temporary = new File(path.concat(".tmp"));
        FileOutputStream stream = new FileOutputStream(temporary);
        try { stream.write(body.toString().getBytes("US-ASCII")); } finally { stream.close(); }
        if (!temporary.renameTo(file)) { temporary.delete(); throw new IOException("Context publication failed"); }
    }
}
