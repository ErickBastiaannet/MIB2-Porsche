import hashlib
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_zoom_probe_consumes_ticket_and_falls_back(tmp_path):
    state = tmp_path / 'state'
    state.mkdir()
    jar = tmp_path / 'PorscheCarPlayZoom.experimental.jar'
    jar.write_bytes(b'fixture jar')
    stock = tmp_path / 'stock.sh'
    result = tmp_path / 'result'
    stock.write_text('echo "$VMOPTIONS" > "' + str(result) + '"\n')
    tool = tmp_path / 'hash.sh'
    tool.write_text('#!/bin/sh\nsha256sum "$2" | cut -d " " -f 1\n')
    tool.chmod(0o755)
    text = (ROOT / 'unit/lsd_zoom_oneshot.sh').read_text()
    replacements = {
        'ROOT=/mnt/app/eso/hmi/connectwow-carplay/zoom-oneshot': 'ROOT=' + str(tmp_path),
        'STATE=/mnt/persist/connectwow-carplay/zoom-oneshot': 'STATE=' + str(state),
        'STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock': 'STOCK=' + str(stock),
        'TOOL=/mnt/app/eso/hmi/connectwow-carplay/controls-v15/cw-window-candidate': 'TOOL=' + str(tool),
        'OLD=/mnt/app/eso/hmi/lsd/jars/ConnectWowZoom.experimental.jar': 'OLD=' + str(tmp_path / 'old.jar'),
        'EXPECTED=264f4231e69c1ab24cf036b7e9a518d25374a3a5723b82b31647371c86779a82': 'EXPECTED=' + hashlib.sha256(jar.read_bytes()).hexdigest(),
        'STOCK_SHA=7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091': 'STOCK_SHA=' + hashlib.sha256(stock.read_bytes()).hexdigest(),
        'exec /bin/ksh': 'exec /bin/sh',
    }
    for before, after in replacements.items():
        assert before in text
        text = text.replace(before, after)
    wrapper = tmp_path / 'wrapper.sh'
    wrapper.write_text(text)
    env = dict(os.environ, VMOPTIONS='')
    def boot():
        return subprocess.run(['/bin/sh', str(wrapper)], env=env, check=False)
    (state / 'pending').write_text('probe')
    assert boot().returncode == 0
    assert '-Xbootclasspath/p:' in result.read_text()
    assert not (state / 'pending').exists()
    assert (state / 'attempted').exists()
    assert boot().returncode == 0
    assert result.read_text().strip() == ''
    (state / 'pending').write_text('probe')
    (tmp_path / 'old.jar').write_bytes(b'old hook')
    assert boot().returncode == 0
    assert result.read_text().strip() == ''
    (tmp_path / 'old.jar').unlink()
    jar.write_bytes(b'corrupt')
    assert boot().returncode == 0
    assert result.read_text().strip() == ''
    stock.write_text('exit 0\n')
    assert boot().returncode != 0
