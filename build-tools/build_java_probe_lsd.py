"""Build a minimal one-boot Java probe launcher from the exact MU1417 OEM lsd.sh."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


OEM_SHA256 = "7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091"
ANCHOR = 'VMOPTIONS="$VMOPTIONS -DScreenRes=4"\n'
MARKER = "# CONNECTWOW_JAVA_PROBE_V1\n"


def build(
    source: Path,
    target: Path,
    jar: str,
    state: str,
    extra_jar: str | None = None,
    extra_state: str | None = None,
) -> None:
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != OEM_SHA256:
        raise SystemExit(f"unexpected OEM lsd.sh: {digest}")
    text = payload.decode("ascii")
    if text.count(ANCHOR) != 1 or MARKER in text:
        raise SystemExit("OEM anchor missing, ambiguous or already patched")
    snippet = (
        MARKER
        + f'CW_PROBE_JAR="{jar}"\n'
        + f'CW_PROBE_STATE="{state}"\n'
        + 'CW_PROBE_ENABLE=0\n'
        + 'if [ -s "$CW_PROBE_STATE/confirmed" ] && [ -s "$CW_PROBE_JAR" ]; then\n'
        + '    CW_PROBE_ENABLE=1\n'
        + 'elif [ -s "$CW_PROBE_STATE/pending" ] && [ -s "$CW_PROBE_JAR" ]; then\n'
        + '    if mv "$CW_PROBE_STATE/pending" "$CW_PROBE_STATE/attempted"; then\n'
        + '        CW_PROBE_ENABLE=1\n'
        + '    fi\n'
        + 'fi\n'
        + 'if [ "$CW_PROBE_ENABLE" -eq 1 ]; then\n'
        + '    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$CW_PROBE_JAR"\n'
        + 'fi\n'
    )
    if (extra_jar or extra_state):
        if not extra_jar or not extra_state:
            raise SystemExit("both extra probe jar and state are required")
        snippet += (
            f'CW_EXTRA_PROBE_JAR="{extra_jar}"\n'
            + f'CW_EXTRA_PROBE_STATE="{extra_state}"\n'
            + 'CW_EXTRA_PROBE_ENABLE=0\n'
            + 'if [ -s "$CW_EXTRA_PROBE_STATE/confirmed" ] && [ -s "$CW_EXTRA_PROBE_JAR" ]; then\n'
            + '    CW_EXTRA_PROBE_ENABLE=1\n'
            + 'elif [ -s "$CW_EXTRA_PROBE_STATE/pending" ] && [ -s "$CW_EXTRA_PROBE_JAR" ]; then\n'
            + '    if mv "$CW_EXTRA_PROBE_STATE/pending" "$CW_EXTRA_PROBE_STATE/attempted"; then\n'
            + '        CW_EXTRA_PROBE_ENABLE=1\n'
            + '    fi\n'
            + 'fi\n'
            + 'if [ "$CW_EXTRA_PROBE_ENABLE" -eq 1 ]; then\n'
            + '    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$CW_EXTRA_PROBE_JAR"\n'
            + 'fi\n'
        )
    snippet += "# CONNECTWOW_JAVA_PROBE_END\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.replace(ANCHOR, ANCHOR + snippet).encode("ascii"))
    print(hashlib.sha256(target.read_bytes()).hexdigest(), target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--jar", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--extra-jar")
    parser.add_argument("--extra-state")
    args = parser.parse_args()
    build(args.source, args.target, args.jar, args.state, args.extra_jar, args.extra_state)


if __name__ == "__main__":
    main()
