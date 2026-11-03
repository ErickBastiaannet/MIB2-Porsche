package org.connectwow.carplay;

import java.io.File;
import java.io.FileOutputStream;
import java.util.zip.CRC32;
import de.audi.tghu.navi.app.map.gui.layout.AbstractLayoutProvider;
import org.dsi.ifc.map.Rect;

/** Observes the existing cluster layout; never changes a model or rectangle. */
public final class PorscheGeometry implements Runnable {
    private static int width, height, x, y, areaWidth, areaHeight, mode;
    private static long generation;
    private static boolean valid, visible, carPlayActive, started;
    private static final Object LOCK = new Object();

    private PorscheGeometry() { }

    public static void observe(AbstractLayoutProvider layout, Rect area, int transport) {
        try {
            int w = layout.getScreenWidth(), h = layout.getScreenHeight();
            synchronized (LOCK) {
                if (area == null || (transport != 2 && transport != 3)
                        || w < 64 || h < 64 || w > 8192 || h > 8192
                        || area.kordX < 0 || area.kordY < 0
                        || area.diffX < 1 || area.diffY < 1
                        || area.diffX > w || area.diffY > h
                        || area.kordX > w - area.diffX || area.kordY > h - area.diffY) {
                    valid = false;
                    generation++;
                } else {
                    if (!valid || width != w || height != h || x != area.kordX
                            || y != area.kordY || areaWidth != area.diffX
                            || areaHeight != area.diffY || mode != transport) generation++;
                    width = w; height = h; x = area.kordX; y = area.kordY;
                    areaWidth = area.diffX; areaHeight = area.diffY; mode = transport;
                    valid = true;
                    if (!started) {
                        Thread worker = new Thread(new PorscheGeometry(), "ConnectWow cluster geometry");
                        worker.setDaemon(true);
                        worker.start();
                        started = true;
                    }
                }
                publish();
            }
        } catch (Throwable failure) { invalidate(); }
    }

    public static void setVisible(boolean value) {
        try {
            synchronized (LOCK) {
                if (visible != value) generation++;
                visible = value;
                publish();
            }
        } catch (Throwable failure) { invalidate(); }
    }

    /** Manager activity is a prerequisite, not evidence of received video. */
    public static void setCarPlayActive(boolean value) {
        try {
            synchronized (LOCK) {
                if (carPlayActive != value) generation++;
                carPlayActive = value;
                publish();
            }
        } catch (Throwable failure) { invalidate(); }
    }

    private static void invalidate() {
        synchronized (LOCK) {
            valid = false;
            generation++;
            try { publish(); } catch (Throwable ignored) { }
        }
    }

    private static void publish() throws Exception {
        if (width == 0 || height == 0) return;
        File file = new File(System.getProperty("connectwow.carplay.geometryFile", "/ramdisk/cw-carplay-geometry.v3"));
        File temporary = new File(file.getPath().concat(".tmp"));
        StringBuffer line = new StringBuffer("CWCP3 ");
        line.append(generation).append(' ').append(System.currentTimeMillis() / 1000L).append(' ');
        line.append(valid ? 1 : 0).append(' ').append(visible ? 1 : 0).append(' ');
        line.append(carPlayActive ? 1 : 0).append(' ').append(mode).append(' ');
        line.append(width).append(' ').append(height).append(' ');
        line.append(x).append(' ').append(y).append(' ').append(areaWidth).append(' ').append(areaHeight).append(' ');
        byte[] prefix = line.toString().getBytes("US-ASCII");
        CRC32 crc = new CRC32(); crc.update(prefix);
        String checksum = Long.toHexString(crc.getValue());
        while (checksum.length() < 8) checksum = "0".concat(checksum);
        line.append(checksum).append('\n');
        FileOutputStream stream = new FileOutputStream(temporary);
        try { stream.write(line.toString().getBytes("US-ASCII")); }
        finally { stream.close(); }
        if (!temporary.renameTo(file)) {
            temporary.delete();
            // Expiry of the previous record makes the native reader fall back.
            throw new java.io.IOException("Geometry publication failed");
        }
    }

    public void run() {
        while (true) {
            try {
                Thread.sleep(1000L);
                synchronized (LOCK) { publish(); }
            } catch (InterruptedException stopped) { return; }
            catch (Throwable failure) { invalidate(); }
        }
    }
}
