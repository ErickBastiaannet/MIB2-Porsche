import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "reconnect", Path(__file__).parents[1] / "build-tools/prepare_reconnect_config.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_preserves_other_children_and_original_environment():
    import json
    data = b'{"children":{"carplay":{"exec":"dio_manager","envs":["LD_LIBRARY_PATH=/stock","IPL_CONFIG_DIR_DIO_MANAGER=/etc/eso/production"]},"other":{"exec":"unchanged"}}}'
    result = json.loads(MODULE.patch(data))
    assert result["children"]["other"] == {"exec": "unchanged"}
    child = result["children"]["carplay"]
    assert child["exec"] == "dio_manager.cw-stock"
    assert child["envs"][:2] == json.loads(data)["children"]["carplay"]["envs"]
    assert "CW_PROCESS_SUPERVISOR=1" in child["envs"]
    with pytest.raises(ValueError):
        MODULE.patch(MODULE.patch(data))


def test_refuses_unknown_layout():
    with pytest.raises(ValueError):
        MODULE.patch(b'{"children":{}}')
