import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SplitBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, ROOT / "build-tools/split_hmi_bridge.py"], check=True)

    def test_feature_jars_do_not_overlap_oem_classes(self):
        manifest = json.loads((ROOT / "build/split-hmi-manifest.json").read_text())
        owners = {}
        for filename, details in manifest.items():
            with zipfile.ZipFile(ROOT / "build" / filename) as jar:
                self.assertEqual(set(details["classes"]), set(jar.namelist()))
            for name in details["classes"]:
                if name.startswith(("de/audi/", "org/dsi/")):
                    self.assertNotIn(name, owners, f"OEM class occurs in {owners.get(name)} and {filename}")
                    owners[name] = filename

    def test_guidance_jar_has_only_one_oem_hook(self):
        with zipfile.ZipFile(ROOT / "build/PorscheCarPlayGuidance.experimental.jar") as jar:
            oem = [name for name in jar.namelist() if name.startswith("de/audi/")]
        self.assertEqual(oem, [
            "de/audi/tghu/navi/app/cluster/ClusterService.class",
            "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance$1.class",
            "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance$State.class",
            "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.class",
        ])


if __name__ == "__main__":
    unittest.main()
