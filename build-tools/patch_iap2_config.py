"""Register the MU1417 iAP2 route-guidance messages without rewriting its config."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

SENT = ("0x5200", "0x5203")
RECEIVED = ("0x5201", "0x5202", "0x5204")


def _merge(value: str, required: tuple[str, ...]) -> str:
    values = [item.strip() for item in value.split(",") if item.strip()]
    known = {item.upper() for item in values}
    values.extend(item for item in required if item.upper() not in known)
    return ",".join(values)


def patch(text: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    section = re.search(r"(?ms)^\[ident\]\s*$.*?(?=^\[|\Z)", text)
    if section:
        body = section.group(0)
        for key, required in (("recvmsgs", RECEIVED), ("sendmsgs", SENT)):
            match = re.search(rf"(?m)^{key}\s*=\s*([^\r\n]*)", body)
            if match:
                body = body[: match.start(1)] + _merge(match.group(1), required) + body[match.end(1) :]
            else:
                body = body.rstrip("\r\n") + newline + key + "=" + ",".join(required) + newline + newline
        return text[: section.start()] + body + text[section.end() :]

    marker = re.search(r"(?m)^\[commands\]\s*$", text)
    if not marker:
        raise ValueError("iap2.cfg has no [commands] marker; refusing an unverified layout")
    addition = (
        "# ConnectWow iAP2 Route Guidance message registration." + newline
        + "[ident]" + newline
        + "recvmsgs=" + ",".join(RECEIVED) + newline
        + "sendmsgs=" + ",".join(SENT) + newline + newline
    )
    return text[: marker.start()] + addition + text[marker.start() :]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    original = args.source.read_text(encoding="utf-8")
    updated = patch(original)
    if patch(updated) != updated:
        raise SystemExit("internal error: patch is not idempotent")
    args.target.write_text(updated, encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
