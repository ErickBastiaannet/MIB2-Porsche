"""Installer mock including a failure after the executable has been replaced."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
for failure in [False, True]:
    with tempfile.TemporaryDirectory() as folder:
        base=Path(folder);app=base/'app';controls=app/'eso/hmi/connectwow-carplay/controls-v15'
        controls.mkdir(parents=True);stage=base/'stage';stage.mkdir();tool=controls/'cw-window-candidate'
        old=b'#!/bin/sh\n# old\nsha256sum "$2" | cut -d " " -f 1\n'
        new=('#!/bin/sh\n# candidate\nif [ -f "'+str(base/'inject-failure')+'" ] && [ "$2" = "'+str(tool)+'" ]; then exit 1; fi\nsha256sum "$2" | cut -d " " -f 1\n').encode()
        tool.write_bytes(old);tool.chmod(0o755);(stage/'cw-window-startup').write_bytes(new)
        text=(ROOT/'unit/install_context_startup.sh').read_text()
        for a,b in {'/mnt/app':str(app),'/ramdisk/cw-context-startup-20261117':str(stage),
                    '41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce':sha(old),
                    '6e7fcdaad2aef40cf9381f6a08374b58501044d63d091ad64957921f8a426d9f':sha(new)}.items():text=text.replace(a,b)
        text=text.replace('set -e\n','set -e\nfunction mount { echo "$*" >> "'+str(base/'mount.log')+'"; }\n',1)
        script=base/'install.sh';script.write_text(text)
        def run():return subprocess.run(['/opt/qnx650/host/linux/x86/usr/bin/ksh',str(script)],env=dict(os.environ,PATH='/usr/bin:/bin'),capture_output=True,text=True)
        (stage/'cw-window-startup').write_bytes(new+b'corrupt')
        assert run().returncode and not (base/'mount.log').exists() and tool.read_bytes()==old
        (stage/'cw-window-startup').write_bytes(new)
        if failure:(base/'inject-failure').touch()
        result=run()
        assert bool(result.returncode)==failure,(result.stdout,result.stderr)
        assert tool.read_bytes()==(old if failure else new)
        assert (controls/'before-context-startup-20261117/cw-window-candidate').read_bytes()==old
        assert (base/'mount.log').read_text().splitlines()[-1]=='-ur '+str(app)
print('CONTEXT_STARTUP_TRANSACTION_PASS corrupt payload refused; verified backup; atomic replacement; post-swap rollback; read-only remount')
