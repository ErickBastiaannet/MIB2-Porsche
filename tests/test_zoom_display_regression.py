from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_zoom_matches_public_mhi2_fifo_without_invented_timing():
    source = (ROOT / "java/org/connectwow/carplay/PorscheClusterControls.java").read_text()
    assert "QUEUE_SIZE = 16" in source
    assert "enqueueLocked(direction)" in source
    assert "INTERVAL_MS" not in source
    assert "TAIL_MS" not in source
    assert 'sendControl("show-map")' not in source


def test_carplay_zoom_preserves_porsche_scale_ack():
    source = (ROOT / "build-tools/BuildPorscheHooks.java").read_text()
    scale = source.index("if (scale) {")
    setting = source.index("if (scaleSetting) {")
    block = source[scale:setting]
    assert '"consumeMapScale", "(I)Z"' in block
    assert '"updateMapScale", "()V"' in block
    assert "Opcodes.RETURN" in block


def test_renderer_reuses_serialized_supervisor_preflight():
    source = (ROOT / "native/porsche_unit.c").read_text()
    start = source.index("static int decode_worker(", source.index("#ifdef CW_YUV_RENDERER"))
    end = source.index("static void restore_context", start)
    worker = source[start:end]
    assert 'cw_dm_query(root, "gd"' not in worker
    assert "cw_window_start" in worker
    assert "retry_at = cw_monotonic_ms() + 250" in source
