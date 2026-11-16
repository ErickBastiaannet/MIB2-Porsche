package de.audi.tghu.navi.app.cluster;
import java.lang.reflect.*;
public final class GuidanceNativeFixture {
 public static void main(String[] args)throws Exception{
  System.setProperty("connectwow.carplay.guidanceFile",args[0]);
  System.setProperty("connectwow.carplay.guidanceStateMaxAgeSeconds","30");
  Method read=PorscheRouteGuidance.class.getDeclaredMethod("read");read.setAccessible(true);Object state=read.invoke(null);
  Field lf=PorscheRouteGuidance.class.getDeclaredField("listener");lf.setAccessible(true);CombiBAPListener listener=new CombiBAPListener();lf.set(null,listener);
  Method update=PorscheRouteGuidance.class.getDeclaredMethod("update",state.getClass());update.setAccessible(true);update.invoke(null,state);
  if(!listener.rgActive||listener.emittedDistance!=20||listener.sideStreets.length==0
    ||!"Pandelaar".equals(listener.currentStreet)||!"Vondellaan".equals(listener.turnInfo[0].getTurnToInfo())
    ||!"Centrum".equals(listener.turnInfo[0].getSignPost())||!"Uden".equals(listener.destinationInfo.getDestination().getCity()))
    throw new AssertionError("native record did not reach original OEM guidance outputs");
  System.out.println("PORSCHE_NATIVE_JAVA_PROCESSING_PASS actual native CWRG5 to OEM descriptor/street/signpost/destination");
 }
}
