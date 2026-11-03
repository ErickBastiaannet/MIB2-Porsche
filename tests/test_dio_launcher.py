"""Exercise stock fallback in the real native-only DIO launcher."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cw-launcher-')
        self.root = Path(self.temp.name)
        self.install = self.root/'install'
        self.install.mkdir()
        self.stock = self.root/'stock'
        self.stock.write_text('''#!/bin/sh
if [ "${CARPLAY_ALTSCREEN_ENABLE:-}" = 1 ]; then
    echo CAPTURE_ATTEMPT
    exit 17
fi
echo STOCK_DIO
exit 0
''')
        self.stock.chmod(0o755)
        self.supervisor = self.install/'porsche-carplay'
        self.supervisor.write_text('#!/bin/sh\nexit 0\n')
        self.supervisor.chmod(0o755)
        (self.install/'installed.manifest').write_text('fixture\n')
        source = (ROOT/'unit/dio_manager.sh').read_text()
        source = source.replace('/mnt/app/eso/hmi/connectwow-carplay', str(self.install))
        source = source.replace('/mnt/app/eso/bin/apps/dio_manager.cw-stock', str(self.stock))
        source = source.replace('/ramdisk/', str(self.root)+'/')
        self.script = self.root/'launch.sh'
        self.script.write_text(source)

    def tearDown(self):
        self.temp.cleanup()

    def run_launcher(self):
        env = dict(os.environ)
        env.pop('LD_PRELOAD', None)
        result = subprocess.run(['/bin/sh', str(self.script)], env=env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return result.stdout

    def test_failed_capture_retries_stock_and_allows_next_phone_session(self):
        self.assertEqual(self.run_launcher(), 'CAPTURE_ATTEMPT\nSTOCK_DIO\n')
        self.assertFalse((self.root/'cw-porsche-native-attempted').exists())
        self.assertEqual(self.run_launcher(), 'CAPTURE_ATTEMPT\nSTOCK_DIO\n')

    def test_no_installation_uses_stock_directly(self):
        (self.install/'installed.manifest').unlink()
        self.assertEqual(self.run_launcher(), 'STOCK_DIO\n')
        self.assertFalse((self.root/'cw-porsche-native-attempted').exists())

    def test_failed_geometry_priming_never_starts_capture(self):
        self.supervisor.write_text('''#!/bin/sh
if [ "$1" = --prime-geometry ]; then exit 19; fi
exit 0
''')
        self.assertEqual(self.run_launcher(), 'STOCK_DIO\n')

    def test_normal_disconnect_allows_next_phone_connection(self):
        self.stock.write_text('''#!/bin/sh
if [ "${CARPLAY_ALTSCREEN_ENABLE:-}" = 1 ]; then
    echo CAPTURE_NORMAL_DISCONNECT
    exit 0
fi
echo STOCK_DIO
exit 0
''')
        self.assertEqual(self.run_launcher(), 'CAPTURE_NORMAL_DISCONNECT\n')
        self.assertFalse((self.root/'cw-porsche-native-attempted').exists())
        self.assertEqual(self.run_launcher(), 'CAPTURE_NORMAL_DISCONNECT\n')

    def test_missing_supervisor_uses_stock_directly(self):
        self.supervisor.unlink()
        self.assertEqual(self.run_launcher(), 'STOCK_DIO\n')
