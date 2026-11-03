"""Package an isolated compositor registration test; never a CarPlay installer."""
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    for manifest in ['build/qnx/sources.sha256', 'build/qnx/artifacts.sha256']:
        for line in (ROOT / manifest).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            if sha((ROOT / name).read_bytes()) != expected:
                raise SystemExit('Stale build; rebuild QNX binaries: ' + name)
    files = {name: (ROOT / 'build/qnx' / name).read_bytes() for name in [
        'porsche-carplay', 'cw-window-selftest', 'libcw-query-stdio.so',
    ]}
    for name, data in files.items():
        if (data[:7] != b'\x7fELF\x01\x01\x01' or
                struct.unpack_from('<H', data, 18)[0] != 40 or
                struct.unpack_from('<I', data, 36)[0] >> 24 != 5):
            raise SystemExit('Invalid QNX ARM EABI5 payload: ' + name)
    launcher = (ROOT / 'unit-query/window-selftest.sh').read_text()
    for marker, name in [('TOOL', 'porsche-carplay'), ('TEST', 'cw-window-selftest'),
                         ('QUERY', 'libcw-query-stdio.so')]:
        launcher = launcher.replace('@' + marker + '_SHA@', sha(files[name]))
    files['window-selftest.sh'] = launcher.encode()
    files['LEESMIJ.txt'] = '''Porsche MU1417 - venstercontrole, GEEN CarPlay-installatie
========================================================
Deze nieuwe renderroute is lokaal getest en voor QNX gebouwd. Hij is nog
niet op de Porsche beproefd. De eerdere directe videostreamtest toonde
geen beeld en is ingetrokken.

Pak de map porsche-window-test uit op de bestaande online-menu-SD.
Laat de originele kaart rechts zien en gebruik de bestaande console:
  sh /net/mmx/fs/sda0/porsche-window-test/window-selftest.sh
Als de SD in een ander slot zit, pas alleen het SD-mountpad aan.

De test maakt kort een eigen grafisch venster op laag 78, controleert
de KD-, EGL- en displaymanagerafmetingen en ruimt het venster weer op.
Hij schakelt de kaart NIET om: verwacht nog geen zichtbaar testbeeld.
Geslaagd: WINDOW_SELFTEST_PASS_CONTEXT_UNCHANGED.

Er worden geen startbestanden vervangen, geen JARs geplaatst en geen
hosts, certificaten of firmware-instellingen gewijzigd. Geen herstart.
Voer alleen uit als de auto stilstaat. Bij een afwijzing: bewaar de
consolemelding; probeer geen andere firmwarevariant of geforceerde route.
'''.encode('utf-8')
    files['manifest.json'] = (json.dumps({
        'purpose': 'compositor-window registration test; no display routing',
        'carplay_installer': False,
        'physical_unit_verified': False,
        'files': {name: sha(data) for name, data in files.items()},
    }, indent=2) + '\n').encode()
    destination = ROOT / 'build/porsche-window-selftest.zip'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            item = zipfile.ZipInfo('porsche-window-test/' + name, (2026, 11, 2, 0, 0, 0))
            item.create_system = 3
            item.external_attr = (0o100755 if name.endswith('.sh') or name in [
                'porsche-carplay', 'cw-window-selftest'] else 0o100644) << 16
            archive.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)
    print('WINDOW_DIAGNOSTIC_PACKAGE', destination)
    print('SHA256', sha(destination.read_bytes()))


if __name__ == '__main__':
    main()
