import hashlib
from pathlib import Path
import struct
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'build/porsche-carplay-native-MU1417-candidate.zip'


@unittest.skipUnless(PACKAGE.exists(), 'Build SD package first')
class PackageTest(unittest.TestCase):
    def test_complete_sd_overlay_has_only_porsche_payload(self):
        with zipfile.ZipFile(PACKAGE) as archive:
            names=archive.namelist()
            self.assertEqual(len(names),len(set(names)))
            self.assertFalse(any('..' in Path(name).parts or name.startswith('/') for name in names))
            self.assertFalse(any(name.endswith(('server-ip.txt','ca-bundle.crt','metainfo2.txt')) for name in names))
            manifest=archive.read('online/carplay/payload.manifest')
            self.assertEqual({line.split(' ',1)[1] for line in manifest.decode().splitlines()}, {
                'porsche-carplay', 'libcw-porsche-capture_receiver.so',
                'libcw-porsche-rgi.so', 'libcw-query-stdio.so', 'dio_manager.sh',
            })
            self.assertNotIn('online/carplay/lsd.sh', names)
            self.assertNotIn('online/carplay/ConnectWowCarPlay.jar', names)
            script=archive.read('install/scripts/carplay_manage.sh').decode()
            self.assertIn(hashlib.sha256(manifest).hexdigest(),script)
            for line in manifest.decode().splitlines():
                expected,name=line.split(' ',1)
                self.assertEqual(hashlib.sha256(archive.read('online/carplay/'+name)).hexdigest(),expected)
            for action in ['install','status','enable','disable','restore']:
                self.assertIn('install/scripts/carplay_'+action+'.sh', names)
            elf=archive.read('online/carplay/porsche-carplay')
            self.assertEqual(elf[:7], b'\x7fELF\x01\x01\x01')
            self.assertEqual(struct.unpack_from('<H',elf,18)[0],40)
            self.assertIn(b'/usr/lib/ldqnx.so.2\0',elf)
            self.assertNotIn(b'/tmp/cw-runtime',elf)
