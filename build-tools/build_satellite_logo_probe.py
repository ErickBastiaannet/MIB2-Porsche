"""Build opt-in CarPlay-only satellite-logo probe from a hash-pinned zoom JAR.
No upload, startup edits, firmware modifications or permanent activation.
"""
import argparse,hashlib,json,os,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COMBI='de/audi/tghu/navi/app/cluster/CombiBAPListener.class'
HELPER='de/audi/tghu/navi/app/cluster/PorscheSatelliteLogo'
SERVICE='de/audi/atip/interapp/combi/bap/navi/CombiBAPServiceNavi'
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--zoom-jar',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--jdk',type=Path,required=True)
 a=p.parse_args();original=a.zoom_jar.read_bytes()
 if hashlib.sha256(original).hexdigest()!=a.expected_sha256:raise SystemExit('Unexpected source zoom JAR')
 exports=[v for package in ['asm','asm.tree','asm.tree.analysis'] for v in ['--add-exports','java.base/jdk.internal.org.objectweb.'+package+'=ALL-UNNAMED']]
 def run(tool,*args):
  exe=a.jdk/tool
  if not exe.exists():exe=a.jdk/(tool+'.exe')
  subprocess.run([str(exe),*map(str,args)],check=True)
 out=ROOT/'build/PorscheCarPlayZoomLogo.probe.jar'
 with zipfile.ZipFile(a.zoom_jar) as z:entries={n:z.read(n) for n in z.namelist()}
 if COMBI not in entries or any(n.startswith(HELPER) for n in entries):raise SystemExit('Unknown or already patched zoom JAR')
 with tempfile.TemporaryDirectory() as tmp:
  t=Path(tmp);classes=t/'classes';classes.mkdir();stub=t/(SERVICE+'.java');stub.parent.mkdir(parents=True)
  stub.write_text('package de.audi.atip.interapp.combi.bap.navi; public interface CombiBAPServiceNavi { void updateMapView(int view,int supplementary); }')
  run('javac','--release','8','-cp',a.zoom_jar,'-d',classes,stub,ROOT/'optional/satellite-logo'/Path(HELPER+'.java'))
  tools=t/'tools';tools.mkdir();run('javac',*exports,'-d',tools,ROOT/'build-tools/BuildSatelliteLogoProbe.java')
  source=t/'Combi.class';source.write_bytes(entries[COMBI]);patched=t/'Patched.class'
  helpers=sorted(classes.rglob('PorscheSatelliteLogo*.class'))
  if len(helpers)!=2:raise SystemExit('Unexpected helper class set')
  run('java',*exports,'-cp',tools,'BuildSatelliteLogoProbe',source,patched,*helpers)
  entries[COMBI]=patched.read_bytes()
  for f in helpers:entries[f.relative_to(classes).as_posix()]=f.read_bytes()
  out.parent.mkdir(exist_ok=True)
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   for name,data in sorted(entries.items()):
    info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));z.writestr(info,data)
 with zipfile.ZipFile(a.zoom_jar) as before,zipfile.ZipFile(out) as after:
  for name in before.namelist():
   if name!=COMBI and before.read(name)!=after.read(name):raise SystemExit('Unrelated zoom class changed')
 manifest={'source_sha256':a.expected_sha256,'probe_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'changed_oem_method':'CombiBAPListener.updateMapView()V: one outgoing interface call','activation':'-Dconnectwow.carplay.satelliteLogo=hide-during-carplay','physical_verified':False,'unit_modified':False,'warning':'MapView0 effects must be physically validated; OEM imagery and supplier attribution are unchanged'}
 out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(out,manifest['probe_sha256'])
if __name__=='__main__':main()
