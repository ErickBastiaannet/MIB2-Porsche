import hashlib
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'build/porsche-carplay-profiles-MU1417.zip'


def test_profile_package_is_layered_and_qnx_safe():
    with zipfile.ZipFile(PACKAGE) as archive:
        names = set(archive.namelist())
        manager = archive.read('install/scripts/carplay_profiles.sh').decode()
        assert manager.startswith('#!/bin/ksh\n')
        assert not re.search(r'(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{', manager)
        for profile in ('stable', 'v145', 'v146', 'controls'):
            manifest_path = f'online/carplay-profiles/{profile}/payload.manifest'
            manifest = archive.read(manifest_path).decode().splitlines()
            for line in manifest:
                expected, filename = line.split(' ', 1)
                payload = archive.read(f'online/carplay-profiles/{profile}/{filename}')
                assert hashlib.sha256(payload).hexdigest() == expected
        notification_jar = archive.read(
            'online/carplay-profiles/v146/PorscheCarPlayNotifications.experimental.jar')
        nested = ROOT / 'build' / 'PorscheCarPlayNotifications.experimental.jar'
        assert notification_jar == nested.read_bytes()
        with zipfile.ZipFile(nested) as jar:
            assert jar.namelist() == ['org/dsi/ifc/carplay/AppState.class']
        assert 'online/carplay-profiles/v145/PorscheCarPlayNotifications.experimental.jar' not in names
        assert 'online/carplay-profiles/v145/cw-rgi.so' not in names
        assert 'online/carplay-profiles/controls/cw-rgi.so' in names


def test_v145_native_contract_and_logging():
    with zipfile.ZipFile(PACKAGE) as archive:
        launcher = archive.read('online/carplay-profiles/v145/v145-launcher.sh').decode()
        receiver = archive.read('online/carplay-profiles/v145/cw-receiver-v145.so')
        assert 'CW_INITIAL_ZOOM_OUT=1' in launcher
        assert 'connectwow-carplay-logs/v14-5' in launcher
        assert 'cw-rgi' not in launcher
        assert b'cluster-night-mode' in receiver
        assert b'cluster-initial-zoom-out' in receiver


def test_v15_has_same_sd_diagnostics():
    with zipfile.ZipFile(PACKAGE) as archive:
        launcher = archive.read('online/carplay-profiles/controls/controls-launcher.sh').decode()
        hmi = archive.read('online/carplay-profiles/controls/lsd-controls.sh').decode()
        assert 'connectwow-carplay-logs/v15' in launcher
        assert 'connectwow-carplay-logs/v15' in hmi
        assert 'CarPlay: kopieer diagnostiek naar SD' in archive.read(
            'install/esd/OnlineMenu.esd').decode()
