import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UnitQueryTest(unittest.TestCase):
    def run_fixture(self, missing=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mmx, sd = root / 'mmx', root / 'sd'
            sd.mkdir()
            dmdt = mmx / 'eso/bin/apps/dmdt'
            dmdt.parent.mkdir(parents=True)
            # Unknown commands fail: any accidentally introduced routing
            # command is a failing fixture, not an unnoticed hardware action.
            dmdt.write_text('''#!/bin/sh
case "$1" in
 gd) echo 'displaymanager knows 1 displayables:';;
 gc) echo 'displaymanager knows 1 contexts:';;
 gs) echo 'displaymanager reports the following system information:'
     echo 'display 4:'
     echo ' size: 960 x 640'
     echo ' context id: 72';;
 *) exit 9;;
esac
''', encoding='utf-8')
            if missing:
                dmdt.write_text(dmdt.read_text().replace(missing, 'missing header'))
            dmdt.chmod(0o755)
            (sd / 'libcw-query-stdio.so').write_bytes(b'fixture-not-loaded')
            hmi = mmx / 'ifs/lsd.jxe'
            hmi.parent.mkdir()
            hmi.write_bytes(b'unchanged-original')
            result = subprocess.run(['sh', str(ROOT / 'unit-query/read-unit.sh'), '--fixture-root', str(mmx), str(sd)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(hmi.read_bytes(), b'unchanged-original')
            reports = list(sd.glob('porsche-runtime-*'))
            self.assertEqual(len(reports), 1)
            self.assertEqual({p.name for p in reports[0].iterdir()}, {'gd.txt', 'gc.txt', 'gs.txt', 'unit.txt'})
            return result

    def test_complete(self):
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('size: 960 x 640', result.stdout)
        self.assertIn('COMPLETE:', result.stdout)

    def test_missing_system_response(self):
        result = self.run_fixture('displaymanager reports the following system information:')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INCOMPLETE:', result.stdout)


if __name__ == '__main__':
    unittest.main()
