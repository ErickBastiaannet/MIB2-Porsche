import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeProfileTest(unittest.TestCase):
    def test_other_library_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library, output = root / 'wrong.so', root / 'report.json'
            library.write_bytes(b'not the MU1417 AirPlay library')
            result = subprocess.run([sys.executable, str(ROOT / 'build-tools/verify_native.py'),
                                     str(library), '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unrecognised AirPlay library', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
