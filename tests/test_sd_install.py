"""Execute the real SD shell workflow against a disposable Linux filesystem.

Only firmware verification is substituted: Linux cannot execute the QNX ELF.
Hashes, backups, file writes, rollback and launchers are exercised by /bin/sh.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STOCK = b'original DIO executable fixture\n'
LSD = b'#!/bin/sh\nVMOPTIONS="$VMOPTIONS -Xquickstart"\n'


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cw-sd-fixture-')
        self.root = Path(self.temporary.name)
        (self.root / '.cw-fixture').touch()
        self.payload = self.root / 'fs/sda0/online/carplay'
        self.payload.mkdir(parents=True)
        self.dio = self.root / 'mnt/app/eso/bin/apps/dio_manager'
        self.lsd = self.root / 'mnt/app/eso/hmi/lsd/lsd.sh'
        for target, data in [(self.dio, STOCK), (self.lsd, LSD)]:
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data); target.chmod(0o755)
        self.install = self.root / 'mnt/app/eso/hmi/connectwow-carplay'
        tool = self.payload / 'porsche-carplay'
        tool.write_text('''#!/usr/bin/env python3
import hashlib, sys
from pathlib import Path
if sys.argv[1] == '--hash':
    try: print(hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest())
    except OSError: sys.exit(1)
elif sys.argv[1] == '--check-firmware': sys.exit(0)
elif sys.argv[1] == '--check-jar': sys.exit(1 if b'CONFLICT' in Path(sys.argv[2]).read_bytes() else 0)
else: sys.exit(2)
''')
        tool.chmod(0o755)
        for name in ['libcw-porsche-capture_receiver.so', 'libcw-porsche-rgi.so', 'libcw-query-stdio.so']:
            (self.payload / name).write_bytes(b'fixture '+name.encode())
        for name in ['dio_manager.sh']:
            (self.payload / name).write_bytes((ROOT / 'unit' / name).read_bytes())
        manifest=''.join(hashlib.sha256(path.read_bytes()).hexdigest()+' '+path.name+'\n'
                         for path in sorted(self.payload.iterdir()))
        (self.payload / 'payload.manifest').write_text(manifest)
        script=(ROOT / 'unit/carplay_manage.sh').read_text()
        script=script.replace('@VERIFIER_SHA256@', hashlib.sha256(tool.read_bytes()).hexdigest())
        script=script.replace('@MANIFEST_SHA256@', hashlib.sha256(manifest.encode()).hexdigest())
        script=script.replace('9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8', hashlib.sha256(STOCK).hexdigest())
        script=script.replace('7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091', hashlib.sha256(LSD).hexdigest())
        self.script=self.root/'manage.sh'; self.script.write_text(script)

    def tearDown(self):
        self.temporary.cleanup()

    def run_action(self, action, expected=0, env=None, ksh_aliases=False):
        arguments=[str(self.script), action, '--fixture-root', str(self.root)]
        runner=[os.environ.get('CW_SD_TEST_SHELL', '/bin/sh')]
        if ksh_aliases:
            runner=['/bin/bash', '-O', 'expand_aliases', '-c',
                    "alias hash='alias -t'\n. \"$@\"\n", 'cw-shell-fixture']
        result=subprocess.run(runner+arguments,
                              capture_output=True, text=True, timeout=15, env=env)
        self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
        return result.stdout

    def test_qnx_hash_alias_regression(self):
        # QNX ksh defines hash='alias -t' before parsing functions. Reproduce
        # that parser condition, including a negative control of the old bug.
        corrected=self.script.read_text()
        self.script.write_text(corrected.replace('cw_sha256', 'hash'))
        self.run_action('install', expected=2, ksh_aliases=True)
        self.assertFalse(self.install.exists())
        self.assertEqual(self.dio.read_bytes(), STOCK)
        self.script.write_text(corrected)
        self.run_action('install', ksh_aliases=True)
        self.run_action('restore', ksh_aliases=True)
        self.assertEqual(self.dio.read_bytes(), STOCK)
        self.assertEqual(self.lsd.read_bytes(), LSD)

    def test_install_idempotence_selection_restore(self):
        self.run_action('install')
        self.assertEqual((self.install/'backup/dio_manager').read_bytes(), STOCK)
        self.assertEqual(self.dio.read_bytes(), (ROOT/'unit/dio_manager.sh').read_bytes())
        self.assertEqual(self.lsd.read_bytes(), LSD)
        self.assertFalse((self.install/'ConnectWowCarPlay.jar').exists())
        self.assertIn('already installed', self.run_action('install'))
        self.run_action('disable'); self.assertFalse((self.install/'enabled').exists())
        self.run_action('enable'); self.assertTrue((self.install/'enabled').exists())
        self.assertIn('Selected: CarPlay', self.run_action('status'))
        self.run_action('restore')
        self.assertEqual(self.dio.read_bytes(), STOCK); self.assertEqual(self.lsd.read_bytes(), LSD)
        self.assertFalse((self.install/'installed.manifest').exists())
        self.assertTrue((self.install/'backup/dio_manager').is_file())

    def test_corrupt_payload_changes_nothing(self):
        (self.payload/'libcw-porsche-capture_receiver.so').write_bytes(b'corrupt')
        self.run_action('install', 1)
        self.assertEqual(self.dio.read_bytes(), STOCK); self.assertFalse(self.install.exists())

    def test_unknown_hmi_prepend_is_untouched(self):
        modified=LSD+b'VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:other.jar"\n'
        self.lsd.write_bytes(modified)
        self.run_action('install')
        self.assertEqual(self.lsd.read_bytes(), modified)
        self.run_action('restore')

    def test_existing_java_jar_is_untouched(self):
        jars=self.lsd.parent/'jars'; jars.mkdir(); (jars/'other.jar').write_bytes(b'CONFLICT')
        self.run_action('install')
        self.assertEqual((jars/'other.jar').read_bytes(), b'CONFLICT')
        self.assertEqual(self.lsd.read_bytes(), LSD)
        self.run_action('restore')

    def test_migration_accepts_restored_stock_backups(self):
        (self.install/'backup').mkdir(parents=True)
        (self.install/'backup/dio_manager').write_bytes(STOCK)
        self.dio.with_name('dio_manager.cw-stock').write_bytes(STOCK)
        self.run_action('install')
        self.assertEqual(self.lsd.read_bytes(), LSD)
        self.run_action('restore')
        self.assertEqual(self.dio.read_bytes(), STOCK)

    def test_existing_hmi_patch_is_outside_native_only_scope(self):
        self.lsd.write_bytes(LSD+b'connectwow-carplay\n')
        self.run_action('install')
        self.assertEqual(self.lsd.read_bytes(), LSD+b'connectwow-carplay\n')
        self.run_action('restore')

    def test_restore_refuses_external_changes(self):
        self.run_action('install'); self.dio.write_bytes(b'external change')
        self.run_action('restore', 1)
        self.assertEqual(self.dio.read_bytes(), b'external change')
        self.assertTrue((self.install/'installed.manifest').exists())

    def test_failed_launcher_staging_rolls_back(self):
        commands=self.root/'commands'; commands.mkdir()
        cp=commands/'cp'
        cp.write_text('#!/bin/sh\nfor arg in "$@"; do case "$arg" in *.cw-new) '
                      'exit 1;; esac; done\nexec /bin/cp "$@"\n')
        cp.chmod(0o755); env=dict(os.environ, PATH=str(commands)+':'+os.environ['PATH'])
        self.assertIn('restoring original launchers', self.run_action('install', 1, env))
        self.assertEqual(self.dio.read_bytes(), STOCK); self.assertEqual(self.lsd.read_bytes(), LSD)
        self.assertFalse((self.install/'installed.manifest').exists())


if __name__ == '__main__':
    unittest.main()
