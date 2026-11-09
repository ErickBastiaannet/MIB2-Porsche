from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wrapper_is_one_shot_and_execs_untouched_oem_binary() -> None:
    text = (ROOT / "unit" / "mm_ipod_rgi.sh").read_text()
    assert "connectwow-rgi/mm-ipod" in text
    assert 'mv "$STATE/pending" "$STATE/attempted"' in text
    assert 'exec "$REAL" "$@"' in text
    assert "LD_PRELOAD" in text


def test_dio_launcher_does_not_preload_mm_ipod_hook() -> None:
    text = (ROOT / "unit" / "dio_manager_controls.sh").read_text()
    assert "cw-rgi.so" not in text
    assert 'LD_PRELOAD="$CW_ROOT/cw-receiver-controls.so' in text
