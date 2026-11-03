package org.connectwow.tests;

import java.io.*;
import java.util.zip.CRC32;
import org.connectwow.carplay.PorscheCluster;
import org.dsi.ifc.displaymanagement.DisplayContext;

public final class ClusterFixture {
    static String ready;
    static void check(boolean condition) { if (!condition) throw new AssertionError(); }
    static void lease(long timestamp, boolean corrupt) throws Exception {
        String prefix = "CWRD1 7 " + timestamp + " 960 640 ";
        CRC32 crc = new CRC32(); crc.update(prefix.getBytes("US-ASCII"));
        String sum = Long.toHexString(crc.getValue());
        while (sum.length() < 8) sum = "0" + sum;
        FileOutputStream out = new FileOutputStream(ready);
        try { out.write((prefix + (corrupt ? "00000000" : sum) + "\n").getBytes("US-ASCII")); }
        finally { out.close(); }
    }
    public static void main(String[] args) throws Exception {
        ready=args[0]+".ready";
        System.setProperty("connectwow.carplay.readyFile", ready);
        System.setProperty("connectwow.carplay.contextFile", args[0]+".context");
        new File(ready).delete();
        DisplayContext[] contexts = new DisplayContext[158];
        DisplayContext stock = new DisplayContext(72, new int[]{33}); contexts[72]=stock;
        PorscheCluster.installContexts(contexts);
        check(contexts[72]==stock && contexts[70].layers[0]==78 && contexts[149].layers[1]==78);
        check(PorscheCluster.selectContext(72,1)==72);
        long now = System.currentTimeMillis()/1000L;
        lease(now,false);
        // Windows File.renameTo does not replace an existing destination;
        // QNX rename does. Keep this host fixture focused on routing logic.
        new File(args[0]+".context").delete();
        check(PorscheCluster.selectContext(72,1)==70);
        new File(args[0]+".context").delete();
        check(PorscheCluster.selectContext(151,1)==149);
        new File(args[0]+".context").delete();
        check(PorscheCluster.selectContext(74,1)==149);
        check(PorscheCluster.selectContext(78,0)==78);
        check(PorscheCluster.selectContext(75,1)==75);
        lease(now-30,false); new File(args[0]+".context").delete(); check(PorscheCluster.selectContext(72,1)==72);
        lease(now+30,false); new File(args[0]+".context").delete(); check(PorscheCluster.selectContext(72,1)==72);
        lease(now,true); new File(args[0]+".context").delete(); check(PorscheCluster.selectContext(72,1)==72);
        lease(now,false);
        PorscheCluster.installContexts(contexts); // already occupied: reject conflicting registration
        new File(args[0]+".context").delete(); check(PorscheCluster.selectContext(72,1)==72 && contexts[72]==stock);
        contexts=new DisplayContext[79]; PorscheCluster.installContexts(contexts);
        new File(args[0]+".context").delete();
        check(PorscheCluster.selectContext(72,1)==70);
        new File(args[0]+".context").delete();
        check(PorscheCluster.selectContext(74,1)==70);
        System.out.println("PORSCHE_JAVA_CLUSTER_PASS context isolation, map switching, stale/corrupt lease, conflicts");
    }
}
