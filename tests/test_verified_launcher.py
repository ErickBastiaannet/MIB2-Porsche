from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class VerifiedLauncherRegressionTest(unittest.TestCase):
    def test_runtime_opt_in_marker_is_created_before_supervisor_starts(self):
        source = (ROOT / 'unit/dio_manager_verified_test.sh').read_text()
        marker = 'echo enabled > "$CW_ROOT/enabled"'
        prime = '"$CW_ROOT/cw-window-candidate" --prime-geometry'
        supervisor = '"$CW_ROOT/cw-window-candidate" --run'
        self.assertIn(marker, source)
        self.assertLess(source.index(marker), source.index(prime))
        self.assertLess(source.index(marker), source.index(supervisor))

    def test_renderer_waits_for_stable_stream_and_ready_cluster(self):
        source = (ROOT / 'unit/dio_manager_verified_test.sh').read_text()
        supervisor = 'exec "$CW_ROOT/cw-window-candidate" --run'
        for requirement in (
            '[ -s "$CW_SOURCE_READY" ]',
            '[ -s "$CW_RING" ]',
            '"$CW_ROOT/cw-window-candidate" --inspect',
            "grep 'context=72'",
            '[ "$CW_STABLE" -ge 3 ]',
            'kill -0 "$CW_CHILD"',
        ):
            self.assertIn(requirement, source)
            self.assertLess(source.index(requirement), source.index(supervisor))


if __name__ == '__main__':
    unittest.main()
