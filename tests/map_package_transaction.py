"""Execute the packaged ksh install/restore against an isolated mock unit."""
import hashlib, os, pathlib, subprocess, tempfile, zipfile
sha=lambda b:hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as tmp:
    top=pathlib.Path(tmp);app=top/'app';root=app/'eso/hmi/connectwow-carplay/controls-v15';root.mkdir(parents=True)
    pkg=top/'package';pkg.mkdir()
    with zipfile.ZipFile('/src/build/map-output-repair-MU1417.zip') as z:
        install=z.read('install.sh').decode();restore=z.read('restore.sh').decode()
    old=b'#!/bin/sh\n# original fixture\nsha256sum "$2" | cut -d " " -f 1\n'
    new=old.replace(b'original',b'candidate')
    capture=b'unchanged capture';firmware=b'verified firmware'
    (root/'cw-window-candidate').write_bytes(old);(root/'cw-window-candidate').chmod(0o755)
    (root/'cw-receiver-controls.so').write_bytes(capture)
    (pkg/'cw-window-candidate').write_bytes(new)
    (top/'lsd.jxe').write_bytes(firmware)
    mappings={'/mnt/app':str(app),'/ifs/lsd.jxe':str(top/'lsd.jxe'),
      '0cf0e784063396004f65d71195649815e467f197a1a9dc2aeb66506c4d412afa':sha(old),
      'c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847':sha(capture),
      'a7c5e723904be98a349b5fcdb9e04846f1306b64ef1ef538d9ee08502864c04d':sha(firmware)}
    # Read actual candidate hash from manifest; this is a filesystem/transaction
    # test of the real script, not an ARM execution test.
    import json
    with zipfile.ZipFile('/src/build/map-output-repair-MU1417.zip') as z:mappings[json.loads(z.read('manifest.json'))['payload_sha256']]=sha(new)
    for name,s in [('install.sh',install),('restore.sh',restore)]:
        for a,b in mappings.items():s=s.replace(a,b)
        s=s.replace('set -e\n','set -e\nfunction mount { echo "$*" >> "'+str(top/'mount.log')+'"; }\n',1)
        (pkg/name).write_text(s)
    env=dict(os.environ,PATH='/usr/bin:/bin')
    def run(name):return subprocess.run(['/opt/qnx650/host/linux/x86/usr/bin/ksh',str(pkg/name)],env=env,capture_output=True,text=True)
    (pkg/'cw-window-candidate').write_bytes(new+b'corrupt')
    assert run('install.sh').returncode!=0 and (root/'cw-window-candidate').read_bytes()==old
    assert not (top/'mount.log').exists()
    (pkg/'cw-window-candidate').write_bytes(new)
    r=run('install.sh');assert r.returncode==0,(r.stdout,r.stderr)
    assert (root/'cw-window-candidate').read_bytes()==new
    assert (root/'before-map-lease-20261116/cw-window-candidate').read_bytes()==old
    assert (root/'cw-receiver-controls.so').read_bytes()==capture
    assert '-ur' in (top/'mount.log').read_text().splitlines()[-1]
    r=run('restore.sh');assert r.returncode==0,(r.stdout,r.stderr)
    assert (root/'cw-window-candidate').read_bytes()==old
    assert '-ur' in (top/'mount.log').read_text().splitlines()[-1]
print('MAP_PACKAGE_TRANSACTION_PASS corrupt payload refused before mount; install/backup/restore; capture untouched; read-only remount')
