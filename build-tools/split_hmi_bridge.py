"""Split the research HMI bridge into independently testable feature jars."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "build/PorscheCarPlayBridge.experimental.jar"
OUTPUTS = {
    "PorscheCarPlayDisplay.experimental.jar": {
        "de/audi/tghu/navi/app/map/gui/layout/LayoutProviderG22Kombi.class",
        "de/audi/app/terminalmode/smartphone/carplay/CarPlayDSIManager.class",
        "de/audi/tghu/fwhmi/DisplayManagerMIB2High.class",
        "org/connectwow/carplay/PorscheCluster.class",
        "org/connectwow/carplay/PorscheGeometry.class",
    },
    "PorscheCarPlayZoom.experimental.jar": {
        "de/audi/tghu/navi/app/cluster/CombiBAPListener.class",
        "org/connectwow/carplay/PorscheCluster.class",
        "org/connectwow/carplay/PorscheClusterControls.class",
        "org/connectwow/carplay/PorscheClusterControls$1.class",
    },
    "PorscheCarPlayGuidance.experimental.jar": {
        "de/audi/tghu/navi/app/cluster/ClusterService.class",
        "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance$1.class",
        "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance$State.class",
        "de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.class",
    },
}


def main():
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source bridge: {SOURCE}")
    manifest = {}
    with zipfile.ZipFile(SOURCE) as source:
        available = set(source.namelist())
        for filename, entries in OUTPUTS.items():
            missing = entries - available
            if missing:
                raise SystemExit(f"{filename}: missing {sorted(missing)}")
            target = ROOT / "build" / filename
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as output:
                for entry in sorted(entries):
                    info = zipfile.ZipInfo(entry)
                    info.date_time = (1980, 1, 1, 0, 0, 0)
                    output.writestr(info, source.read(entry))
            manifest[filename] = {
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "classes": sorted(entries),
            }
    (ROOT / "build/split-hmi-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    for filename, details in manifest.items():
        print(details["sha256"], filename)


if __name__ == "__main__":
    main()
