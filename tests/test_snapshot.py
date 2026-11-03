import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'build-tools/read_snapshot.py'
spec = importlib.util.spec_from_file_location('read_snapshot', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SYNTHETIC = '''displaymanager reports the following system information:
display 0:
 name: main
 terminal: main
 size: 1440 x 540
 context id: 78
display 1:
 name: cluster
 terminal: 2nd_lvds
 size: 800 x 480
 context id: 72
'''


class SnapshotTest(unittest.TestCase):
    def test_cluster_selected_instead_of_central_pcm(self):
        result = module.read_cluster(SYNTHETIC)
        self.assertEqual((result['width'], result['height']), (800, 480))
        self.assertEqual(result['report_display_index'], 1)
        self.assertFalse(result['carplay_output_proven'])

    def test_no_cluster_no_fallback(self):
        with self.assertRaises(ValueError):
            module.read_cluster(SYNTHETIC.split('display 1:')[0])

    def test_duplicate_cluster_rejected(self):
        with self.assertRaises(ValueError):
            module.read_cluster(SYNTHETIC + 'display 7:\n terminal: 2nd_lvds\n size: 800 x 298\n context id: 72\n')

    def test_partial_response_rejected(self):
        with self.assertRaises(ValueError):
            module.read_cluster(SYNTHETIC.replace(' size: 800 x 480\n', ''))

    def test_report_index_is_not_a_hardcoded_java_dsi_id(self):
        result = module.read_cluster(SYNTHETIC.replace('display 1:', 'display 7:'))
        self.assertEqual(result['report_display_index'], 7)

    def test_unnamed_display_is_rejected(self):
        with self.assertRaises(ValueError):
            module.read_cluster(SYNTHETIC.replace(' terminal: 2nd_lvds\n', ''))


if __name__ == '__main__':
    unittest.main()
