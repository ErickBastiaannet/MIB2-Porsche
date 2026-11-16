"""User-mandated boundary: processing changes must leave known flow/map untouched."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_receiving_map_and_startup_boundary_is_unchanged():
    values=json.loads((ROOT/'tests/fixtures/guidance-processing-boundary.json').read_text())
    assert 'native/porsche_rgi_hook.c' in values and 'native/porsche_unit.c' in values
    for name,expected in values.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
