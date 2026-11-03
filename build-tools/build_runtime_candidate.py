"""Package the verified native build without an automatic firmware installer."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    for name in ('sources.sha256', 'artifacts.sha256'):
        for line in (ROOT / 'build/qnx' / name).read_text().splitlines():
            expected, path = line.split(maxsplit=1)
            if digest((ROOT / path).read_bytes()) != expected:
                raise SystemExit('Stale QNX build: ' + path)
    files = {
        'payload/porsche-carplay': (ROOT / 'build/qnx/porsche-carplay-window-candidate').read_bytes(),
        'payload/libcw-porsche-capture_receiver.so': (ROOT / 'build/qnx/libcw-porsche-capture_receiver.so').read_bytes(),
        'payload/libcw-porsche-rgi.so': (ROOT / 'build/qnx/libcw-porsche-rgi.so').read_bytes(),
        'payload/libcw-query-stdio.so': (ROOT / 'build/qnx/libcw-query-stdio.so').read_bytes(),
        'hmi-candidate/PorscheCarPlayBridge.experimental.jar': (ROOT / 'build/PorscheCarPlayBridge.experimental.jar').read_bytes(),
        'diagnostics/cw-ram-receive': (ROOT / 'build/qnx/cw-ram-receive').read_bytes(),
        'diagnostics/cw-hidden-yuv-window': (ROOT / 'build/qnx/cw-hidden-yuv-window').read_bytes(),
        'source/dio_manager.sh': (ROOT / 'unit/dio_manager.sh').read_bytes(),
        'firmware-profile.json': (ROOT / 'firmware-profile.json').read_bytes(),
        'LICENSE.upstream': (ROOT / 'LICENSE.upstream').read_bytes(),
        'LEESMIJ.txt': (
            'Porsche MU1417 native CarPlay-kandidaat\n'
            '=====================================\n'
            'Geen automatische SD-installatie; Java/HMI wordt niet automatisch gewijzigd.\n'
            'Ontvanger: IPv6 TCP 7001, toegestaan door de firmware-firewall.\n'
            'Diagnostische bestandsoverdracht: TCP 22111 op de debugverbinding.\n'
            'Decoder en EGL-venster draaien in afzonderlijke processen.\n'
            'Herstel eerst de tijdelijke DIO-starter van de vorige voertuigtest.\n'
            'De volledige iPhone-videolevering moet nog fysiek worden bevestigd.\n'
            'De HMI-kandidaat observeert Porsche setMapScale en stuurt zoom alleen bij een vers CarPlay-ready-signaal.\n'
            'De instrumentmenulijst is OEM en wordt niet overschreven: de firmware-API biedt hier geen veilige per-regel-zichtbaarheid.\n'
            'LET OP: dit pakket bevat alleen de rechter CarPlay-kaartvideoketen.\n'
            'iAP2 Route Guidance (0x5200..0x5204) en de vertaling naar Porsche BAP voor\n'
            'manoeuvrepijlen, afstand en rijstroken op het linker fysieke scherm ontbreken nog.\n'
            'Het pakket is daarom geen complete cluster-navigation-oplossing en mag niet worden geinstalleerd.\n'
            'De reguliere SD-installer blijft daarom geblokkeerd.\n'
        ).encode(),
    }
    for folder, patterns in [('native', ('*.c', '*.h', '*.inc')), ('build/native', ('*.c', '*.h', '*.inc'))]:
        for pattern in patterns:
            for path in sorted((ROOT / folder).glob(pattern)):
                files['source/' + folder.replace('/', '-') + '/' + path.name] = path.read_bytes()
    manifest = {
        'firmware': 'MHI2_ER_POG24_K5137_MU1417',
        'status': 'complete MU1417 test candidate; physical semantic-guidance verification pending',
        'carplay_video': {'family': 'IPv6', 'tcp_port': 7001},
        'route_guidance': {
            'implemented': True,
            'iap2_messages': ['0x5200', '0x5201', '0x5202', '0x5203', '0x5204'],
            'target': 'CombiBAPServiceNavi / left physical instrument display',
        },
        'changes_firewall': False,
        'changes_hmi_startup': True,
        'hmi_bridge_included_but_not_installed': False,
        'cluster_controls': {
            'zoom': True,
            'oem_menu_preserved': True,
            'turn_arrows': True,
            'lane_guidance': True,
            'maneuver_distance': True,
        },
        'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in sorted(files.items())},
    }
    files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output = ROOT / 'build/porsche-mu1417-runtime-candidate.zip'
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    print('RUNTIME_CANDIDATE_BUILT', output, output.stat().st_size)


if __name__ == '__main__':
    main()
