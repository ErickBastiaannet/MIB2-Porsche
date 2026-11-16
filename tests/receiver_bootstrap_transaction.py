import hashlib,os,pathlib,subprocess,tempfile
sha=lambda b:hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as tmp:
 t=pathlib.Path(tmp);app=t/'app';system=t/'system';root=app/'eso/hmi/connectwow-carplay/controls-v15';root.mkdir(parents=True);(app/'eso/bin/apps').mkdir(parents=True)
 config=system/'etc/eso/production/smartphone_integrator.json';config.parent.mkdir(parents=True);old=b'previous SI config';config.write_bytes(old)
 pkg=t/'package';pkg.mkdir();tool=b'#!/bin/sh\nsha256sum "$2" | cut -d " " -f 1\n';(root/'cw-window-candidate').write_bytes(tool);(root/'cw-window-candidate').chmod(0o755)
 capture=b'capture unchanged';(root/'cw-receiver-controls.so').write_bytes(capture)
 wrapper=pathlib.Path('/src/unit/carplay_receiver_start.sh').read_bytes();new=pathlib.Path('/src/.tmp/map-output-live/smartphone-video-bootstrap.json').read_bytes()
 (pkg/'carplay_receiver_start.sh').write_bytes(wrapper);(pkg/'smartphone-video-bootstrap.json').write_bytes(new)
 script=pathlib.Path('/src/unit/install_receiver_bootstrap.sh').read_text()
 for a,b in {'/mnt/app':str(app),'/mnt/system':str(system),'e042e65da4f366fef35c700528c7054fcf7f6e38dba23f7c291928895d91cb86':sha(old),'41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce':sha(tool),'c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847':sha(capture)}.items():script=script.replace(a,b)
 script=script.replace('set -e\n','set -e\nfunction mount { echo "$*" >> "'+str(t/'mount.log')+'"; }\n',1)
 (pkg/'install.sh').write_text(script)
 def run():return subprocess.run(['/opt/qnx650/host/linux/x86/usr/bin/ksh',str(pkg/'install.sh')],env=dict(os.environ,PATH='/usr/bin:/bin'),capture_output=True,text=True)
 (pkg/'carplay_receiver_start.sh').write_bytes(wrapper+b'corrupt');r=run();assert r.returncode!=0 and config.read_bytes()==old and not (t/'mount.log').exists()
 (pkg/'carplay_receiver_start.sh').write_bytes(wrapper);r=run();assert r.returncode==0,(r.stdout,r.stderr)
 assert config.read_bytes()==new and (app/'eso/bin/apps/cw-carplay-start').read_bytes()==wrapper
 assert (root/'before-video-bootstrap-20261116/smartphone_integrator.json').read_bytes()==old
 assert (root/'cw-window-candidate').read_bytes()==tool and (root/'cw-receiver-controls.so').read_bytes()==capture
 assert (t/'mount.log').read_text().splitlines()[-2:]==['-ur '+str(system),'-ur '+str(app)]
 print('VIDEO_BOOTSTRAP_TRANSACTION_PASS corrupt payload rejected; config backup; atomic install; existing video binaries retained; both mounts read-only')
