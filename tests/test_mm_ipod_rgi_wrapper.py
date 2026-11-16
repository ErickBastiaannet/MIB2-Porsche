from pathlib import Path
import os
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_wrapper_is_one_shot_and_execs_untouched_oem_binary() -> None:
    text = (ROOT / "unit" / "mm_ipod_rgi.sh").read_text()
    assert "connectwow-rgi/mm-ipod" in text
    assert 'mv "$STATE/pending" "$STATE/attempted"' in text
    assert 'exec "$REAL" "$@"' in text
    assert "LD_PRELOAD" in text


def test_dio_launcher_does_not_preload_mm_ipod_hook() -> None:
    text = (ROOT / "unit" / "dio_manager_controls.sh").read_text()
    assert "cw-rgi.so" not in text
    assert 'LD_PRELOAD="$CW_ROOT/cw-receiver-controls.so' in text


@pytest.mark.skipif(os.name == "nt", reason="Runs the actual shell launcher on Linux")
def test_one_boot_trial_survives_reconnect_and_expires_on_reboot(tmp_path):
    state=tmp_path / "state";state.mkdir()
    root=tmp_path / "root";root.mkdir()
    real=tmp_path / "real.sh"
    real.write_text('#!/bin/sh\necho "${CW_RGI_ENABLE:-0}"\n')
    real.chmod(0o755)
    libc=next(Path('/lib').glob('*/libc.so.6'),None)
    if libc is None:pytest.skip('No host shared-library fixture')
    (root / 'cw-rgi.so').symlink_to(libc)
    trial=tmp_path / "ram-trial"
    text=(ROOT / "unit/mm_ipod_rgi.sh").read_text()
    text=text.replace('ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15','ROOT='+str(root))
    text=text.replace('REAL=/mnt/app/armle/usr/sbin/connectwow-rgi/mm-ipod','REAL='+str(real))
    text=text.replace('STATE=/mnt/persist/connectwow-carplay/guidance-native','STATE='+str(state))
    text=text.replace('TRIAL=/ramdisk/cw-guidance-native-trial','TRIAL='+str(trial))
    wrapper=tmp_path / 'wrapper.sh';wrapper.write_text(text)
    def run():
        env=dict(os.environ);env.pop('LD_PRELOAD',None)
        return subprocess.check_output(['sh',str(wrapper)],env=env,text=True).strip()
    (state / 'pending').write_text('pending\n')
    assert run()=='1' and not (state/'pending').exists() and (state/'attempted').exists()
    assert run()=='1'  # USB reconnect in the same PCM boot.
    trial.unlink()  # Full boot clears RAM, not persistent attempted.
    assert run()=='0'
    (state/'confirmed').write_text('confirmed\n')
    assert run()=='1'
