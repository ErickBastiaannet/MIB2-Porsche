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


def test_renderer_tolerates_transient_geometry_lease_misses():
    source = (ROOT / "native/porsche_unit.c").read_text()
    assert source.count("next_geometry_check = checked_at + 250U") == 2
    assert source.count("checked_at - last_geometry_ok > 2000U") == 2
    assert "CARPLAY_SOURCE_EXIT geometry-unavailable" in source
    assert "CARPLAY_RENDERER_EXIT geometry-unavailable" in source


def test_supervisor_reuses_a_valid_existing_cluster_window():
    source = (ROOT / "native/porsche_unit.c").read_text()
    assert "cw_dm_layer(text, LAYER, geometry.width, geometry.height, 0) ||" in source
    assert "cw_dm_layer(text, LAYER, geometry.width, geometry.height, 1)" in source


def test_first_pixel_wait_uses_source_liveness_not_a_fixed_deadline():
    source = (ROOT / "native/porsche_unit.c").read_text()
    session = (ROOT / "native/porsche_session.c").read_text()
    assert "if (have_pixels && cw_monotonic_ms() - last_pixels > 5000U)" in source
    assert "have_pixels ? 5000U : 15000U" not in source
    assert "s->phase == CW_CARPLAY" in session
    assert "s->phase == CW_WAIT_VIDEO ? 15U" not in session


def test_supervisor_tolerates_one_transient_geometry_read_gap():
    source = (ROOT / "native/porsche_unit.c").read_text()
    assert "cw_geometry last_valid_geometry" in source
    assert "last_geometry_read_ok" in source
    assert "cw_monotonic_ms() - last_geometry_read_ok <= 2000U" in source


def test_first_frame_waits_for_overlay_without_killing_healthy_worker():
    source = (ROOT / "native/porsche_unit.c").read_text()
    assert "!output_ok && session.phase == CW_WAIT_VIDEO" in source
    assert "retain the healthy decoder and retry activation" in source
