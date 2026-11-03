"""Package a read-only SD query, not a CarPlay installer."""
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
helper = ROOT / 'build/qnx/libcw-query-stdio.so'
binary = helper.read_bytes()
if binary[:6] != b'\x7fELF\x01\x01' or struct.unpack_from('<HH', binary, 16) != (3, 40):
    raise SystemExit('Query helper is not a little-endian ARM ELF32 shared library')
flags = struct.unpack_from('<I', binary, 36)[0]
if flags >> 24 != 5:
    raise SystemExit('Query helper has the wrong EABI version')
instructions = '''Porsche runtime-uitlezing — GEEN CarPlay-installatie
==================================================
1. Pak de ZIP uit in een map porsche-runtime op de SD-kaart.
2. Zet de oorspronkelijke Porsche-kaart zichtbaar in het rechter instrumentenscherm.
3. Voer vanuit de bestaande console uit:
   sh /net/mmx/fs/sda0/porsche-runtime/read-unit.sh

Dit pad geldt voor de MMX SD-mount die we eerder gebruikten. Staat de kaart
op een andere mount, gebruik dan daar hetzelfde script met het volledige pad.

Het script vraagt dmdt alleen om gd, gc en gs: bestaande vensters, contexten,
schermformaten en de actieve context. De helper maakt alleen de uitvoer van
dit korte diagnoseproces zichtbaar en begrenst elke aanvraag op tien seconden.

Het schermformaat wordt op de console getoond. De volledige resultaten komen
op de SD-kaart in porsche-runtime-<procesnummer>. Het belangrijkste bestand
voor het formaat is gs.txt. Er wordt geen firmwaredump gemaakt.

Er worden geen JARs geïnstalleerd, geen kaartcontexten gewisseld, geen
certificaten/hosts gewijzigd en geen processen van de navigatie herstart.
Dit pakket kan nog GEEN CarPlay op het instrumentenscherm tonen.
'''
files = {
    'read-unit.sh': (ROOT / 'unit-query/read-unit.sh').read_bytes(),
    'libcw-query-stdio.so': binary,
    'source/query_stdio.c': (ROOT / 'unit-query/query_stdio.c').read_bytes(),
    'LEESMIJ.txt': instructions.encode('utf-8'),
}
manifest = {'purpose': 'read-only runtime query', 'carplay_installer': False,
            'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode('utf-8')
destination = ROOT / 'build/porsche-runtime-query.zip'
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in files.items():
        item = zipfile.ZipInfo(name, (2026, 10, 28, 0, 0, 0))
        item.external_attr = (0o100755 if name.endswith(('.so', '.sh')) else 0o100644) << 16
        archive.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)
print('READ_ONLY_QUERY_PACKAGE', destination)
