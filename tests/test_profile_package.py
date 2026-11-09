import hashlib
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'build/porsche-carplay-profiles-MU1417.zip'


def test_profile_package_is_layered_and_qnx_safe():
    with zipfile.ZipFile(PACKAGE) as archive:
        names = set(archive.namelist())
        manager = archive.read('install/scripts/cwpm.sh').decode()
        assert manager.startswith('#!/bin/ksh\n')
        assert 'install/scripts/carplay_profiles.sh' not in names
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
        for wrapper in (
            'stable', 'v145', 'v146', 'confirm_v146', 'controls',
            'java', 'guidance', 'confirm_guidance', 'confirm', 'logs', 'status', 'oem',
        ):
            body = archive.read(f'install/scripts/carplay_profile_{wrapper}.sh').decode()
            assert '"$BASE/cwpm.sh"' in body


def test_v145_native_contract_and_logging():
    with zipfile.ZipFile(PACKAGE) as archive:
        launcher = archive.read('online/carplay-profiles/v145/v145-launcher.sh').decode()
        receiver = archive.read('online/carplay-profiles/v145/cw-receiver-v145.so')
        assert 'CW_AUTO_ALT_WAKE=1' in launcher
        assert 'CW_INITIAL_ZOOM_OUT' not in launcher
        assert 'connectwow-carplay-logs/v14-5' in launcher
        assert 'cw-rgi' not in launcher
        assert '--prime-geometry' not in launcher
        assert 'WAITING_FOR_READY_STREAM' not in launcher
        assert 'exec "$CW_ROOT/cw-window-candidate" --run "$CW_ROOT" "$CW_CHILD"' in launcher
        assert b'alt-main-ready-armed' in receiver
        assert b'map-control-session-remembered' in receiver
        assert b'cluster-night-mode-replayed' in receiver
        assert b'cluster-night-mode-after-showui' in receiver


def test_v15_has_same_sd_diagnostics():
    with zipfile.ZipFile(PACKAGE) as archive:
        launcher = archive.read('online/carplay-profiles/controls/controls-launcher.sh').decode()
        hmi = archive.read('online/carplay-profiles/controls/lsd-controls.sh').decode()
        assert 'connectwow-carplay-logs/v15' in launcher
        assert 'connectwow-carplay-logs/v15' in hmi
        assert 'CarPlay: kopieer diagnostiek naar SD' in archive.read(
            'install/esd/OnlineMenu.esd').decode()


def test_combined_java_bridge_is_explicit_one_shot():
    with zipfile.ZipFile(PACKAGE) as archive:
        manager = archive.read('install/scripts/cwpm.sh').decode()
        menu = archive.read('install/esd/OnlineMenu.esd').decode()
        assert 'test-controls-java)' in manager
        assert 'echo combined > "$CONTROLS_STATE/pending"' in manager
        assert 'stage_file "$CONTROLS/lsd-controls.sh" "$LSD"' in manager
        assert '[ -s "$CONTROLS_STATE/attempted" ] || fail' in manager
        assert 'test gecombineerde Java-bridge eenmaal' in menu
        assert 'bevestig gecombineerde Java-bridge' in menu


def test_guidance_uses_mm_ipod_and_separate_fail_closed_java_probe():
    with zipfile.ZipFile(PACKAGE) as archive:
        names = set(archive.namelist())
        manager = archive.read('install/scripts/cwpm.sh').decode()
        menu = archive.read('install/esd/OnlineMenu.esd').decode()
        controls = 'online/carplay-profiles/controls/'
        assert controls + 'mm-ipod-rgi.sh' in names
        assert controls + 'PorscheCarPlayGuidance.experimental.jar' in names
        assert controls + 'lsd-guidance.sh' in names
        launcher = archive.read(controls + 'controls-launcher.sh').decode()
        assert 'cw-rgi.so' not in launcher
        mm_ipod = archive.read(controls + 'mm-ipod-rgi.sh').decode()
        assert 'connectwow-rgi/mm-ipod' in mm_ipod
        assert 'mv "$STATE/pending" "$STATE/attempted"' in mm_ipod
        hmi = archive.read(controls + 'lsd-guidance.sh').decode()
        assert 'controls-v15/PorscheCarPlayGuidance.experimental.jar' in hmi
        assert '[ -s "$CW_EXTRA_PROBE_STATE/confirmed" ]' in hmi
        assert 'test-guidance)' in manager
        assert 'patch_iap2_config || fail' in manager
        assert 'ConnectWow iAP2 Route Guidance message registration.' in manager
        assert 'IAP2_GUIDANCE_SHA=5ca0a762dcf24bef3661f77dc4641433767026e4500a2a60f2c60ed0cc77af41' in manager
        assert 'rollback_guidance' in manager
        assert 'echo confirmed > /mnt/persist/connectwow-carplay/guidance-probe/confirmed' in manager
        assert 'test routebegeleiding eenmaal' in menu
        assert 'bevestig routebegeleiding' in menu
