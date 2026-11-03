"""Build the persistent SD package for the physically verified v14 path."""
import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def online_menu_source() -> Path:
    """Resolve the Online Menu template after this tool became its own repo."""
    configured = os.environ.get('CONNECTWOW_ONLINE_MENU_ESD')
    candidates = [
        Path(configured) if configured else None,
        ROOT / 'templates/OnlineMenu.esd',
        ROOT.parent / 'mqb-backend-private/resources/online-setup/source/install/esd/OnlineMenu.esd',
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise SystemExit(
        'OnlineMenu.esd not found; set CONNECTWOW_ONLINE_MENU_ESD or add templates/OnlineMenu.esd'
    )


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    verified = ROOT / 'verified/v14'
    files = {
        'cw-window-candidate': (verified / 'cw-window-candidate').read_bytes(),
        'cw-receiver-v6.so': (verified / 'cw-receiver-v6.so').read_bytes(),
        'libcw-query-stdio.so': (verified / 'libcw-query-stdio.so').read_bytes(),
        'dio_manager_verified_test.sh': (ROOT / 'unit/dio_manager_verified_test.sh').read_bytes(),
    }
    expected = {
        'cw-window-candidate': '950107cb71eb13127175e9c5a29e3e387b74aac18e9a161f936c894aedf51072',
        'cw-receiver-v6.so': '40b489be4a6a299c5e7aa83d850138ffcffb122d4d1adc6ea46ed8ba9b69f7e1',
        'libcw-query-stdio.so': 'af1c407e4693447903283e800484e82bacf269dee8d6a72e21176e3e7b6fa9a7',
    }
    for name, digest in expected.items():
        if sha(files[name]) != digest:
            raise SystemExit(f'Refusing to package non-v14 artifact: {name}')
    manifest = ''.join(f'{sha(data)} {name}\n' for name, data in files.items()).encode()
    entry = (ROOT / 'unit/carplay_verified_test.sh').read_bytes()
    menu = online_menu_source().read_text(encoding='utf-8')
    menu += '''

# Switchable Porsche MU1417 CarPlay test; automatically restores OEM DIO
screen CarPlayTest OnlineMenu
script
   value sys 1 0x0100 "/scripts/online/carplay_verified_enable.sh"
   label "CarPlay instrumentenscherm inschakelen"
script
   value sys 1 0x0100 "/scripts/online/carplay_verified_disable.sh"
   label "CarPlay instrumentenscherm uitschakelen"
script
   value sys 1 0x0100 "/scripts/online/carplay_verified_status.sh"
   label "CarPlay status en laatste logs"
'''
    readme = '''ConnectWow Porsche CarPlay - schakelbare v14-test
=================================================
Pak deze ZIP uit OVER de bestaande Online Menu-SD-kaart en kies eerst de
bestaande menu-updatefunctie. Start daarna een route in Apple Kaarten. Trek USB
volledig los en wacht totdat CarPlay op de PCM gesloten is. Open pas daarna
CarPlayTest en kies CarPlay instrumentenscherm inschakelen. Sluit USB vervolgens
opnieuw aan. Deze volgorde is onderdeel van de bewezen v14-
proef: een reeds draaiende CarPlay-sessie passeert de tijdelijke starter niet.

Dit reproduceert de sessie die op de fysieke Panamera CARPLAY_ACTIVE gaf met
een geldige 800x480-videostroom. De HMI/Java-bestanden worden niet gewijzigd.
Vooraf worden bekende eerdere ConnectWow-startwijzigingen gecontroleerd terug-
gezet naar de OEM DIO- en HMI-back-ups. Beide back-ups moeten exact overeenkomen
met de vastgelegde K5137/MU1417-checksums; anders stopt het script zonder proef.
Na eenmalig inschakelen blijft de geverifieerde starter actief voor volgende
ritten. Runtimebestanden en uitgebreide logs staan in RAM. Alleen een begrensde
samenvatting van de laatste sessie wordt persistent bewaard. Uitschakelen zet de
originele Porsche DIO terug; payload en diagnostiek blijven beschikbaar.
Apple Kaarten en Google Maps zijn beide fysiek werkend bevestigd.
'''
    archive = ROOT / 'build/porsche-carplay-v14-switchable-MU1417.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        def put(path: str, data: bytes, executable: bool = False) -> None:
            info = zipfile.ZipInfo(path, (2026, 11, 3, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
        enable = b'#!/bin/sh\nBASE=${0%/*}\nexec /bin/sh "$BASE/carplay_verified_test.sh" enable\n'
        disable = b'#!/bin/sh\nBASE=${0%/*}\nexec /bin/sh "$BASE/carplay_verified_test.sh" disable\n'
        status = b'#!/bin/sh\nBASE=${0%/*}\nexec /bin/sh "$BASE/carplay_verified_test.sh" status\n'
        put('install/scripts/carplay_verified_test.sh', entry, True)
        put('install/scripts/carplay_verified_enable.sh', enable, True)
        put('install/scripts/carplay_verified_disable.sh', disable, True)
        put('install/scripts/carplay_verified_status.sh', status, True)
        put('install/esd/OnlineMenu.esd', menu.encode())
        for name, data in files.items():
            put(f'online/carplay-verified/{name}', data, name != 'cw-receiver-v6.so')
        put('online/carplay-verified/payload.manifest', manifest)
        put('LEESMIJ-CARPLAY-V14.txt', readme.encode('utf-8'))
    metadata = {'path': archive.name, 'sha256': sha(archive.read_bytes()), 'mode': 'v14-persistent-switchable'}
    (ROOT / 'build/verified-test-package.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(archive)
    print(metadata['sha256'])


if __name__ == '__main__':
    main()
