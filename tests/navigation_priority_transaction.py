"""Real packaged ksh against isolated filesystems, including one-boot fallback."""
import hashlib,json,os,pathlib,subprocess,tempfile,zipfile
ROOT=pathlib.Path('/src');sha=lambda b:hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(ROOT/'build/porsche-navigation-priority-MU1417-test.zip') as z:
 raw={n:z.read(n) for n in z.namelist()};manifest=json.loads(raw['manifest.json'])
 for n,d in manifest['files'].items():assert sha(raw[n])==d,n
 assert sha(raw['rom-link-audit.json'])==manifest['offline_rom_audit_sha256']
 assert json.loads(raw['rom-link-audit.json'])['jar_sha256']==manifest['files']['PorscheNavigationPriority.test.jar']
for failure in [False,True]:
 with tempfile.TemporaryDirectory() as tmp:
  top=pathlib.Path(tmp);app=top/'app';persist=top/'persist';ram=top/'ram';ram.mkdir()
  root=app/'eso/hmi/connectwow-carplay/controls-v15';root.mkdir(parents=True)
  lsd=app/'eso/hmi/lsd/lsd.sh';lsd.parent.mkdir(parents=True)
  baseline=b'#!/bin/sh\n# verified baseline fixture\n';lsd.write_bytes(baseline)
  old=b'#!/bin/sh\n# stock fixture\nsha256sum "$2" | cut -d " " -f 1\n';new=old.replace(b'stock',b'candidate')
  (root/'cw-window-candidate').write_bytes(old);(root/'cw-window-candidate').chmod(0o755)
  capture=b'untouched capture';guidance=b'untouched guidance';jar=b'priority jar fixture'
  (root/'cw-receiver-controls.so').write_bytes(capture);(root/'PorscheCarPlayGuidance.experimental.jar').write_bytes(guidance)
  zoom=app/'eso/hmi/connectwow-carplay/zoom-probe';zoom.mkdir();(zoom/'PorscheCarPlayZoom.experimental.jar').write_text('zoom');(zoom/'PorscheCarPlayZoomLogo.probe.jar').write_text('logo')
  for name in ['zoom-probe','guidance-probe','satellite-logo-probe']:
   s=persist/'connectwow-carplay'/name;s.mkdir(parents=True);(s/'confirmed').write_text('confirmed')
  package=top/'package';package.mkdir()
  text=raw['lsd-priority-trial.sh'].decode()
  mappings={'/mnt/app':str(app),'/mnt/persist':str(persist),'/ramdisk':str(ram),manifest['files']['PorscheNavigationPriority.test.jar']:sha(jar),manifest['files']['cw-window-priority']:sha(new)}
  for a,b in mappings.items():text=text.replace(a,b)
  newlsd=text.encode();(package/'lsd-priority-trial.sh').write_bytes(newlsd)
  (package/'PorscheNavigationPriority.test.jar').write_bytes(jar);(package/'cw-window-priority').write_bytes(new);(package/'link-check.sh').write_bytes(raw['link-check.sh'])
  mappings.update({manifest['baseline_window']:sha(old),manifest['baseline_lsd']:sha(baseline),manifest['files']['lsd-priority-trial.sh']:sha(newlsd),'c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847':sha(capture),'a24db7e9851b736bc4a3def7081de8219ab4f6e9f15a23c6ed644e1b5d30bf52':sha(guidance)})
  for n in ['install.sh','restore.sh']:
   s=raw[n].decode()
   for a,b in mappings.items():s=s.replace(a,b)
   s=s.replace('/bin/ksh "$PWD/link-check.sh"','echo MOCK_J9_LINK_CHECK')
   s=s.replace('/bin/ksh','/opt/qnx650/host/linux/x86/usr/bin/ksh')
   s=s.replace('set -e\n','set -e\nfunction mount { echo "$*" >> "'+str(top/'mount.log')+'"; }\n',1)
   if failure and n=='install.sh':
    injection='function mv { if [ "$1" = "-f" ] && [ "$2" = "'+str(lsd)+'.new" ]; then return 17; fi; /bin/mv "$@"; }\n'
    s=s.replace('RW=0\nCHANGED=0',injection+'RW=0\nCHANGED=0',1)
   (package/n).write_text(s)
  env=dict(os.environ,PATH='/usr/bin:/bin')
  def run(n):return subprocess.run(['/opt/qnx650/host/linux/x86/usr/bin/ksh',str(package/n)],capture_output=True,text=True,env=env)
  (package/'PorscheNavigationPriority.test.jar').write_bytes(jar+b'corrupt');r=run('install.sh');assert r.returncode!=0 and lsd.read_bytes()==baseline and not(top/'mount.log').exists()
  (package/'PorscheNavigationPriority.test.jar').write_bytes(jar);r=run('install.sh')
  if failure:
   assert r.returncode!=0 and lsd.read_bytes()==baseline and (root/'cw-window-candidate').read_bytes()==old,(r.stdout,r.stderr)
   assert (top/'mount.log').read_text().splitlines()[-1].startswith('-ur');continue
  assert r.returncode==0,(r.stdout,r.stderr)
  assert lsd.read_bytes()==newlsd and (root/'cw-window-candidate').read_bytes()==new
  assert (root/'cw-receiver-controls.so').read_bytes()==capture and (root/'PorscheCarPlayGuidance.experimental.jar').read_bytes()==guidance
  snippet=text.split('# CONNECTWOW_JAVA_PROBE_V1\n',1)[1].split('# CONNECTWOW_JAVA_PROBE_END',1)[0]
  (package/'boot.sh').write_text(snippet+'\necho "$VMOPTIONS"\n')
  first=run('boot.sh');assert first.returncode==0,(first.stdout,first.stderr)
  assert first.stdout.count('-Xbootclasspath/p:')==1 and 'PorscheNavigationPriority.test.jar' in first.stdout and 'navigationPriority=porsche-first' in first.stdout
  assert (ram/'cw-nav-priority.enabled').exists()
  second=run('boot.sh');assert second.returncode==0
  assert 'PorscheNavigationPriority.test.jar' not in second.stdout and 'PorscheCarPlayZoomLogo.probe.jar' in second.stdout and 'PorscheCarPlayGuidance.experimental.jar' in second.stdout
  assert not(ram/'cw-nav-priority.enabled').exists()
  state=persist/'connectwow-carplay/navigation-priority'
  (state/'confirmed').write_text('physically confirmed')
  for unused in range(2):
   permanent=run('boot.sh');assert permanent.returncode==0,(permanent.stdout,permanent.stderr)
   assert permanent.stdout.count('-Xbootclasspath/p:')==1 and 'PorscheNavigationPriority.test.jar' in permanent.stdout
   assert (ram/'cw-nav-priority.enabled').exists()
  r=run('restore.sh');assert r.returncode==0,(r.stdout,r.stderr)
  assert not(state/'confirmed').exists()
  assert lsd.read_bytes()==baseline and (root/'cw-window-candidate').read_bytes()==old
  assert (top/'mount.log').read_text().splitlines()[-1].startswith('-ur')
print('PRIORITY_PACKAGE_PASS hashes, corrupt input refusal, atomic rollback, single candidate classpath, next-boot fallback, complete baseline restore')
