"""Fail-closed verifier for the Porsche K5137/MU1417 iAP2 driver."""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

DRIVER_SHA256 = "7b9a1a6beef7bc893bb5a824486f4ad5fc34912a0b894a6d24d171ab324a8cb7"
CALL_SITES = {
    0x1068C: 0xEB000345,  # iap2_msg -> link_send_raw_message
    0x21584: 0xEBFFC61D,  # transport_recv_pkt -> link_handle_iap2pkt
}


def verify(path: Path) -> None:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != DRIVER_SHA256:
        raise ValueError(f"unexpected MU1417 iAP2 driver hash: {actual}")
    for offset, expected in CALL_SITES.items():
        if offset + 4 > len(payload):
            raise ValueError(f"call site outside driver: 0x{offset:x}")
        actual_word = struct.unpack_from("<I", payload, offset)[0]
        if actual_word != expected:
            raise ValueError(
                f"call-site mismatch at 0x{offset:x}: "
                f"0x{actual_word:08x} != 0x{expected:08x}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("driver", type=Path)
    args = parser.parse_args()
    verify(args.driver)
    print(f"MU1417_IAP2_DRIVER_OK {DRIVER_SHA256}")


if __name__ == "__main__":
    main()
