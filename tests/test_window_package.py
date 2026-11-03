import hashlib
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'build/porsche-window-selftest.zip'


@unittest.skipUnless(PACKAGE.exists(), 'Build window diagnostic first')
class WindowPackageTest(unittest.TestCase):
    def test_diagnostic_contains_no_installation_payload_and_checks_every_binary(self):
        with zipfile.ZipFile(PACKAGE) as archive:
            prefix = 'porsche-window-test/'
            self.assertEqual(set(archive.namelist()), {prefix + name for name in [
                'porsche-carplay', 'cw-window-selftest', 'libcw-query-stdio.so',
                'window-selftest.sh', 'LEESMIJ.txt', 'manifest.json',
            ]})
            manifest = json.loads(archive.read(prefix + 'manifest.json'))
            self.assertFalse(manifest['carplay_installer'])
            self.assertFalse(manifest['physical_unit_verified'])
            for name, expected in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(prefix + name)).hexdigest(), expected)
            launcher = archive.read(prefix + 'window-selftest.sh').decode()
            for name in ['porsche-carplay', 'cw-window-selftest', 'libcw-query-stdio.so']:
                self.assertIn(manifest['files'][name], launcher)
            self.assertNotIn('@TOOL_SHA@', launcher)
            self.assertNotIn('mount -uw', launcher)
            self.assertNotIn('reboot', launcher)
            self.assertIn('--window-selftest', launcher)
