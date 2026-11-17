"""Build the separate opt-in priority candidate; no upload or installation."""
import argparse,hashlib,json,os,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'zoom':'59842f9e68060680a93dcbb2eba6dbeb184dfd1295a626782b832c9905bcf542','guidance':'a24db7e9851b736bc4a3def7081de8219ab4f6e9f15a23c6ed644e1b5d30bf52','dispatcher':'b2857648820390ddd238f1ce1e550b62203cff834aaa08375b561b588e144063'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--dispatcher-jar',type=Path,required=True);a=p.parse_args()
 zoom=ROOT/'build/PorscheCarPlayZoomLogo.probe.jar';guidance=ROOT/'build/PorscheCarPlayGuidance.experimental.jar'
 for name,path in [('zoom',zoom),('guidance',guidance)]:
  if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED[name]:raise SystemExit('Unknown source '+name)
 with zipfile.ZipFile(a.dispatcher_jar) as z:
  if hashlib.sha256(z.read('de/audi/tghu/navi/app/dsi/DSINavigationDispatcher.class')).hexdigest()!=EXPECTED['dispatcher']:raise SystemExit('Unknown original dispatcher')
 out=ROOT/'build/navigation-priority';out.mkdir(exist_ok=True)
 exports=[v for pkg in ['asm','asm.tree','asm.tree.analysis'] for v in ['--add-exports','java.base/jdk.internal.org.objectweb.'+pkg+'=ALL-UNNAMED']]
 def run(tool,*args):
  exe=a.jdk/tool
  if not exe.exists():exe=a.jdk/(tool+'.exe')
  subprocess.run([str(exe),*map(str,args)],check=True)
 with tempfile.TemporaryDirectory() as tmp:
  t=Path(tmp);classes=t/'classes';classes.mkdir();tools=t/'tools';tools.mkdir()
  stub=t/'PorscheRouteGuidance.java';stub.write_text('package de.audi.tghu.navi.app.cluster; public final class PorscheRouteGuidance { public static void cwPreempt(){} public static void cwReset(){} }')
  controls=t/'PorscheClusterControls.java';controls.write_text('package org.connectwow.carplay; public final class PorscheClusterControls { public static void cwDiscard(){} }')
  sources=list((ROOT/'optional/navigation-priority').rglob('*.java'))
  run('javac','--release','8','-d',classes,stub,controls,ROOT/'tests/RuntimeLinkProbe.java',*sources)
  run('javac',*exports,'-d',tools,ROOT/'build-tools/BuildNavigationPriority.java')
  target=out/'PorscheNavigationPriority.test.jar'
  run('java',*exports,'-cp',tools,'BuildNavigationPriority',zoom,guidance,a.dispatcher_jar,classes,target)
  manifest={'artifact_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'baseline':EXPECTED,'opt_in':'-Dconnectwow.carplay.navigationPriority=porsche-first','physical_verified':False,'installed':False,'native_required':True}
  (out/'java-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  print('PRIORITY_JAVA_CANDIDATE',manifest['artifact_sha256'])
if __name__=='__main__':main()
