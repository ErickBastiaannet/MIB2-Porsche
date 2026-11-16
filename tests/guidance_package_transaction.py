"""Exercise actual checklist install/restore scripts on an isolated mock unit."""
import hashlib,json,os,pathlib,subprocess,tempfile,zipfile
sha=lambda b:hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as tmp:
 top=pathlib.Path(tmp);app=top/'app';root=app/'eso/hmi/connectwow-carplay/controls-v15';root.mkdir(parents=True)
 state=top/'persist/connectwow-carplay'
 for name in ['guidance-native','guidance-probe']:(state/name).mkdir(parents=True);(state/name/'confirmed').write_text('confirmed\n')
 (top/'ramdisk').mkdir();pkg=top/'package';pkg.mkdir()
 with zipfile.ZipFile('/src/build/guidance-processing-checklist-MU1417.zip') as z:
  manifest=json.loads(z.read('manifest.json'));scripts={n:z.read(n).decode() for n in ['install.sh','restore.sh']}
 old={'cw-rgi.so':b'original native','PorscheCarPlayGuidance.experimental.jar':b'original jar'}
 new={'cw-rgi.so':b'candidate native','PorscheCarPlayGuidance.experimental.jar':b'candidate jar'}
 hash_tool=b'#!/bin/sh\nsha256sum "$2" | cut -d " " -f 1\n'
 (root/'cw-window-candidate').write_bytes(hash_tool);(root/'cw-window-candidate').chmod(0o755)
 mappings={'/mnt/app':str(app),'/mnt/persist':str(top/'persist'),'/ramdisk':str(top/'ramdisk')}
 for n in old:
  (root/n).write_bytes(old[n]);(pkg/n).write_bytes(new[n]);mappings[manifest['required_live_sha256'][n]]=sha(old[n]);mappings[manifest['payload_sha256'][n]]=sha(new[n])
 for name,s in scripts.items():
  for a,b in mappings.items():s=s.replace(a,b)
  s=s.replace('set -e\n','set -e\nfunction mount { echo "$*" >> "'+str(top/'mount.log')+'"; }\n',1)
  (pkg/name).write_text(s)
 env=dict(os.environ,PATH='/usr/bin:/bin')
 def run(n):return subprocess.run(['/opt/qnx650/host/linux/x86/usr/bin/ksh',str(pkg/n)],capture_output=True,text=True,env=env)
 (pkg/'cw-rgi.so').write_bytes(b'corrupt')
 assert run('install.sh').returncode!=0 and not (top/'mount.log').exists()
 assert all((root/n).read_bytes()==old[n] for n in old)
 (pkg/'cw-rgi.so').write_bytes(new['cw-rgi.so'])
 r=run('install.sh');assert r.returncode==0,(r.stdout,r.stderr)
 assert all((root/n).read_bytes()==new[n] for n in old)
 assert all((root/'before-processing-checklist-20261116'/n).read_bytes()==old[n] for n in old)
 for name in ['guidance-native','guidance-probe']:
  assert not (state/name/'confirmed').exists() and (state/name/'pending').read_text().strip()=='pending'
 assert '-ur' in (top/'mount.log').read_text().splitlines()[-1]
 r=run('restore.sh');assert r.returncode==0,(r.stdout,r.stderr)
 assert all((root/n).read_bytes()==old[n] for n in old)
 for name in ['guidance-native','guidance-probe']:assert (state/name/'confirmed').exists() and not (state/name/'pending').exists()
 assert (root/'cw-window-candidate').read_bytes()==hash_tool
 assert '-ur' in (top/'mount.log').read_text().splitlines()[-1]
print('GUIDANCE_PACKAGE_TRANSACTION_PASS bad payload refused; paired install/backup/restore; markers restored; map unchanged; RO remount')
