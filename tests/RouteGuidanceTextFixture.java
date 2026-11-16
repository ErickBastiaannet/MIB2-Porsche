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

    private static void set(Object state,String name,Object value) throws Exception {
        Field field=state.getClass().getDeclaredField(name);field.setAccessible(true);field.set(state,value);
    }

    private static void checkPhase(Object state,int expected,int expectedMain,boolean bargraph) throws Exception {
        Method method=PorscheRouteGuidance.class.getDeclaredMethod("presentation",state.getClass());method.setAccessible(true);
        Object p=method.invoke(null,state);
        Field phase=p.getClass().getDeclaredField("phase"),main=p.getClass().getDeclaredField("main"),bar=p.getClass().getDeclaredField("bargraphOn");
        phase.setAccessible(true);main.setAccessible(true);bar.setAccessible(true);
        if(phase.getInt(p)!=expected||main.getInt(p)!=expectedMain||bar.getBoolean(p)!=bargraph)
            throw new AssertionError("reference presentation phase/main/bargraph mismatch");
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
        Method laneParser = PorscheRouteGuidance.class.getDeclaredMethod("lane", String.class);
        laneParser.setAccessible(true);
        org.dsi.ifc.navigation.NavLaneGuidanceData left=(org.dsi.ifc.navigation.NavLaneGuidanceData)laneParser.invoke(null, "0,65491,0,1,1,0,2;ffd30000002d");
        if(left.laneDirection!=0x20||left.guidanceInfo!=2||left.laneSideStreets.length!=2
                ||(left.laneSideStreets[0]&255)!=0||(left.laneSideStreets[1]&255)!=0xe0)
            throw new AssertionError("lane degrees were not mapped to reference BAP codes");
        org.dsi.ifc.navigation.NavLaneGuidanceData fallback=(org.dsi.ifc.navigation.NavLaneGuidanceData)laneParser.invoke(null, "0,1000,0,0,0,0,2;ffd3");
        if(fallback.laneDirection!=0x20||fallback.guidanceInfo!=0)
            throw new AssertionError("unknown lane primary acquired a recommendation");
        if(laneParser.invoke(null, "0,1000,0,0,0,0,2;")!=null)
            throw new AssertionError("lane without geometry was invented");
        laneParser.invoke(null, "2,45,0,1,1,0,0");
        Field current = state.getClass().getDeclaredField("currentRoad");
        Field turn = state.getClass().getDeclaredField("turnTo");
        current.setAccessible(true); turn.setAccessible(true);
        if (!"Nieuwe Erpseweg".equals(current.get(state)) || !"N279".equals(turn.get(state)))
            throw new AssertionError("street fields did not survive CWRG1 transport");

        Field listenerField = PorscheRouteGuidance.class.getDeclaredField("listener");
        Field appliedAt = PorscheRouteGuidance.class.getDeclaredField("lastAppliedAt");
        listenerField.setAccessible(true); appliedAt.setAccessible(true);
        CombiBAPListener listener = new CombiBAPListener();
        listener.env=new de.audi.tghu.navi.app.NavigationEnv(new de.audi.atip.base.IFrameworkAccess(){
            public long getUTCTime(){return 1700000000000L;}
            public long convertUTCTimeToLocalTime(long value){return value+3600000L;}
        });
        listenerField.set(null, listener);
        Method update = PorscheRouteGuidance.class.getDeclaredMethod("update", state.getClass());
        update.setAccessible(true);
        update.invoke(null, state);
        if (!listener.rgActive || listener.viewMode != 1)
            throw new AssertionError("Porsche route guidance status/type were not activated");
        if (!"Nieuwe Erpseweg".equals(listener.currentStreet))
            throw new AssertionError("next road overwrote current-position street");
        if (listener.distanceCalls != 1) throw new AssertionError("first guidance update missing");
        if (listener.destinationDistance != 12345 || listener.destinationTime != 1700007200 || !listener.destinationEta)
            throw new AssertionError("destination distance/time missing");
        if (!"Uden".equals(listener.destinationInfo.getDestination().getCity()))
            throw new AssertionError("reference DestinationInfo FctID 46 missing");
        if (!"Nieuwe Erpseweg".equals(listener.currentStreet))
            throw new AssertionError("destination overwrote current position");
        update.invoke(null, state);
        if (listener.distanceCalls != 1) throw new AssertionError("guidance update was not rate limited");
        appliedAt.setLong(null, System.currentTimeMillis() - 2100L);
        update.invoke(null, state);
        if (listener.distanceCalls != 2) throw new AssertionError("guidance heartbeat missing");
        Field lanes = state.getClass().getDeclaredField("lanes");
        Field visibility = state.getClass().getDeclaredField("laneVisibility");
        lanes.setAccessible(true); visibility.setAccessible(true);
        lanes.set(state, new org.dsi.ifc.navigation.NavLaneGuidanceData[]{
            (org.dsi.ifc.navigation.NavLaneGuidanceData)laneParser.invoke(null, "0,65491,0,1,1,0,2")
        });
        for (int value = 0; value <= 2; value++) {
            visibility.setInt(state, value);
            appliedAt.setLong(null, System.currentTimeMillis() - 2100L);
            update.invoke(null, state);
            if (listener.lanesShown != (value == 2))
                throw new AssertionError("cached lanes displayed without explicit iOS intent");
        }
        set(state,"rawType",Integer.valueOf(2));set(state,"stepDistance",Long.valueOf(1000));
        set(state,"distanceValid",Boolean.TRUE);set(state,"distance",Integer.valueOf(900));
        checkPhase(state,2,13,false); // 900m is Prepare, not Action.
        set(state,"distance",Integer.valueOf(225));checkPhase(state,4,13,true);
        set(state,"distance",Integer.valueOf(226));checkPhase(state,2,13,false);
        set(state,"distance",Integer.valueOf(2000));checkPhase(state,2,13,false);
        System.setProperty("connectwow.carplay.guidanceFarStraight","true");
        checkPhase(state,1,11,false);
        System.clearProperty("connectwow.carplay.guidanceFarStraight");
        set(state,"stepDistance",Long.valueOf(3001));set(state,"distance",Integer.valueOf(400));checkPhase(state,4,13,true);
        set(state,"distanceValid",Boolean.FALSE);checkPhase(state,2,13,false);
        set(state,"main",Integer.valueOf(11));checkPhase(state,1,11,false);
        set(state,"active",Boolean.FALSE);checkPhase(state,0,0,false);
        set(state,"active",Boolean.TRUE);set(state,"main",Integer.valueOf(3));
        set(state,"routeState",Integer.valueOf(1));set(state,"distanceValid",Boolean.TRUE);
        set(state,"distance",Integer.valueOf(900));checkPhase(state,1,11,false);
        set(state,"distance",Integer.valueOf(70));checkPhase(state,4,3,true);
        set(state,"distanceValid",Boolean.FALSE);set(state,"routeState",Integer.valueOf(2));
        set(state,"destination","Vondellaan 12, Uden");
        checkPhase(state,2,3,false);update.invoke(null,state);
        if (!"Vondellaan 12, Uden".equals(listener.destinationInfo.getDestination().getCity())
                || !"Nieuwe Erpseweg".equals(listener.currentStreet))
            throw new AssertionError("arrival lost destination or replaced current position");
        Method limit=PorscheRouteGuidance.class.getDeclaredMethod("limitDestination",String.class);
        limit.setAccessible(true);
        StringBuffer label=new StringBuffer();for(int i=0;i<49;i++)label.append('x');
        String supplementary=label.toString()+"\uD83D\uDE97";
        String limited=(String)limit.invoke(null,supplementary);
        if(limited.getBytes("UTF-8").length>50 || !limited.equals(label.toString()))
            throw new AssertionError("50-byte destination limit split Unicode scalar");
        if(!"".equals(limit.invoke(null,new Object[]{null})))throw new AssertionError("null destination");
        StringBuffer accented=new StringBuffer();for(int i=0;i<26;i++)accented.append('\u00e9');
        String bounded=(String)limit.invoke(null,accented.toString());
        if(bounded.length()!=25 || bounded.getBytes("UTF-8").length!=50)
            throw new AssertionError("reference bound must count UTF-8 bytes, not chars");
        set(state,"active",Boolean.FALSE);set(state,"routeState",Integer.valueOf(0));
        listener.failNextLaneClear=true;
        listener.failNextDestinationClear=true;
        update.invoke(null,state);
        Field clearPending=PorscheRouteGuidance.class.getDeclaredField("clearPending");clearPending.setAccessible(true);
        if(listener.rgActive||listener.maneuverPhase!=0||listener.destinationDistance!=0
                ||listener.destinationTime!=0||!clearPending.getBoolean(null))
            throw new AssertionError("one failed clear prevented other stop fields");
        update.invoke(null,state);
        if(clearPending.getBoolean(null)||listener.lanesShown
                || listener.destinationInfo.getDestination().getCity().length()!=0
                || !"Nieuwe Erpseweg".equals(listener.currentStreet))
            throw new AssertionError("failed clear was not retried");
        // New processing metadata: real current instruction, geometry, text,
        // ETA, and deadlines; no alternate transport or display path.
        String junction="005a0000ffa6";
        body="CWRG5 12 "+now+" 1 20 0 13 64 0 0 1200 600 1 1 1000 1 77 1 0 "
            +"1700010000 1 1 1 3 0 0 0 0 0 -90 "+now+" "+junction
            +" "+hex("Pandelaar")+" "+hex("Vondellaan")+" "+hex("Uden")
            +" "+hex("Vondellaan")+" "+hex("Centrum")+" ";
        crc=new CRC32();crc.update(body.getBytes(StandardCharsets.US_ASCII));
        try(FileOutputStream stream=new FileOutputStream(stateFile)){
            stream.write((body+String.format("%08x\n",crc.getValue())).getBytes(StandardCharsets.US_ASCII));
        }
        Object detailed=read.invoke(null);
        update.invoke(null,detailed);
        if(listener.sideStreets==null||listener.sideStreets.length==0)
            throw new AssertionError("junction geometry never reached existing descriptor");
        if(!"Vondellaan".equals(listener.turnInfo[0].getTurnToInfo())
                ||!"Centrum".equals(listener.turnInfo[0].getSignPost())
                ||!"Pandelaar".equals(listener.currentStreet))
            throw new AssertionError("next-road/signpost fields lost or replaced actual position");
        if(listener.destinationTime!=1700013600||!listener.destinationEta)
            throw new AssertionError("explicit ETA did not use verified HU local conversion");
        if(listener.emittedBargraph!=100)throw new AssertionError("action blink should start full");
        Method etaMethod=PorscheRouteGuidance.class.getDeclaredMethod("arrivalTime",CombiBAPListener.class,detailed.getClass());etaMethod.setAccessible(true);
        set(detailed,"routeState",Integer.valueOf(2));
        if(((Long)etaMethod.invoke(null,listener,detailed)).longValue()!=0L)
            throw new AssertionError("arrival retained an obsolete ETA counter");
        set(detailed,"routeState",Integer.valueOf(1));
        set(detailed,"etaValid",Boolean.FALSE);set(detailed,"timeRemaining",Long.valueOf(600L));
        set(detailed,"remainingAt",Long.valueOf(System.currentTimeMillis()/1000L-30L));
        long elapsedEta=((Long)etaMethod.invoke(null,listener,detailed)).longValue();
        if(elapsedEta<1700004169000L||elapsedEta>1700004170000L)
            throw new AssertionError("remaining-time snapshot age was not applied to ETA");
        set(detailed,"etaValid",Boolean.TRUE);

        Field blinkAt=PorscheRouteGuidance.class.getDeclaredField("lastBlinkAt");blinkAt.setAccessible(true);
        blinkAt.setLong(null,System.currentTimeMillis()-601L);
        update.invoke(null,detailed);
        if(listener.emittedBargraph!=0)throw new AssertionError("reference action blink did not alternate");
        set(detailed,"distance",Integer.valueOf(0));set(detailed,"distanceValid",Boolean.FALSE);
        appliedAt.setLong(null,System.currentTimeMillis()-2100L);update.invoke(null,detailed);
        if(listener.emittedDistance!=20)throw new AssertionError("same-instruction distance replay missing");
        set(detailed,"cursor",Integer.valueOf(78));update.invoke(null,detailed);
        if(listener.emittedDistance!=0)throw new AssertionError("distance leaked to next instruction");
        // Force a published stop deadline into the past: the existing read/poll
        // expires guidance even with no next native packet.
        body=body.replace(" 3 0 0 0 0 0 -90 "," 3 1 "+(System.currentTimeMillis()-1L)+" 0 0 0 -90 ");
        crc=new CRC32();crc.update(body.getBytes(StandardCharsets.US_ASCII));
        try(FileOutputStream stream=new FileOutputStream(stateFile)){
            stream.write((body+String.format("%08x\n",crc.getValue())).getBytes(StandardCharsets.US_ASCII));
        }
        Object expired=read.invoke(null);Field activeField=expired.getClass().getDeclaredField("active");activeField.setAccessible(true);
        if(activeField.getBoolean(expired))throw new AssertionError("quiet stop did not expire in existing poll");
        update.invoke(null,expired);
        // Arrival expiration is independent of additional native packets.
        body="CWRG5 13 "+now+" 1 0 0 3 0 0 0 0 0 1 12 0 0 77 2 0 "
            +"0 0 0 1 1 0 0 "+(System.currentTimeMillis()-1L)+" 0 0 1000 0 - "
            +hex("Pandelaar")+" - "+hex("Uden")+" - - ";
        crc=new CRC32();crc.update(body.getBytes(StandardCharsets.US_ASCII));
        try(FileOutputStream stream=new FileOutputStream(stateFile)){
            stream.write((body+String.format("%08x\n",crc.getValue())).getBytes(StandardCharsets.US_ASCII));
        }
        Object arrivedExpired=read.invoke(null);
        if(activeField.getBoolean(arrivedExpired))throw new AssertionError("quiet arrival hold never expired");
        Method roadText=PorscheRouteGuidance.class.getDeclaredMethod("nextRoadText",String.class);roadText.setAccessible(true);
        if(!"Vondellaan".equals(roadText.invoke(null,"A50:  Vondellaan \t")))
            throw new AssertionError("reference next-road normalization missing");
        // Native v3 adds current-maneuver metadata without changing the CRC contract.
        body="CWRG3 8 "+now+" 1 900 0 13 192 0 0 12345 3600 1 2 1000 1 720 - - - ";
        crc=new CRC32();crc.update(body.getBytes(StandardCharsets.US_ASCII));
        try(FileOutputStream stream=new FileOutputStream(stateFile)){
            stream.write((body+String.format("%08x\n",crc.getValue())).getBytes(StandardCharsets.US_ASCII));
        }
        Object v3=read.invoke(null);
        checkPhase(v3,2,13,false);
        body="CWRG4 9 "+now+" 1 0 0 3 0 0 0 0 0 1 -1 0 0 -1 2 0 - - - ";
        crc=new CRC32();crc.update(body.getBytes(StandardCharsets.US_ASCII));
        try(FileOutputStream stream=new FileOutputStream(stateFile)){
            stream.write((body+String.format("%08x\n",crc.getValue())).getBytes(StandardCharsets.US_ASCII));
        }
        Object v4=read.invoke(null);checkPhase(v4,2,3,false);
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
