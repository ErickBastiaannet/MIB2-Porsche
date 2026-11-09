import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_probe_builder():
    path = ROOT / "build-tools/build_java_probe_lsd.py"
    spec = importlib.util.spec_from_file_location("build_java_probe_lsd", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fixture_oem():
        return (
            '#!/bin/ksh\nVMOPTIONS=""\n'
            + module.ANCHOR
            + 'echo "$VMOPTIONS"\n'
        ).encode("ascii")

    module.fixture_oem = fixture_oem
    return module
