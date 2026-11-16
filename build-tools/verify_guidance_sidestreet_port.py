"""Compare the adapted sidestreet helper with the pinned, unmodified reference."""
import argparse,subprocess,tempfile
from pathlib import Path
REV='21f501611b0b28dbdeb2849e8443ce90ec9517ff'
ROOT=Path(__file__).resolve().parents[1]
HARNESS='''package com.luka.carplay.rgd;
import java.lang.reflect.Method;import java.util.Arrays;
public final class SideStreetOracle {
 public static void main(String[] args)throws Exception{
  Class<?> p=Class.forName("de.audi.tghu.navi.app.cluster.PorscheRouteGuidanceSideStreets");
  Method port=p.getDeclaredMethod("calcSideStreetsBytes",int.class,int.class,int.class,int[].class,int.class);port.setAccessible(true);
  int[][] lists={null,{}, {-90,0,90},{180,135,90,45,0,-45,-90,-135,-180},{1000,-1000,-1,0,45},{135,90,45,-45,-90,-135},{0,0,-90,90}};
  int[] exits={-180,-135,-90,-45,-1,0,1,45,90,135,180,1000,-1000};int checks=0;
  for(int type=0;type<54;type++)for(int j=0;j<3;j++)for(int side=0;side<2;side++)for(int angle:exits)for(int[] list:lists){
   byte[] expected=SideStreets.calcSideStreetsBytes(type,j,side,list,angle);
   byte[] actual=(byte[])port.invoke(null,type,j,side,list,angle);
   if(!Arrays.equals(expected,actual))throw new AssertionError("sidestreet mismatch "+type+"/"+j+"/"+side+"/"+angle);
   checks++;
  }
  System.out.println("PORSCHE_SIDESTREET_REFERENCE_PASS "+checks+" cases");
 }
}'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',type=Path);p.add_argument('--jdk',type=Path,required=True);a=p.parse_args()
 def tool(n):
  t=a.jdk/n;return str(t if t.exists() else t.with_suffix('.exe'))
 with tempfile.TemporaryDirectory() as tmp:
  out=Path(tmp)
  for name in ['SideStreets','ManeuverMapper']:
   data=subprocess.check_output(['git','-C',str(a.reference),'show',REV+':java_patch/com/luka/carplay/rgd/'+name+'.java'])
   (out/(name+'.java')).write_bytes(data)
  (out/'SideStreetOracle.java').write_text(HARNESS)
  subprocess.run([tool('javac'),'--release','8','-d',str(out),str(out/'SideStreets.java'),str(out/'ManeuverMapper.java'),str(out/'SideStreetOracle.java'),str(ROOT/'java/de/audi/tghu/navi/app/cluster/PorscheRouteGuidanceSideStreets.java')],check=True)
  subprocess.run([tool('java'),'-cp',str(out),'com.luka.carplay.rgd.SideStreetOracle'],check=True)
if __name__=='__main__':main()
