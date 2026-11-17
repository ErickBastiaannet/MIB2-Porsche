"""Package the checked candidate as a one-boot trial with exact baseline/restore guards."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE_WINDOW='6e7fcdaad2aef40cf9381f6a08374b58501044d63d091ad64957921f8a426d9f'
BASE_LSD='5a7f5a087afb6699f2ba5ecb2297e2235f403db0e591164dd0749178dda2a368'
def main():
 d=ROOT/'build/navigation-priority';base=ROOT/'build/lsd-logo-confirmed.sh';window=d/'cw-window-priority';jar=d/'PorscheNavigationPriority.test.jar'
 if sha(base)!=BASE_LSD:raise SystemExit('Unknown confirmed baseline launcher')
 audit=d/'rom-link-audit.json';report=json.loads(audit.read_text())
 if report.get('jar_sha256')!=sha(jar):raise SystemExit('ROM audit does not match candidate JAR')
 for key,empty in [('missing_members',[]),('private_access_errors',[]),('unverified_references',[]),('rom_read_failures',{})]:
  if report.get(key)!=empty:raise SystemExit('Incomplete ROM audit: '+key)
 text=base.read_text();marker='# CONNECTWOW_JAVA_PROBE_V1\n'
 if text.count(marker)!=1:raise SystemExit('Unknown launcher marker')
 initial='CW_PRIORITY_ACTIVE=0\nrm -f /ramdisk/cw-nav-priority.enabled /ramdisk/cw-nav-priority.v1 /ramdisk/cw-nav-priority.applied\n'
 activation='    CW_PRIORITY_STATE=/mnt/persist/connectwow-carplay/navigation-priority\n    CW_PRIORITY_ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15\n    CW_PRIORITY_JAR=$CW_PRIORITY_ROOT/PorscheNavigationPriority.test.jar\n    CW_PRIORITY_BACKUP=$CW_PRIORITY_ROOT/before-navigation-priority-20261116\n    if { [ -s "$CW_PRIORITY_STATE/confirmed" ] || [ -s "$CW_PRIORITY_STATE/pending" ]; } && [ -s "$CW_PRIORITY_JAR" ] &&\n       [ -s /mnt/persist/connectwow-carplay/guidance-probe/confirmed ] &&\n       [ "$("$CW_PRIORITY_BACKUP/cw-window-candidate" --hash "$CW_PRIORITY_JAR")" = JARHASH ] &&\n       [ "$("$CW_PRIORITY_BACKUP/cw-window-candidate" --hash "$CW_PRIORITY_ROOT/cw-window-candidate")" = WINDOWHASH ]; then\n        if [ -s "$CW_PRIORITY_STATE/confirmed" ] || mv "$CW_PRIORITY_STATE/pending" "$CW_PRIORITY_STATE/attempted"; then\n            if echo enabled > /ramdisk/cw-nav-priority.enabled; then\n                CW_PROBE_JAR=$CW_PRIORITY_JAR\n                CW_PRIORITY_ACTIVE=1\n                VMOPTIONS="$VMOPTIONS -Dconnectwow.carplay.navigationPriority=porsche-first"\n            fi\n        fi\n    fi\n'
 activation=activation.replace('JARHASH',sha(jar)).replace('WINDOWHASH',sha(window))
 text=text.replace(marker,marker+initial)
 anchor='    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$CW_PROBE_JAR"\n'
 if text.count(anchor)!=1:raise SystemExit('Unknown zoom prefix')
 text=text.replace(anchor,activation+anchor)
 anchor='    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$CW_EXTRA_PROBE_JAR"\n'
 if text.count(anchor)!=1:raise SystemExit('Unknown guidance prefix')
 text=text.replace(anchor,'    if [ "$CW_PRIORITY_ACTIVE" -eq 0 ]; then\n'+anchor+'    fi\n')
 lsd=d/'lsd-priority-trial.sh';lsd.write_bytes(text.encode('ascii'))
 header='#!/bin/ksh\nset -e\nROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15\nLSD=/mnt/app/eso/hmi/lsd/lsd.sh\nBACKUP=$ROOT/before-navigation-priority-20261116\nSTATE=/mnt/persist/connectwow-carplay/navigation-priority\nTOOL=$ROOT/cw-window-candidate\nfunction cw_hash { "$TOOL" --hash "$1"; }\ncd "$(dirname "$0")"\n'
 install=header
 checks={'"$ROOT/cw-window-candidate"':BASE_WINDOW,'"$LSD"':BASE_LSD,'"$ROOT/cw-receiver-controls.so"':'c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847','"$ROOT/PorscheCarPlayGuidance.experimental.jar"':'a24db7e9851b736bc4a3def7081de8219ab4f6e9f15a23c6ed644e1b5d30bf52','cw-window-priority':sha(window),'PorscheNavigationPriority.test.jar':sha(jar),'lsd-priority-trial.sh':sha(lsd)}
 for name,digest in checks.items():install+='[ "$(cw_hash '+name+')" = '+digest+' ] || exit 1\n'
 install+='[ ! -e "$BACKUP" ] && [ ! -e "$ROOT/PorscheNavigationPriority.test.jar" ] && [ ! -e "$STATE/pending" ] || exit 1\n[ -s /mnt/persist/connectwow-carplay/guidance-probe/confirmed ] || exit 1\n/bin/ksh -n lsd-priority-trial.sh\n/bin/ksh "$PWD/link-check.sh"\nRW=0\nCHANGED=0\nfunction cw_cleanup {\n trap - 0\n set +e\n if [ "$CHANGED" = 1 ]; then\n  cp -p "$BACKUP/cw-window-candidate" "$ROOT/cw-window-candidate.restore" && mv -f "$ROOT/cw-window-candidate.restore" "$ROOT/cw-window-candidate"\n  cp -p "$BACKUP/lsd.sh" "$LSD.restore" && mv -f "$LSD.restore" "$LSD"\n  rm -f "$STATE/pending" "$ROOT/PorscheNavigationPriority.test.jar"\n fi\n [ "$RW" = 0 ] || mount -ur /mnt/app\n}\ntrap cw_cleanup 0\nmount -uw /mnt/app\nRW=1\nmkdir "$BACKUP"\ncp -p "$TOOL" "$BACKUP/cw-window-candidate"\ncp -p "$LSD" "$BACKUP/lsd.sh"\nTOOL=$BACKUP/cw-window-candidate\n[ "$(cw_hash "$ROOT/cw-window-candidate")" = "$(cw_hash "$TOOL")" ] || exit 1\n[ "$(cw_hash "$LSD")" = "$(cw_hash "$BACKUP/lsd.sh")" ] || exit 1\ncp cw-window-priority "$ROOT/cw-window-candidate.new"\nchmod 755 "$ROOT/cw-window-candidate.new"\ncp PorscheNavigationPriority.test.jar "$ROOT/PorscheNavigationPriority.test.jar.new"\nchmod 644 "$ROOT/PorscheNavigationPriority.test.jar.new"\ncp -p lsd-priority-trial.sh "$LSD.new"\n/bin/ksh -n "$LSD.new"\n[ "$(cw_hash cw-window-priority)" = "$(cw_hash "$ROOT/cw-window-candidate.new")" ] || exit 1\n[ "$(cw_hash PorscheNavigationPriority.test.jar)" = "$(cw_hash "$ROOT/PorscheNavigationPriority.test.jar.new")" ] || exit 1\n[ "$(cw_hash lsd-priority-trial.sh)" = "$(cw_hash "$LSD.new")" ] || exit 1\nCHANGED=1\nmv -f "$ROOT/PorscheNavigationPriority.test.jar.new" "$ROOT/PorscheNavigationPriority.test.jar"\nmv -f "$ROOT/cw-window-candidate.new" "$ROOT/cw-window-candidate"\nmv -f "$LSD.new" "$LSD"\nmkdir -p "$STATE"\necho pending > "$STATE/pending.new"\nmv -f "$STATE/pending.new" "$STATE/pending"\nmount -ur /mnt/app\nRW=0\nCHANGED=0\ntrap - 0\necho NAVIGATION_PRIORITY_ONESHOT_READY_NO_REBOOT\n'
 restore=header+'TOOL=$BACKUP/cw-window-candidate\n'
 for name,digest in [('"$TOOL"',BASE_WINDOW),('"$BACKUP/lsd.sh"',BASE_LSD)]:restore+='[ "$(cw_hash '+name+')" = '+digest+' ] || exit 1\n'
 restore+='[ \"$(cw_hash \"$ROOT/cw-window-candidate\")\" = '+sha(window)+' ] || exit 1\n'
 restore+='[ \"$(cw_hash \"$LSD\")\" = '+sha(lsd)+' ] || exit 1\n'
 restore+='mount -uw /mnt/app\ntrap \'mount -ur /mnt/app\' 0\ncp -p "$TOOL" "$ROOT/cw-window-candidate.restore"\ncp -p "$BACKUP/lsd.sh" "$LSD.restore"\n[ "$(cw_hash "$ROOT/cw-window-candidate.restore")" = "$(cw_hash "$TOOL")" ] || exit 1\n[ "$(cw_hash "$LSD.restore")" = "$(cw_hash "$BACKUP/lsd.sh")" ] || exit 1\nmv -f "$ROOT/cw-window-candidate.restore" "$ROOT/cw-window-candidate"\nmv -f "$LSD.restore" "$LSD"\nrm -f "$STATE/pending" "$STATE/confirmed" /ramdisk/cw-nav-priority.enabled\nmount -ur /mnt/app\ntrap - 0\necho NAVIGATION_PRIORITY_BASELINE_RESTORED_RESTART_REQUIRED\n'
 (d/'install.sh').write_bytes(install.encode());(d/'restore.sh').write_bytes(restore.encode())
 link='#!/bin/ksh\nset -e\ncd "$(dirname "$0")"\nunset LD_PRELOAD || :\nJAVA_HOME=/ifs/jre\nexport JAVA_HOME\nLD_LIBRARY_PATH=/ifs/jre/bin:/armle/lib:/armle/usr/lib:/eso/lib\nexport LD_LIBRARY_PATH\nCW_LINK_JAR=$(pwd)/PorscheNavigationPriority.test.jar\n[ -s "$CW_LINK_JAR" ] || exit 1\n/armle/usr/bin/env JAVA_HOME=/ifs/jre LD_LIBRARY_PATH=/ifs/jre/bin:/armle/lib:/armle/usr/lib:/eso/lib /ifs/jre/bin/j9 -Xverify:all -Xmx32m -Xbootclasspath:/ifs/lsd.jxe -Xbootclasspath/p:$CW_LINK_JAR org.connectwow.tests.RuntimeLinkProbe de.audi.tghu.navi.app.cluster.CombiBAPListener de.audi.tghu.navi.app.cluster.ClusterService de.audi.tghu.navi.app.cluster.PorscheRouteGuidance de.audi.tghu.navi.app.cluster.NavigationPriorityRuntime de.audi.tghu.navi.app.dsi.DSINavigationDispatcher org.connectwow.carplay.PorscheCluster org.connectwow.carplay.PorscheClusterControls org.connectwow.carplay.PorscheNavigationPriority > link-check.log 2>&1 &\nCW_LINK_PID=$!\nfunction cw_link_cleanup {\n    trap - 0\n    if [ "$CW_LINK_PID" -gt 1 ]; then\n        kill -TERM "$CW_LINK_PID" 2>/dev/null || :\n        sleep 1\n        kill -KILL "$CW_LINK_PID" 2>/dev/null || :\n        wait "$CW_LINK_PID" 2>/dev/null || :\n    fi\n}\ntrap cw_link_cleanup 0\ntrap \'exit 1\' 1 2 15\nCW_LINK_COUNT=0\nwhile kill -0 "$CW_LINK_PID" 2>/dev/null && [ "$CW_LINK_COUNT" -lt 20 ]; do\n    sleep 1\n    CW_LINK_COUNT=$((CW_LINK_COUNT+1))\ndone\nif kill -0 "$CW_LINK_PID" 2>/dev/null; then\n    kill -TERM "$CW_LINK_PID" 2>/dev/null || :\n    sleep 1\n    kill -KILL "$CW_LINK_PID" 2>/dev/null || :\n    wait "$CW_LINK_PID" 2>/dev/null || :\n    CW_LINK_PID=0\n    echo PRIORITY_J9_LINK_TIMEOUT\n    exit 1\nfi\nCW_LINK_RC=0\nwait "$CW_LINK_PID" || CW_LINK_RC=$?\nCW_LINK_PID=0\ncat link-check.log\n[ "$CW_LINK_RC" -eq 0 ] || exit 1\necho PRIORITY_J9_LINK_PASS\n'
 (d/'link-check.sh').write_bytes(link.encode())
 install=install.replace('/bin/ksh "$PWD/link-check.sh"', '[ \"$(cw_hash link-check.sh)\" = '+sha(d/'link-check.sh')+' ] || exit 1\n/bin/ksh "$PWD/link-check.sh"')
 (d/'install.sh').write_bytes(install.encode())
 readme=(ROOT/'optional/navigation-priority/LEESMIJ-TEST.txt').read_bytes()
 files={'cw-window-priority':window,'PorscheNavigationPriority.test.jar':jar,'lsd-priority-trial.sh':lsd,'install.sh':d/'install.sh','restore.sh':d/'restore.sh','link-check.sh':d/'link-check.sh'}
 manifest={'firmware':'MHI2_ER_POG24_K5137_MU1417','physical_verified':False,'installed':False,'one_boot_only':True,'baseline_window':BASE_WINDOW,'baseline_lsd':BASE_LSD,'files':{n:sha(p) for n,p in files.items()}}
 package=ROOT/'build/porsche-navigation-priority-MU1417-test.zip'
 with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
  for n,p in sorted(files.items()):
   info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));z.writestr(info,p.read_bytes())
  manifest['offline_rom_audit_sha256']=sha(audit)
  z.writestr('rom-link-audit.json',audit.read_bytes())
  z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n');z.writestr('LEESMIJ-TEST.txt',readme)
 (d/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('PRIORITY_TEST_PACKAGE_READY',package,sha(package))
if __name__=='__main__':main()
