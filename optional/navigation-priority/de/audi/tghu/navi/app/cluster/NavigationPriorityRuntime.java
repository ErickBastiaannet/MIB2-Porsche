package de.audi.tghu.navi.app.cluster;

import java.io.*;
import java.util.StringTokenizer;
import java.util.zip.CRC32;
import org.connectwow.carplay.PorscheNavigationPriority;

/** Opt-in adapter. All guidance writes and native route events share LOCK. */
public final class NavigationPriorityRuntime {
    public static final Object LOCK = new Object();
    private static final String ROOT = System.getProperty("connectwow.carplay.priorityRoot", "/ramdisk");
    private static final boolean ENABLED = "porsche-first".equals(System.getProperty("connectwow.carplay.navigationPriority"));
    private static final PorscheNavigationPriority POLICY = new PorscheNavigationPriority();
    private static volatile int oemState = PorscheNavigationPriority.OEM_UNKNOWN;
    private static boolean ownsGuidance, preempting;
    private static Thread writer;
    private static int writerDepth, logLines, nativeWriters;
    private static long source;
    private NavigationPriorityRuntime() { }
    public static boolean permitsCarPlay() { return !ENABLED || (oemState == PorscheNavigationPriority.OEM_IDLE && uiReady()); }

    /** Valid DSI update, BEFORE it is dispatched to OEM listeners. */
    public static void beforeNative(boolean active, int validity) {
        if (!ENABLED || validity != 1) return;
        synchronized (LOCK) {
            if (!active && oemState == PorscheNavigationPriority.OEM_IDLE) return;
            oemState = active ? PorscheNavigationPriority.OEM_ROUTE : PorscheNavigationPriority.OEM_UNKNOWN;
            try { new File(ROOT.concat("/cw-carplay-ready.v1")).delete(); } catch(Throwable ignored) { }
            org.connectwow.carplay.PorscheClusterControls.cwDiscard();
            publish();
            // Finish/clear only our own output before native listeners publish.
            preempting = true;
            try { if (ownsGuidance) PorscheRouteGuidance.cwPreempt(); }
            catch(Throwable failed) { log("preempt-clear-failed"); }
            finally { preempting = false; writer = null; writerDepth = 0; ownsGuidance = false; }
            PorscheRouteGuidance.cwReset();
            publish();
            log(active ? "OEM_ROUTE" : "OEM_ENDING");
        }
    }
    /** After ClusterService has processed the original active/inactive update. */
    public static void afterNative(boolean active) {
        if (!ENABLED) return;
        synchronized (LOCK) {
            if (!active && oemState == PorscheNavigationPriority.OEM_IDLE) return;
            // Do not promote unknown/unobserved startup to idle from a synthetic call.
            if (active) oemState = PorscheNavigationPriority.OEM_ROUTE;
            else { oemState = PorscheNavigationPriority.OEM_IDLE; ownsGuidance = false; PorscheRouteGuidance.cwReset(); }
            publish();
            log(active ? "OEM_PUBLISHED" : "OEM_IDLE");
        }
    }
    /** No OEM listener monitor is held on entry. Do not hold LOCK across OEM calls. */
    public static int beginBap(boolean routeField) {
        if (!ENABLED) return 2;
        synchronized (LOCK) {
            if (writer == Thread.currentThread()) return 2;
            if (routeField && ownsGuidance && oemState == PorscheNavigationPriority.OEM_IDLE) return 0;
            nativeWriters++;
            return 1;
        }
    }
    public static void endBap(int ticket) {
        if (!ENABLED || ticket != 1) return;
        synchronized (LOCK) { nativeWriters--; LOCK.notifyAll(); }
    }
    /** Called under LOCK by the isolated guidance wrappers. */
    public static boolean enter(int operation, boolean routeActive) {
        if (!ENABLED) return true;
        while (nativeWriters > 0) {
            try { LOCK.wait(); } catch(InterruptedException stopped) { Thread.currentThread().interrupt(); return false; }
        }
        if (operation == 1) {
            if (!preempting && (oemState != PorscheNavigationPriority.OEM_IDLE || !ownsGuidance)) return false;
        } else {
            if (oemState != PorscheNavigationPriority.OEM_IDLE) return false;
            if (routeActive && !uiReady()) return false;
            if (!routeActive && !ownsGuidance) return false;
            if (routeActive) ownsGuidance = true; // includes partial writes if the OEM call fails
        }
        writer = Thread.currentThread(); writerDepth++;
        return true;
    }
    public static void leave(int operation, boolean active, boolean clearPending) {
        if (!ENABLED) return;
        if (operation == 1) ownsGuidance = clearPending;
        else if (active) ownsGuidance = true;
        if (writerDepth > 0) writerDepth--;
        if (writerDepth == 0) writer = null;
    }
    /** Reuses the existing guidance poll; no extra thread/constructor worker. */
    public static void poll() {
        if (!ENABLED) return;
        synchronized (LOCK) { publish(); }
    }
    private static boolean uiReady() {
        long[] r = record(ROOT.concat("/cw-carplay-ready.v1"), "CWRD1", 4);
        long[] a = record(ROOT.concat("/cw-nav-priority.applied"), "CWNPA1", 4);
        long owner = 0L;
        try { owner = sourceOwner(System.currentTimeMillis()/1000L); } catch(Throwable absent) { }
        return r != null && r[0] > 0 && r[2] >= 64 && r[3] >= 64 &&
            a != null && a[2] == 1 && owner > 1 && a[3] == owner;
    }
    private static void publish() {
        try {
            long now = System.currentTimeMillis()/1000L;
            try { source = sourceOwner(now); } catch(Throwable absentPhone) { source = 0L; }
            boolean ready = uiReady();
            PorscheNavigationPriority.Decision d = POLICY.request(oemState, ready, ownsGuidance, source);
            StringBuffer body = new StringBuffer("CWNP1 ");
            body.append(d.generation + 1L).append(' ').append(now).append(' ')
                .append(oemState == PorscheNavigationPriority.OEM_IDLE ? 1 : 0).append(' ').append(source).append(' ');
            byte[] prefix = body.toString().getBytes("US-ASCII");CRC32 crc = new CRC32();crc.update(prefix);
            String hex = Long.toHexString(crc.getValue());while(hex.length()<8)hex="0".concat(hex);
            body.append(hex).append('\n');
            File f=new File(ROOT.concat("/cw-nav-priority.v1")),t=new File(ROOT.concat("/cw-nav-priority.v1.tmp"));
            FileOutputStream out=new FileOutputStream(t);try{out.write(body.toString().getBytes("US-ASCII"));}finally{out.close();}
            if(!t.renameTo(f)){t.delete();throw new IOException("priority publication failed");}
            if(d.pending && d.mapSource == PorscheNavigationPriority.CARPLAY && ready) POLICY.acknowledge(d);
            // Native OEM restoration is acknowledged separately, not inferred from lease deletion.
            long[] ack=record(ROOT.concat("/cw-nav-priority.applied"), "CWNPA1",4);
            if(d.pending && d.mapSource == PorscheNavigationPriority.PORSCHE && ack!=null &&
                ack[0]==d.generation+1L && ack[2]==0 && ack[3]==source)POLICY.acknowledge(d);
        } catch(Throwable failed) { log("priority-publish-failed"); }
    }
    private static long sourceOwner(long now) throws Exception {
        StringTokenizer t=new StringTokenizer(read(ROOT.concat("/cw-porsche-altstream.ready")));
        if(t.countTokens()!=2)return 0L;
        long pid=Long.parseLong(t.nextToken()),at=Long.parseLong(t.nextToken());
        return pid>1&&pid<=2147483647L&&at<=now&&now-at<=3?pid:0L;
    }
    private static String read(String path) throws Exception {
        FileInputStream in=new FileInputStream(path);byte[] bytes=new byte[256];int n=0,b;
        try{while(n<bytes.length&&(b=in.read())!=-1)bytes[n++]=(byte)b;}finally{in.close();}
        if(n==bytes.length)throw new IOException("oversize priority record");
        return new String(bytes,0,n,"US-ASCII");
    }
    private static long[] record(String path,String magic,int count) {
        try {
            String s=read(path);int p=s.lastIndexOf(' ');
            if(!s.endsWith("\n")||p<0||s.length()!=p+10)return null;
            CRC32 crc=new CRC32();crc.update(s.substring(0,p+1).getBytes("US-ASCII"));
            if(Long.parseLong(s.substring(p+1,s.length()-1),16)!=crc.getValue())return null;
            StringTokenizer t=new StringTokenizer(s.substring(0,p)," ");
            if(t.countTokens()!=count+1||!magic.equals(t.nextToken()))return null;
            long[] v=new long[count];for(int i=0;i<count;i++){v[i]=Long.parseLong(t.nextToken());if(v[i]<0||v[i]>4294967295L)return null;}
            long now=System.currentTimeMillis()/1000L;if(v[1]>now||now-v[1]>3)return null;
            return v;
        }catch(Throwable unavailable){return null;}
    }
    private static void log(String event) {
        if(logLines++>=128)return;
        try{FileOutputStream out=new FileOutputStream(ROOT.concat("/cw-navigation-priority.log"),true);
            try{out.write(event.concat("\n").getBytes("US-ASCII"));}finally{out.close();}
        }catch(Throwable unavailable) { }
    }
}
