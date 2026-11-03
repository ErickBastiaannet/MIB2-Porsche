"""Build a non-installing SD/RAM field-test overlay for Porsche MU1417."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent

def sha(data): return hashlib.sha256(data).hexdigest()

files = {
    'porsche-carplay': (ROOT/'build/qnx/porsche-carplay-window-candidate').read_bytes(),
    'libcw-porsche-capture_receiver.so': (ROOT/'build/qnx/libcw-porsche-capture_receiver.so').read_bytes(),
    'libcw-porsche-rgi.so': (ROOT/'build/qnx/libcw-porsche-rgi.so').read_bytes(),
    'libcw-query-stdio.so': (ROOT/'build/qnx/libcw-query-stdio.so').read_bytes(),
}
manifest = ''.join(f'{sha(data)} {name}\n' for name,data in files.items()).encode()
files['payload.manifest'] = manifest
menu = (REPO/'resources/online-setup/source/install/esd/OnlineMenu.esd').read_text(encoding='utf-8')
menu += '\n# ConnectWow bounded Porsche RAM test\nscreen CarPlayRAM OnlineMenu\n'
menu += '\nscript\n   value sys 1 0x0100 "/scripts/online/carplay_ram_test.sh"\n   label "Start CarPlay RAM-test (60 sec)"\n'
readme = '''ConnectWow Porsche CarPlay RAM-test - K5137/MU1417
=====================================================
Pak deze ZIP uit over de bestaande Online Menu-SD-kaart en werk daarna het
Online Menu bij. Kies CarPlayRAM > Start CarPlay RAM-test (60 sec), verbind de
iPhone en open Apple Kaarten. Er wordt niets naar /mnt/app geschreven.
Resultaten staan na afloop in /connectwow-carplay-logs/latest/ op de SD-kaart.
Voorwaarde: de originele DIO-back-up dio_manager.cw-stock bestaat op de unit.
'''.encode()
meta = json.dumps({'firmware':'MHI2_ER_POG24_K5137_MU1417','mode':'RAM only','timeout_seconds':60,
                   'writes_app_volume':False,'payload':{n:sha(d) for n,d in files.items()}},indent=2).encode()
out=ROOT/'build/porsche-carplay-RAM-test-MU1417.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    def put(name,data,mode=0o100644):
        i=zipfile.ZipInfo(name,(2026,11,3,0,0,0));i.create_system=3;i.external_attr=mode<<16;i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
    put('install/scripts/carplay_ram_test.sh',(ROOT/'unit/carplay_ram_test.sh').read_bytes(),0o100755)
    put('install/esd/OnlineMenu.esd',menu.encode())
    for name,data in files.items(): put('online/carplay-ram/'+name,data,0o100755 if name=='porsche-carplay' else 0o100644)
    put('LEESMIJ-RAM-TEST.txt',readme);put('online/carplay-ram/build-info.json',meta)
print(out)
