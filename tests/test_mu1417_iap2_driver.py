import hashlib
import struct
from pathlib import Path

import pytest

from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "verify_mu1417_iap2_driver",
    ROOT / "build-tools" / "verify_mu1417_iap2_driver.py",
)
MODULE = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def valid_driver() -> bytearray:
    payload = bytearray(0x21588)
    for offset, opcode in MODULE.CALL_SITES.items():
        struct.pack_into("<I", payload, offset, opcode)
    return payload


def test_rejects_unknown_hash_even_when_call_sites_match(tmp_path: Path) -> None:
    path = tmp_path / "ipod-drvr-iap2.so"
    path.write_bytes(valid_driver())
    with pytest.raises(ValueError, match="unexpected MU1417 iAP2 driver hash"):
        MODULE.verify(path)


def test_declares_both_verified_k5137_call_sites() -> None:
    assert MODULE.CALL_SITES == {0x1068C: 0xEB000345, 0x21584: 0xEBFFC61D}
    assert len(MODULE.DRIVER_SHA256) == 64
    int(MODULE.DRIVER_SHA256, 16)


def test_hash_constant_is_lowercase_sha256() -> None:
    assert MODULE.DRIVER_SHA256 == MODULE.DRIVER_SHA256.lower()
    assert hashlib.sha256(b"").hexdigest() != MODULE.DRIVER_SHA256
