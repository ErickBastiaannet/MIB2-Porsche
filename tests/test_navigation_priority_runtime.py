"""Exercise the actual runtime adapter with file leases and concurrent OEM writers."""
import os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def tool(n):
 jdk=Path(os.environ.get('JAVA_HOME',''))/'bin'
 for p in [jdk/n,jdk/(n+'.exe')]:
  if p.is_file():return str(p)
 found=shutil.which(n)
 if found:return found
 import pytest
 pytest.skip('JDK required')
def test_runtime_ordering_and_leases(tmp_path):
 src={
 'org/connectwow/carplay/PorscheClusterControls.java':'package org.connectwow.carplay; public final class PorscheClusterControls { public static int flushed; public static void cwDiscard(){flushed++;} }',
 'de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.java':r'''package de.audi.tghu.navi.app.cluster;
public final class PorscheRouteGuidance {
 public static int resets,preempted;
 public static void cwReset(){resets++;}
 public static void cwPreempt(){if(NavigationPriorityRuntime.enter(1,false)){preempted++;NavigationPriorityRuntime.leave(1,false,false);}}
}''',
 'de/audi/tghu/navi/app/cluster/PriorityRuntimeFixture.java':r'''package de.audi.tghu.navi.app.cluster;
import java.nio.file.*;import java.util.zip.CRC32;import java.util.concurrent.CountDownLatch;import java.util.concurrent.TimeUnit;
public final class PriorityRuntimeFixture {
 static Path root;static volatile Throwable failed;
 static void check(boolean v){if(!v)throw new AssertionError();}
 static void record(String path,String magic,long... values)throws Exception{
  StringBuilder b=new StringBuilder(magic).append(' ');for(long v:values)b.append(v).append(' ');
  CRC32 crc=new CRC32();crc.update(b.toString().getBytes("US-ASCII"));
  b.append(String.format("%08x",crc.getValue())).append('\n');Files.write(root.resolve(path),b.toString().getBytes("US-ASCII"));
 }
 static void video()throws Exception{
  long now=System.currentTimeMillis()/1000;
  Files.write(root.resolve("cw-porsche-altstream.ready"),("1234 "+now+"\n").getBytes("US-ASCII"));
  record("cw-carplay-ready.v1","CWRD1",1,now,800,480);record("cw-nav-priority.applied","CWNPA1",1,now,1,1234);
 }
 static void join(Thread t)throws Exception{t.join(3000);check(!t.isAlive());if(failed!=null)throw new AssertionError(failed);}
 public static void main(String[] args)throws Exception{
  root=Paths.get(System.getProperty("connectwow.carplay.priorityRoot"));Files.createDirectories(root);video();
  check(!NavigationPriorityRuntime.permitsCarPlay()); // unknown startup cannot steal display
  NavigationPriorityRuntime.beforeNative(false,1);check(!NavigationPriorityRuntime.permitsCarPlay());
  NavigationPriorityRuntime.afterNative(false);check(!NavigationPriorityRuntime.permitsCarPlay()); // real display acknowledgement still missing
  video();check(NavigationPriorityRuntime.permitsCarPlay());
  synchronized(NavigationPriorityRuntime.LOCK){check(NavigationPriorityRuntime.enter(0,true));check(NavigationPriorityRuntime.beginBap(true)==2);NavigationPriorityRuntime.leave(0,true,false);}
  check(NavigationPriorityRuntime.beginBap(true)==0); // old native route deltas cannot overwrite CarPlay
  int resets=PorscheRouteGuidance.resets;
  NavigationPriorityRuntime.beforeNative(false,1);NavigationPriorityRuntime.afterNative(false);check(PorscheRouteGuidance.resets==resets); // repeated idle no replay/reset
  NavigationPriorityRuntime.beforeNative(true,0);check(NavigationPriorityRuntime.permitsCarPlay()); // invalid DSI validity ignored
  NavigationPriorityRuntime.beforeNative(true,1);check(!NavigationPriorityRuntime.permitsCarPlay()&&PorscheRouteGuidance.preempted==1);
  synchronized(NavigationPriorityRuntime.LOCK){check(!NavigationPriorityRuntime.enter(1,false));check(!NavigationPriorityRuntime.enter(0,true));}
  NavigationPriorityRuntime.afterNative(true);int nativeTicket=NavigationPriorityRuntime.beginBap(true);check(nativeTicket==1);
  NavigationPriorityRuntime.beforeNative(false,1);NavigationPriorityRuntime.afterNative(false);video();
  CountDownLatch waiting=new CountDownLatch(1),acquired=new CountDownLatch(1),release=new CountDownLatch(1);
  Thread cp=new Thread(new Runnable(){public void run(){try{synchronized(NavigationPriorityRuntime.LOCK){waiting.countDown();check(NavigationPriorityRuntime.enter(0,true));acquired.countDown();check(release.await(2,TimeUnit.SECONDS));NavigationPriorityRuntime.leave(0,true,false);}}catch(Throwable t){failed=t;}}});cp.setDaemon(true);cp.start();check(waiting.await(2,TimeUnit.SECONDS));
  check(!acquired.await(50,TimeUnit.MILLISECONDS));NavigationPriorityRuntime.endBap(nativeTicket);check(acquired.await(2,TimeUnit.SECONDS));
  Thread nativeRoute=new Thread(new Runnable(){public void run(){try{NavigationPriorityRuntime.beforeNative(true,1);NavigationPriorityRuntime.afterNative(true);}catch(Throwable t){failed=t;}}});nativeRoute.setDaemon(true);nativeRoute.start();
  release.countDown();join(cp);join(nativeRoute);check(!NavigationPriorityRuntime.permitsCarPlay());
  check(PorscheRouteGuidance.preempted==2); // exclusive batch completed BEFORE new native publication
  NavigationPriorityRuntime.beforeNative(false,1);NavigationPriorityRuntime.afterNative(false);video();
  record("cw-nav-priority.applied","CWNPA1",1,System.currentTimeMillis()/1000,1,9999);check(!NavigationPriorityRuntime.permitsCarPlay());
  video();Files.write(root.resolve("cw-carplay-ready.v1"),"CWRD1 invalid\n".getBytes("US-ASCII"));check(!NavigationPriorityRuntime.permitsCarPlay());
  video();record("cw-carplay-ready.v1","CWRD1",1,System.currentTimeMillis()/1000-10,800,480);check(!NavigationPriorityRuntime.permitsCarPlay());
  video();NavigationPriorityRuntime.poll();check(Files.readAllBytes(root.resolve("cw-nav-priority.v1")).length<256);
  System.out.println("PRIORITY_RUNTIME_PASS OEM event ordering, pending native writer, exclusive CarPlay batch, late clear blocked, repeated idle, stale/mismatched/corrupt leases");
 }
}'''
 }
 paths=[]
 for name,body in src.items():
  p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);paths.append(p)
 sources=list((ROOT/'optional/navigation-priority').rglob('*.java'))
 subprocess.run([tool('javac'),'--release','8','-d',str(tmp_path),*map(str,paths+sources)],check=True)
 r=subprocess.run([tool('java'),'-Xverify:all','-Dconnectwow.carplay.navigationPriority=porsche-first','-Dconnectwow.carplay.priorityRoot='+str(tmp_path/'runtime'),'-cp',str(tmp_path),'de.audi.tghu.navi.app.cluster.PriorityRuntimeFixture'],capture_output=True,text=True,timeout=15,check=True)
 assert 'PRIORITY_RUNTIME_PASS' in r.stdout
