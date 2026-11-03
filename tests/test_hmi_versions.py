import importlib.util
import io
from pathlib import Path
import struct
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sd_builder', ROOT / 'build-tools/build_sd_zip.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def archive(major):
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as jar:
        jar.writestr('org/connectwow/carplay/PorscheGeometry.class',
                     struct.pack('>IHHH', 0xcafebabe, 0, 46, 1))
        jar.writestr('de/audi/tghu/fwhmi/DisplayManagerMIB2High.class',
                     struct.pack('>IHHH', 0xcafebabe, 0, major, 1))
    return result.getvalue()


class HmiVersionsTest(unittest.TestCase):
    def test_native_only_package_does_not_modify_java_or_hmi(self):
        self.assertEqual(set(builder.FILES), {
            'porsche-carplay', 'libcw-porsche-capture_receiver.so',
            'libcw-porsche-rgi.so', 'libcw-query-stdio.so', 'dio_manager.sh',
        })
        self.assertNotIn('lsd.sh', builder.FILES)
        self.assertNotIn('ConnectWowCarPlay.jar', builder.FILES)

    def test_helper_46_does_not_hide_incompatible_oem_override(self):
        with self.assertRaisesRegex(ValueError, '49.*maximum 48.*DisplayManagerMIB2High'):
            builder.validate_hmi_class_versions(archive(49))

    def test_version_48_passes_version_gate_only(self):
        # Header compatibility is necessary, not proof of valid/working bytecode.
        builder.validate_hmi_class_versions(archive(48))

    def test_withdrawn_real_artifact_is_rejected(self):
        withdrawn = ROOT / 'build/DO-NOT-INSTALL-porsche-carplay-MU1417-WITHDRAWN.zip'
        if not withdrawn.exists():
            self.skipTest('Withdrawn local artifact not present')
        with zipfile.ZipFile(withdrawn) as archive_file:
            data = archive_file.read('online/carplay/ConnectWowCarPlay.jar')
        with self.assertRaisesRegex(ValueError, 'version 49'):
            builder.validate_hmi_class_versions(data)
