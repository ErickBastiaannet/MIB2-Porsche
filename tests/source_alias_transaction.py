"""Run with the existing QNX toolchain image; production paths are mocked."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sha = lambda value: hashlib.sha256(value).hexdigest()
with tempfile.TemporaryDirectory() as folder:
    base = Path(folder)
    app = base / 'app'
    controls = app / 'eso/hmi/connectwow-carplay/controls-v15'
    controls.mkdir(parents=True)
    start = app / 'eso/bin/apps/cw-carplay-start'
    start.parent.mkdir(parents=True)
    stage = base / 'stage'
    stage.mkdir()
    old_lib, old_start = b'previous library', b'previous starter'
    new_lib = (ROOT / 'build/qnx/libcw-porsche-rgi-source-alias.so').read_bytes()
    new_start = (ROOT / 'unit/carplay_receiver_start.sh').read_bytes()
    (controls / 'cw-rgi.so').write_bytes(old_lib)
    start.write_bytes(old_start)
    (stage / 'cw-rgi.so').write_bytes(new_lib)
    (stage / 'carplay_receiver_start.sh').write_bytes(new_start)
    tool = controls / 'cw-window-candidate'
    tool.write_text('#!/bin/sh\nsha256sum "$2" | cut -d " " -f 1\n')
    tool.chmod(0o755)
    script = (ROOT / 'unit/install_source_alias_repair.sh').read_text()
    for previous, replacement in {
        '/mnt/app': str(app), '/ramdisk/cw-source-repair-20261117': str(stage),
        'c917554dc9027d8d0fc8044dbccf71c1ef7f5689966427b7bf122df86701e2e9': sha(old_lib),
        'f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e': sha(old_start),
    }.items():
        script = script.replace(previous, replacement)
    script = script.replace('set -e\n', 'set -e\nfunction mount { echo "$*" >> "' + str(base / 'mount.log') + '"; }\n', 1)
    path = base / 'install.sh'
    path.write_text(script)
    def run():
        return subprocess.run(['/opt/qnx650/host/linux/x86/usr/bin/ksh', str(path)],
                              env=dict(os.environ, PATH='/usr/bin:/bin'), capture_output=True, text=True)
    (stage / 'cw-rgi.so').write_bytes(new_lib + b'corrupt')
    result = run()
    assert result.returncode and not (base / 'mount.log').exists()
    assert (controls / 'cw-rgi.so').read_bytes() == old_lib and start.read_bytes() == old_start
    (stage / 'cw-rgi.so').write_bytes(new_lib)
    result = run()
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (controls / 'cw-rgi.so').read_bytes() == new_lib and start.read_bytes() == new_start
    backup = controls / 'before-apple-source-20261117'
    assert (backup / 'cw-rgi.so').read_bytes() == old_lib
    assert (backup / 'cw-carplay-start').read_bytes() == old_start
    assert (base / 'mount.log').read_text().splitlines()[-1] == '-ur ' + str(app)
    assert run().returncode != 0
print('SOURCE_ALIAS_TRANSACTION_PASS corrupt payload refused; verified backups; atomic install; read-only remount; repeat refused')
