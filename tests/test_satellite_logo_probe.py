"""Host behavior/compatibility tests for the isolated, opt-in logo probe."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_carplay_logo_lifecycle(tmp_path):
 jdk=Path(os.environ.get('JAVA_HOME',''))/'bin'
 def tool(name):
  for p in [jdk/name,jdk/(name+'.exe')]:
   if p.is_file():return str(p)
  import shutil
  p=shutil.which(name)
  if p:return p
  import pytest
  pytest.skip('JDK required')
 sources={
 'de/audi/atip/interapp/combi/bap/navi/CombiBAPServiceNavi.java':'package de.audi.atip.interapp.combi.bap.navi; public interface CombiBAPServiceNavi { void updateMapView(int a,int b); }',
 'org/connectwow/carplay/PorscheCluster.java':'package org.connectwow.carplay; public final class PorscheCluster { public static boolean carPlayReady(){return false;} }',
 'de/audi/tghu/navi/app/cluster/SatelliteLogoFixture.java':r'''package de.audi.tghu.navi.app.cluster;
import de.audi.atip.interapp.combi.bap.navi.CombiBAPServiceNavi;
public class SatelliteLogoFixture implements CombiBAPServiceNavi {
 int view,extra,calls;boolean fail;
 public void updateMapView(int a,int b){if(fail){fail=false;throw new RuntimeException("injected");}view=a;extra=b;calls++;}
 static void check(boolean ok){if(!ok)throw new AssertionError();}
 public static void main(String[] args)throws Exception {
  SatelliteLogoFixture t=new SatelliteLogoFixture();
  java.lang.reflect.Field f=PorscheSatelliteLogo.class.getDeclaredField("started");f.setAccessible(true);f.setBoolean(null,true);
  PorscheSatelliteLogo.send(t,1,7);check(t.view==1&&t.extra==7);
  PorscheSatelliteLogo.refresh(true);check(t.view==1); // opt-in required
  System.setProperty("connectwow.carplay.satelliteLogo","hide-during-carplay");
  PorscheSatelliteLogo.refresh(true);check(t.view==0&&t.extra==7);
  int n=t.calls;PorscheSatelliteLogo.refresh(true);check(t.calls==n);
  PorscheSatelliteLogo.send(t,1,9);check(t.view==0&&t.extra==9); // OEM refresh remains suppressed
  PorscheSatelliteLogo.refresh(false);check(t.view==1&&t.extra==9); // lost lease restores OEM
  PorscheSatelliteLogo.refresh(true);check(t.view==0);
  PorscheSatelliteLogo.send(t,2,8);check(t.view==2); // non-satellite untouched
  PorscheSatelliteLogo.send(t,0,3);PorscheSatelliteLogo.refresh(false);check(t.view==0&&t.extra==3);
  PorscheSatelliteLogo.send(t,1,4);t.fail=true;
  try{PorscheSatelliteLogo.refresh(true);throw new AssertionError();}catch(RuntimeException expected){}
  PorscheSatelliteLogo.refresh(true);check(t.view==0&&t.extra==4); // failed transition retried
  System.clearProperty("connectwow.carplay.satelliteLogo");PorscheSatelliteLogo.refresh(true);check(t.view==1);
  PorscheSatelliteLogo.send(t,2,11);PorscheSatelliteLogo.refresh(false);check(t.view==2&&t.extra==11);
  System.out.println("SATELLITE_LOGO_LIFECYCLE_PASS opt-in, valid-video suppression, OEM updates, restore, supplementary, failure retry");
 }
}'''
 }
 paths=[]
 for name,body in sources.items():
  p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);paths.append(str(p))
 helper=ROOT/'optional/satellite-logo/de/audi/tghu/navi/app/cluster/PorscheSatelliteLogo.java'
 subprocess.run([tool('javac'),'--release','8','-d',str(tmp_path),*paths,str(helper)],check=True)
 r=subprocess.run([tool('java'),'-cp',str(tmp_path),'de.audi.tghu.navi.app.cluster.SatelliteLogoFixture'],capture_output=True,text=True,check=True)
 assert 'SATELLITE_LOGO_LIFECYCLE_PASS' in r.stdout
