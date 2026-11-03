package org.connectwow.tests;

import java.io.*;
import java.util.zip.CRC32;
import org.connectwow.carplay.PorscheGeometry;
import de.audi.tghu.navi.app.map.gui.layout.AbstractLayoutProvider;
import org.dsi.ifc.map.Rect;

/** Executes the legacy-version helper, with synthetic model objects only. */
public final class GeometryFixture extends AbstractLayoutProvider {
    public int getScreenWidth() { return 960; }
    public int getScreenHeight() { return 640; }

    static String[] read(String path) throws Exception {
        BufferedReader reader = new BufferedReader(new FileReader(path));
        String line;
        try { line = reader.readLine(); } finally { reader.close(); }
        int split = line.lastIndexOf(' ');
        CRC32 crc = new CRC32();
        crc.update(line.substring(0, split + 1).getBytes("US-ASCII"));
        if (Long.parseLong(line.substring(split + 1), 16) != crc.getValue()) throw new AssertionError("CRC");
        return line.split(" ");
    }

    public static void main(String[] args) throws Exception {
        String path = args[0];
        System.setProperty("connectwow.carplay.geometryFile", path);
        Rect area = new Rect();
        area.kordX = 40; area.kordY = 20; area.diffX = 880; area.diffY = 600;
        GeometryFixture layout = new GeometryFixture();
        PorscheGeometry.setVisible(true);
        PorscheGeometry.setCarPlayActive(true);
        PorscheGeometry.observe(layout, area, 2);
        String[] first = read(path);
        if (!first[3].equals("1") || !first[5].equals("1") || !first[7].equals("960")) throw new AssertionError("Initial observation");
        long generation = Long.parseLong(first[1]);
        Thread.sleep(2100L);
        String[] heartbeat = read(path);
        if (Long.parseLong(heartbeat[2]) <= Long.parseLong(first[2])) throw new AssertionError("Heartbeat missing");
        if (Long.parseLong(heartbeat[1]) != generation) throw new AssertionError("Heartbeat changed layout generation");
        // Invalid geometry must not modify the caller's rectangle and must
        // withdraw activity, without stopping the OEM function with an error.
        area.diffX = 1000;
        PorscheGeometry.observe(layout, area, 2);
        if (!read(path)[3].equals("0") || area.diffX != 1000) throw new AssertionError("Invalid geometry");
        area.diffX = 880;
        PorscheGeometry.observe(layout, area, 2);
        PorscheGeometry.setVisible(false);
        if (!read(path)[3].equals("1") || !read(path)[4].equals("0")) throw new AssertionError("Hidden");
        PorscheGeometry.setVisible(true);
        PorscheGeometry.setCarPlayActive(false);
        String[] disconnected = read(path);
        if (!disconnected[3].equals("1") || !disconnected[5].equals("0")) throw new AssertionError("Disconnect");
        System.out.println("PORSCHE_JAVA_OBSERVER_PASS heartbeat, CRC, invalid geometry, visibility, disconnect");
    }
}
