package de.audi.tghu.navi.app.cluster;

import java.io.*;
import java.util.StringTokenizer;
import java.util.zip.CRC32;
import de.audi.atip.interapp.combi.bap.navi.data.CombiBAPDestinationInfo;
import de.audi.atip.interapp.combi.bap.navi.data.CombiBAPNaviDestination;
import org.dsi.ifc.navigation.BapManeuverDescriptor;
import org.dsi.ifc.navigation.BapTurnToInfo;
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
    private static final String LOG_PATH = System.getProperty("connectwow.carplay.guidanceLog", "/ramdisk/cw-porsche-rgi-java.log");
    private static final Object LOCK = new Object();
    private static CombiBAPListener listener;
    private static boolean started;
    private static long appliedEpoch = -1;
    private static long lastAppliedAt;
    private static long lastValidReadAt;
    private static int lastDistance = -1;
    private static int lastMain = -1;
    private static String lastSemanticKey = "";
    private static boolean active;
    private static boolean clearPending;
    private static long lastFailureLog;

    private static int lastCursor=-1,lastRawType=-1,lastBlinkValue=100;
    private static long lastBlinkAt;
    private static boolean blinkHigh=true;
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
                lastBlinkAt=0; // Never spin on a due blink when the snapshot is unreadable.
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
            long delay=250L;
            if(lastBlinkAt>0)delay=Math.min(delay,Math.max(1L,lastBlinkAt+600L-System.currentTimeMillis()));
            try { Thread.sleep(delay); }
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
        boolean detailed = version.equals("CWRG5");
        boolean lifecycle = version.equals("CWRG4") || detailed;
        boolean phased = version.equals("CWRG3") || lifecycle;
        boolean extended = version.equals("CWRG2") || phased;
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
        state.distanceValid = state.distance > 0;
        if (phased) {
            state.rawType = bounded(fields.nextToken(), -1, 53);
            state.stepDistance = boundedLong(fields.nextToken(), 0L, 4294967295L);
            state.distanceValid = bounded(fields.nextToken(), 0, 1) == 1;
            state.cursor = bounded(fields.nextToken(), -1, 65535);
        }
        if(lifecycle){
            state.routeState=bounded(fields.nextToken(),0,6);
            state.endReason=bounded(fields.nextToken(),0,3);
        }
        if(detailed){
            state.eta=boundedLong(fields.nextToken(),0L,4102444800L);
            state.etaValid=bounded(fields.nextToken(),0,1)==1;
            state.maneuverState=bounded(fields.nextToken(),0,255);
            state.countKnown=bounded(fields.nextToken(),0,1)==1;
            state.maneuverCount=bounded(fields.nextToken(),0,65535);
            state.zeroPending=bounded(fields.nextToken(),0,1)==1;
            state.stopDeadline=boundedLong(fields.nextToken(),0L,Long.MAX_VALUE);
            state.arrivalDeadline=boundedLong(fields.nextToken(),0L,Long.MAX_VALUE);
            state.junction=bounded(fields.nextToken(),0,255);
            state.driving=bounded(fields.nextToken(),0,255);
            state.exitAngle=bounded(fields.nextToken(),-32768,32767);
            state.remainingAt=boundedLong(fields.nextToken(),0L,4102444800L);
            String geometry=fields.nextToken();
            if(!geometry.equals("-")){
                if(geometry.length()>64||geometry.length()%4!=0)throw new IOException("invalid junction angles");
                state.junctionAngles=new int[geometry.length()/4];
                try {for(int i=0;i<state.junctionAngles.length;i++)state.junctionAngles[i]=(short)Integer.parseInt(geometry.substring(i*4,i*4+4),16);}
                catch(NumberFormatException invalid){throw new IOException("invalid junction angle");}
            }
        }
        if (fields.countTokens() != lanes + (extended ? 3 : 2) + (detailed ? 2 : 0)) throw new IOException("invalid guidance field count");
        state.lanes = new NavLaneGuidanceData[lanes];
        StringBuffer laneSignature = new StringBuffer();
        for (int i = 0; i < lanes; ++i) {
            String laneToken = fields.nextToken();
            if (i != 0) laneSignature.append('|');
            laneSignature.append(laneToken);
            state.lanes[i] = lane(laneToken, i);
        }
        int emitted=0;
        for(int i=0;i<state.lanes.length;i++)if(state.lanes[i]!=null)emitted++;
        if(emitted!=state.lanes.length){
            NavLaneGuidanceData[] compact=new NavLaneGuidanceData[emitted];int at=0;
            for(int i=0;i<state.lanes.length;i++)if(state.lanes[i]!=null)compact[at++]=state.lanes[i];
            state.lanes=compact;
        }
        state.laneSignature = laneSignature.toString();
        state.currentRoad = text(fields.nextToken());
        state.turnTo = text(fields.nextToken());
        state.destination = extended ? text(fields.nextToken()) : "";
        if(detailed){state.nextRoad=text(fields.nextToken());state.signPost=text(fields.nextToken());}
        long clock=System.currentTimeMillis();
        if((state.zeroPending&&state.stopDeadline>0&&clock>=state.stopDeadline)
                || (state.arrivalDeadline>0&&clock>=state.arrivalDeadline))state.active=false;
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
        return lane(token, 0);
    }

    private static int laneDirection(int angle) {
        if(angle < -180 || angle > 180)return 255;
        int[] keys={-180,-135,-90,-45,0,45,90,135,180};
        int[] codes={0x72,0x60,0x40,0x20,0,0xe0,0xc0,0xa0,0x92};
        int selected=0,difference=Integer.MAX_VALUE;
        for(int i=0;i<keys.length;i++){
            int d=Math.abs(angle-keys[i]);
            if(d<difference){difference=d;selected=i;}
        }
        return codes[selected];
    }

    private static NavLaneGuidanceData lane(String token,int ordinal) throws IOException {
        String angles="";
        int split=token.indexOf(';');
        if(split>=0){angles=token.substring(split+1);token=token.substring(0,split);}
        if(angles.length()>64 || angles.length()%4!=0)throw new IOException("invalid lane angles");
        StringTokenizer values = new StringTokenizer(token, ",", true);
        int[] parsed = new int[7]; int index = 0; boolean expectValue = true;
        while (values.hasMoreTokens()) {
            String value = values.nextToken();
            if (value.equals(",")) { if (expectValue) throw new IOException("empty lane value"); expectValue = true; }
            else {
                if (!expectValue || index == parsed.length) throw new IOException("invalid lane value");
                // Restore signed iAP2 degrees before mapping to BAP codes;
                // -45 degrees is wire 65491, but BAP direction is 0x20.
                parsed[index] = bounded(value, 0, index <= 1 ? 65535 : 255);
                ++index;
                expectValue = false;
            }
        }
        if (index != parsed.length || expectValue) throw new IOException("incomplete lane value");
        int primary=laneDirection((short)parsed[1]);
        int[] branches=new int[angles.length()/4];int branchCount=0;
        for(int i=0;i<angles.length();i+=4){
            int raw;
            try { raw=Integer.parseInt(angles.substring(i,i+4),16); }
            catch(NumberFormatException invalid){throw new IOException("invalid lane angle");}
            int direction=laneDirection((short)raw);
            if(direction==255)continue;
            if(primary==255)primary=direction;
            if(direction==primary)continue;
            boolean duplicate=false;
            for(int j=0;j<branchCount;j++)if(branches[j]==direction)duplicate=true;
            if(!duplicate)branches[branchCount++]=direction;
        }
        if(primary==255)return null;
        for(int i=1;i<branchCount;i++){
            int value=branches[i],j=i-1;
            while(j>=0&&branches[j]>value){branches[j+1]=branches[j];j--;}
            branches[j+1]=value;
        }
        byte[] sideStreets=new byte[branchCount];
        for(int i=0;i<branchCount;i++)sideStreets[i]=(byte)branches[i];
        int recommendation=laneDirection((short)parsed[1])==255 || parsed[6]>2 ? 0 : parsed[6];
        return new NavLaneGuidanceData((short)(parsed[0]<=32767?parsed[0]:ordinal), (short)primary, sideStreets,
            (short)0, (byte)0, (byte)0, (byte)0, (byte)recommendation);
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
            if (active || clearPending) clear(target);
            appliedEpoch = state.epoch;
            return;
        }
        Presentation presentation = presentation(state);
        String semanticKey = semanticKey(state).concat(presentation.key());
        boolean semanticChanged = !semanticKey.equals(lastSemanticKey);
        boolean sameManeuver=state.cursor>=0&&state.cursor==lastCursor&&state.rawType==lastRawType;
        if(!sameManeuver){lastBlinkAt=0;blinkHigh=true;lastBlinkValue=100;}
        boolean blink=presentation.bargraphOn&&presentation.bargraph<20;
        boolean blinkDue=blink&&(lastBlinkAt==0||now-lastBlinkAt>=600L);
        long elapsed = now - lastAppliedAt;
        if (!semanticChanged && !blinkDue && elapsed < HEARTBEAT_MILLIS) {
            int delta = lastDistance < 0 ? Integer.MAX_VALUE : Math.abs(state.distance - lastDistance);
            if (state.epoch == appliedEpoch || elapsed < updateInterval(state.distance)
                    || delta < updateThreshold(state.distance)) return;
        }
        target.setGALState(true);
        target.setViewMode(1);
        target.setRgActive(true);
        int progress=blink?(blinkDue?(blinkHigh?100:0):lastBlinkValue):presentation.bargraph;
        target.setDistanceToNextManeuver(presentation.distance,
            presentation.bargraphOn, progress);
        target.setManeuverDescriptor(new BapManeuverDescriptor[]{
            new BapManeuverDescriptor(presentation.main, presentation.direction, state.z,
                presentation.main==0||presentation.main==1||presentation.main==3||presentation.main==11 ? new byte[0] :
                PorscheRouteGuidanceSideStreets.calcSideStreetsBytes(state.rawType,state.junction,state.driving,state.junctionAngles,state.exitAngle))
        });
        target.updateBapManeuverState(presentation.phase);
        // Match reference BAPBridge.laneGuidanceVisible: cache presence alone
        // is not iOS's display intent. Unknown visibility must stay hidden.
        boolean showLanes = state.laneVisibility == 2 && state.lanes.length != 0 && !(state.countKnown && state.maneuverCount==0 && state.routeState==0);
        target.setLaneGuidance(showLanes ? state.lanes : new NavLaneGuidanceData[0], showLanes);
        // MU1417 exposes this exact package-private BAP path. The cluster's
        // position line retains the actual road currently being driven.
        // Destination and next-road labels must not overwrite this field.
        if (state.currentRoad.length() != 0) target.setCurrentStreet(state.currentRoad);
        // Reference BAPBridge FctID 46: full iOS destination label, UTF-8
        // limited to 50 bytes, in the same seven-string OEM constructor slot.
        // Do not route it through CurrentPositionInfo/currentStreet.
        target.setDestinationInfo(destinationInfo(state.destination));
        target.setTurnToInfo(new BapTurnToInfo[]{new BapTurnToInfo(
            limitDestination(nextRoadText(state.nextRoad.length()>0?state.nextRoad:state.turnTo)),limitDestination(normalizeRouteText(state.signPost)))});
        target.setRgDistanceToNextDestination(state.distanceRemaining, state.distanceRemaining > 0);
        long arrival=arrivalTime(target,state);
        target.setRgTimeToNextDestination(arrival, true, arrival>0);
        active = true;
        appliedEpoch = state.epoch;
        lastAppliedAt = now;
        lastDistance = presentation.distance;
        lastCursor = state.cursor;
        lastRawType = state.rawType;
        if(blinkDue){lastBlinkValue=progress;blinkHigh=!blinkHigh;lastBlinkAt=now;}
        else if(!blink){lastBlinkAt=0;blinkHigh=true;lastBlinkValue=100;}
        lastMain = state.main;
        lastSemanticKey = semanticKey;
        StringBuffer trace = new StringBuffer("apply epoch=");
        trace.append(state.epoch).append(" maneuver=").append(state.main).append('/').append(state.direction)
             .append(" next_m=").append(state.distance).append(" remaining_m=").append(state.distanceRemaining)
             .append(" remaining_s=").append(state.timeRemaining).append(" lanes=").append(state.lanes.length)
             .append(" cursor=").append(state.cursor).append(" phase=").append(presentation.phase);
        log(trace.toString());
    }

    private static void clearIfNeeded() {
        CombiBAPListener target;
        synchronized (LOCK) { target = listener; }
        if (target != null && (active || clearPending)) clear(target);
    }

    private static void clear(CombiBAPListener target) {
        boolean failed=false;
        // One failed OEM field must neither prevent the remaining clears nor
        // make us forget to retry on the next inactive snapshot/poll.
        try { target.setLaneGuidance(new NavLaneGuidanceData[0], false); } catch(Throwable t){failed=true;}
        try { target.setManeuverDescriptor(new BapManeuverDescriptor[0]); } catch(Throwable t){failed=true;}
        try { target.setDistanceToNextManeuver(0, false, 0); } catch(Throwable t){failed=true;}
        try { target.setTurnToInfo(new BapTurnToInfo[0]); } catch(Throwable t){failed=true;}
        try { target.setDestinationInfo(destinationInfo("")); } catch(Throwable t){failed=true;}
        try { target.setRgDistanceToNextDestination(0, false); } catch(Throwable t){failed=true;}
        try { target.setRgTimeToNextDestination(0L, false, false); } catch(Throwable t){failed=true;}
        try { target.setGALState(false); } catch(Throwable t){failed=true;}
        try { target.setRgActive(false); } catch(Throwable t){failed=true;}
        try { target.updateBapManeuverState(0); } catch(Throwable t){failed=true;}
        clearPending=failed;
        active = false;
        lastAppliedAt = 0L;
        lastDistance = -1;
        lastCursor = lastRawType = -1;
        lastBlinkAt=0;blinkHigh=true;lastBlinkValue=100;
        lastMain = -1;
        lastSemanticKey = "";
        log(failed ? "clear pending retry" : "clear complete");
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
        key.append(':').append(state.cursor).append(':').append(state.distanceValid)
           .append(':').append(state.rawType).append(':').append(state.stepDistance)
           .append(':').append(state.routeState).append(':').append(state.endReason)
           .append(':').append(state.nextRoad).append(':').append(state.signPost)
           .append(':').append(state.eta).append(':').append(state.etaValid)
           .append(':').append(state.junction).append(':').append(state.driving).append(':').append(state.exitAngle);
        for(int i=0;i<state.junctionAngles.length;i++)key.append(':').append(state.junctionAngles[i]);
        return key.toString();
    }

    private static final class State {
        long epoch, timestamp;
        boolean active;
        int distance, distanceRemaining, bargraph, main, direction, z, laneVisibility;
        long timeRemaining;
        NavLaneGuidanceData[] lanes;
        String currentRoad, turnTo, destination, laneSignature;
        int rawType = -1, cursor = -1;
        int routeState,endReason;
        long stepDistance;
        boolean distanceValid;
        long eta,remainingAt,stopDeadline,arrivalDeadline;
        boolean etaValid,countKnown,zeroPending;
        int maneuverState,maneuverCount,junction,driving,exitAngle=1000;
        int[] junctionAngles=new int[0];
        String nextRoad="",signPost="";
    }

    /** Reference BAPBridge prepare/action policy, with Porsche's verified
     * updateBapManeuverState entry point. No elapsed-time advancement. */
    private static String normalizeRouteText(String value) {
        if(value==null)return "";
        StringBuffer out=new StringBuffer(value.length());boolean pending=false;
        for(int i=0;i<value.length();i++){
            char c=value.charAt(i);
            if(c<0x20||Character.isWhitespace(c)){if(out.length()>0)pending=true;}
            else {if(pending){out.append(' ');pending=false;}out.append(c);}
        }
        return out.toString();
    }
    private static String nextRoadText(String value) {
        String text=normalizeRouteText(value);int colon=text.lastIndexOf(':');
        return colon>=0&&colon+1<text.length()?text.substring(colon+1).trim():text;
    }

    private static long arrivalTime(CombiBAPListener target,State s) {
        if(s.routeState==2)return 0L;
        try {
            long utc=System.currentTimeMillis();
            de.audi.atip.base.IFrameworkAccess fw=target.env==null?null:target.env.getFramework();
            if(fw!=null)utc=fw.getUTCTime();
            long arrival;
            if(s.etaValid&&s.eta>0)arrival=s.eta*1000L;
            else if(s.timeRemaining>0){
                long elapsed=s.remainingAt>0?Math.max(0L,System.currentTimeMillis()/1000L-s.remainingAt):0L;
                arrival=utc+Math.max(0L,s.timeRemaining-elapsed)*1000L;
            }else return 0L;
            // Reference HuTime uses the HU conversion, not a hard-coded zone.
            return fw==null?arrival:fw.convertUTCTimeToLocalTime(arrival);
        }catch(Throwable unavailable){return 0L;}
    }

    private static CombiBAPDestinationInfo destinationInfo(String value) {
        return new CombiBAPDestinationInfo(
            new CombiBAPNaviDestination("", "", limitDestination(value), "", "", "", ""));
    }

    // Reference BAPBridge.limitUtf8, including surrogate-pair boundary guard.
    private static String limitDestination(String value) {
        if (value == null) return "";
        try {
            if (value.getBytes("UTF-8").length <= 50) return value;
            int lo = 0, hi = value.length();
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                if (value.substring(0, mid).getBytes("UTF-8").length <= 50) lo = mid;
                else hi = mid - 1;
            }
            if (lo > 0 && lo < value.length()
                    && value.charAt(lo-1) >= '\uD800' && value.charAt(lo-1) <= '\uDBFF'
                    && value.charAt(lo) >= '\uDC00' && value.charAt(lo) <= '\uDFFF') lo--;
            return value.substring(0, lo);
        } catch (UnsupportedEncodingException unavailable) {
            return ""; // Never publish unbounded or guessed-encoding text.
        }
    }

    private static Presentation presentation(State s) {
        Presentation p = new Presentation();
        p.main=s.main; p.direction=s.direction;
        int distance=s.distance;
        boolean distanceValid=s.distanceValid;
        // Reference transientNoDistance/replayDistanceToManeuver: never borrow
        // a distance across a changed cursor/type or an explicit empty route.
        if(distance==0&&s.active&&s.routeState!=2&&s.cursor>=0
                &&s.cursor==lastCursor&&s.rawType==lastRawType&&lastDistance>0
                &&(!s.countKnown||s.maneuverCount>0)){
            distance=lastDistance;distanceValid=true;
        }
        p.distance=distanceValid?distance:0;
        if (!s.active) { p.main=0; return p; }
        if (s.main==0 || s.main==1 || s.main==11) {
            p.main=11; p.direction=0; p.phase=1; return p;
        }
        boolean highway=s.stepDistance>0 ? s.stepDistance>2000L
            : s.rawType==8 || s.rawType==9 || s.rawType==22 || s.rawType==23
                || s.rawType==51 || s.rawType==52 || s.rawType==53;
        int prepare=highway ? 3000 : 1500;
        int action=prepare*15/100;
        if (s.stepDistance>0 && s.stepDistance<action) action=(int)s.stepDistance;
        boolean arrival=s.main==3;
        // Fifthbro parseAndApply: an arrival maneuver can be prefetched far
        // ahead. A reached notification requires RS=2 or the final 70m.
        if(arrival && s.routeState!=2 && (!distanceValid || distance>70)) {
            p.main=11;p.direction=0;p.phase=1;return p;
        }
        boolean approach=arrival || (distanceValid && distance>0 && distance<=prepare);
        // Reference offers Next and Straight modes for distant instructions.
        // Preserve its default Next. Straight can be selected without changing
        // route data; do not impose an invented 900 m hide threshold.
        boolean farStraight="true".equals(System.getProperty("connectwow.carplay.guidanceFarStraight", "false"));
        if (farStraight && !approach) {
            p.main=11;p.direction=0;p.phase=1;return p;
        }
        p.bargraphOn=distanceValid && distance>0 && distance<=action;
        p.bargraph=p.bargraphOn ? Math.min(100,distance*100/action) : 0;
        p.phase=p.bargraphOn ? 4 : 2;
        return p;
    }

    private static final class Presentation {
        int main,direction,phase,bargraph,distance;
        boolean bargraphOn;
        String key() {
            StringBuffer k=new StringBuffer();
            k.append(':').append(main).append(':').append(direction).append(':').append(phase);
            return k.toString();
        }
    }
}
