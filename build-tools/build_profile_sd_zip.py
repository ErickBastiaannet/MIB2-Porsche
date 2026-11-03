"""Build one SD overlay that can switch safely between OEM, stable V14 and Controls V15."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(files: dict[str, bytes]) -> bytes:
    return ''.join(f'{digest(data)} {name}\n' for name, data in sorted(files.items())).encode()


def main() -> None:
    verified = ROOT / 'verified/v14'
    stable = {
        'cw-window-candidate': (verified / 'cw-window-candidate').read_bytes(),
        'cw-receiver-v6.so': (verified / 'cw-receiver-v6.so').read_bytes(),
        'libcw-query-stdio.so': (verified / 'libcw-query-stdio.so').read_bytes(),
        'stable-launcher.sh': (ROOT / 'unit/dio_manager_verified_test.sh').read_bytes(),
    }
    expected = {
        'cw-window-candidate': '950107cb71eb13127175e9c5a29e3e387b74aac18e9a161f936c894aedf51072',
        'cw-receiver-v6.so': '40b489be4a6a299c5e7aa83d850138ffcffb122d4d1adc6ea46ed8ba9b69f7e1',
        'libcw-query-stdio.so': 'af1c407e4693447903283e800484e82bacf269dee8d6a72e21176e3e7b6fa9a7',
    }
    for name, wanted in expected.items():
        if digest(stable[name]) != wanted:
            raise SystemExit(f'Refusing changed stable artifact: {name}')

    controls = {
        'cw-window-candidate': stable['cw-window-candidate'],
        'cw-receiver-controls.so': (ROOT / 'build/qnx/libcw-porsche-capture_receiver.so').read_bytes(),
        'cw-rgi.so': (ROOT / 'build/qnx/libcw-porsche-rgi.so').read_bytes(),
        'libcw-query-stdio.so': stable['libcw-query-stdio.so'],
        'controls-launcher.sh': (ROOT / 'unit/dio_manager_controls.sh').read_bytes(),
        'lsd-controls.sh': (ROOT / 'unit/lsd_controls_watchdog.sh').read_bytes(),
        'PorscheCarPlayBridge.experimental.jar': (ROOT / 'build/PorscheCarPlayBridge.experimental.jar').read_bytes(),
    }
    stable_manifest = manifest(stable)
    controls_manifest = manifest(controls)
    manager = (ROOT / 'unit/carplay_profiles.sh').read_text(encoding='utf-8')
    manager = manager.replace('@STABLE_MANIFEST_SHA@', digest(stable_manifest))
    manager = manager.replace('@CONTROLS_MANIFEST_SHA@', digest(controls_manifest))
    manager = manager.replace('@VERIFIER_SHA@', expected['cw-window-candidate'])
    if '@' in manager:
        raise SystemExit('Unresolved manager placeholder')
    if re.search(r'(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{', manager):
        raise SystemExit('QNX-incompatible shell function syntax; use: function name {')

    menu = (ROOT / 'templates/OnlineMenu.esd').read_text(encoding='utf-8') + '''

# Porsche instrument cluster profiles
screen CarPlayProfiles OnlineMenu
script
   value sys 1 0x0100 "/scripts/online/carplay_profile_stable.sh"
   label "CarPlay: herstel bewezen Stable V14"
script
   value sys 1 0x0100 "/scripts/online/carplay_profile_controls.sh"
   label "CarPlay: test zoom en routepijlen (V15)"
script
   value sys 1 0x0100 "/scripts/online/carplay_profile_confirm.sh"
   label "CarPlay: bevestig werkende Controls V15"
script
   value sys 1 0x0100 "/scripts/online/carplay_profile_status.sh"
   label "CarPlay: status"
script
   value sys 1 0x0100 "/scripts/online/carplay_profile_oem.sh"
   label "CarPlay: volledig terug naar Porsche OEM"
'''
    wrappers = {
        'stable': 'install-stable', 'controls': 'install-controls',
        'confirm': 'confirm-controls', 'status': 'status', 'oem': 'restore-oem',
    }
    readme = '''Porsche MU1417 - CarPlay-profielen op SD
==========================================
Pak deze ZIP uit over de bestaande Online Menu-kaart en voer de normale
menu-update uit. Onder CarPlayProfiles staan vijf acties.

Stable V14 is de fysiek bewezen basis voor Apple Kaarten en Google Maps.
Controls V15 voegt de native kaartbediening en RGI-routegeleiding toe: zoomen
wordt semantisch naar de CarPlay-kaart gestuurd en manoeuvre-, rijstrook- en
straat-/volgende-wegdata worden aan de Porsche-routegeleidingsketen aangeboden. Deze uitgebreidere laag
is nog niet fysiek bevestigd. Daarom start de gewijzigde HMI precies eenmaal.
Zonder expliciete bevestiging gebruikt een volgende boot automatisch weer de
originele Porsche-HMI. Kies na een volledig geslaagde rit pas 'bevestig'.

'Stable V14' kan altijd vanuit het Online Menu over Controls heen worden gezet.
'Porsche OEM' herstelt zowel de originele HMI- als DIO-starter. Installaties
stoppen zonder wijzigingen als payload of OEM-back-ups niet exact kloppen.

De bestaande Porsche kaartmenu's worden niet verborgen: het instrumentenpaneel
opent die lokaal en de HU ontvangt het event pas daarna. Eerdere BAP-capability-
routes sluiten het menu aantoonbaar niet en kunnen wel de videolaag verbergen.

CarPlay-meldingen gebruiken het originele Porsche-popup- en speechkanaal. De
AppState-patch neutraliseert uitsluitend navigatie-eigendom. WhatsApp, Berichten,
Telegram en Flitsmeister kunnen alleen iets tonen of laten horen wanneer iOS en
de betreffende app dit voor CarPlay toestaan; de unit leest geen afgeschermde
iPhone-meldingen uit.
'''
    output = ROOT / 'build/porsche-carplay-profiles-MU1417.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
        def put(path: str, data: bytes, executable: bool = False) -> None:
            info = zipfile.ZipInfo(path, (2026, 11, 3, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

        put('install/scripts/carplay_profiles.sh', manager.encode(), True)
        for suffix, action in wrappers.items():
            body = f'#!/bin/sh\nBASE=${{0%/*}}\nexec /bin/sh "$BASE/carplay_profiles.sh" {action}\n'.encode()
            put(f'install/scripts/carplay_profile_{suffix}.sh', body, True)
        put('install/esd/OnlineMenu.esd', menu.encode())
        for name, data in stable.items():
            put(f'online/carplay-profiles/stable/{name}', data, name.endswith('.sh') or name == 'cw-window-candidate')
        put('online/carplay-profiles/stable/payload.manifest', stable_manifest)
        for name, data in controls.items():
            put(f'online/carplay-profiles/controls/{name}', data, name.endswith('.sh') or name == 'cw-window-candidate')
        put('online/carplay-profiles/controls/payload.manifest', controls_manifest)
        put('LEESMIJ-CARPLAY-PROFIELEN.txt', readme.encode('utf-8'))

    metadata = {'path': output.name, 'sha256': digest(output.read_bytes()), 'stable': digest(stable_manifest), 'controls': digest(controls_manifest)}
    (ROOT / 'build/profile-package.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(output)
    print(metadata['sha256'])


if __name__ == '__main__':
    main()
