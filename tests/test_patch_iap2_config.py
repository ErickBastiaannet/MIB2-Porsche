import importlib.util
from pathlib import Path


PATH = Path(__file__).parents[1] / "build-tools" / "patch_iap2_config.py"
SPEC = importlib.util.spec_from_file_location("patch_iap2_config", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_adds_verified_ident_section_and_is_idempotent():
    original = "[accessory]\nname=PORSCHE\n\n[commands]\niap2_nowplay_set=no\n"
    updated = MODULE.patch(original)
    assert "[ident]\nrecvmsgs=0x5201,0x5202,0x5204\nsendmsgs=0x5200,0x5203\n" in updated
    assert updated.index("[ident]") < updated.index("[commands]")
    assert MODULE.patch(updated) == updated


def test_preserves_existing_custom_message_ids():
    original = "[ident]\nrecvmsgs=0x1234,0x5201\nsendmsgs=0x5678\n\n[commands]\n"
    updated = MODULE.patch(original)
    assert "recvmsgs=0x1234,0x5201,0x5202,0x5204" in updated
    assert "sendmsgs=0x5678,0x5200,0x5203" in updated


def test_refuses_unknown_layout():
    try:
        MODULE.patch("[accessory]\nname=PORSCHE\n")
    except ValueError as error:
        assert "unverified layout" in str(error)
    else:
        raise AssertionError("unknown layout was modified")


def test_rgi_driver_binding_runs_in_mm_ipod_and_intercepts_driver_load():
    source = (PATH.parents[1] / "native/porsche_rgi_hook.c").read_text()
    assert "void *dlopen(" in source
    assert 'strstr(path,"ipod-drvr-iap2.so")' in source
    assert "bind_driver(handle)" in source
    assert "RTLD_NOLOAD" not in source


def test_rgi_driver_uses_verified_writable_dispatch_tables():
    source = (PATH.parents[1] / "native/porsche_rgi_hook.c").read_text()
    assert "0xebffc61dU" in source
    assert "link_send_raw_message" in source
    assert "link_handle_iap2pkt" in source
    assert 'dlsym(handle,"ident_info_funcs")' in source
    assert 'table+0xc0+0x20' in source
    assert 'mprotect(' not in source
    assert 'if(rc!=1)push_packet(link,packet)' in source
    assert "got_guidance" in source
    assert "now-last_request>=2" in source
    assert "now-last_publish>=2" in source


def test_capture_path_does_not_load_the_mm_ipod_hook():
    source = (PATH.parents[1] / "build-tools/prepare_native.py").read_text()
    assert 'cw_rgi_handle' not in source
    assert 'rgi-activate-binding' not in source
