import hashlib
from pathlib import Path

import pytest

from build_tools_probe import load_probe_builder


def test_probe_builder_preserves_oem_and_adds_only_guarded_ticket(tmp_path):
    module = load_probe_builder()
    source = tmp_path / "lsd.sh"
    source.write_bytes(module.fixture_oem())
    module.OEM_SHA256 = hashlib.sha256(source.read_bytes()).hexdigest()
    target = tmp_path / "probe.sh"
    module.build(source, target, "/probe/zoom.jar", "/persist/zoom")
    text = target.read_text("ascii")
    assert text.count(module.MARKER) == 1
    assert '-s "$CW_PROBE_STATE/confirmed"' in text
    assert 'mv "$CW_PROBE_STATE/pending" "$CW_PROBE_STATE/attempted"' in text
    assert 'CW_PROBE_ENABLE=1' in text
    assert '-Xbootclasspath/p:$CW_PROBE_JAR' in text
    assert "exec /bin/ksh" not in text
    assert len(target.read_bytes()) > len(source.read_bytes())


def test_probe_builder_rejects_unknown_stock(tmp_path):
    module = load_probe_builder()
    source = tmp_path / "lsd.sh"
    source.write_text("not OEM")
    with pytest.raises(SystemExit):
        module.build(source, tmp_path / "out", "/x", "/y")


def test_probe_builder_adds_one_shot_extra_probe_without_confirming_it(tmp_path):
    module = load_probe_builder()
    source = tmp_path / "lsd.sh"
    source.write_bytes(module.fixture_oem())
    module.OEM_SHA256 = hashlib.sha256(source.read_bytes()).hexdigest()
    target = tmp_path / "probe.sh"
    module.build(source, target, "/probe/zoom.jar", "/persist/zoom",
                 "/probe/guidance.jar", "/persist/guidance")
    text = target.read_text("ascii")
    assert 'CW_EXTRA_PROBE_JAR="/probe/guidance.jar"' in text
    assert 'mv "$CW_EXTRA_PROBE_STATE/pending" "$CW_EXTRA_PROBE_STATE/attempted"' in text
    assert '[ -s "$CW_EXTRA_PROBE_STATE/confirmed" ]' in text
    assert 'CW_EXTRA_PROBE_ENABLE=1' in text
