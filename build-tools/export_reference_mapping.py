"""Regenerate the pinned reference oracle; never contacts or changes a unit."""
import argparse
import subprocess
import tempfile
from pathlib import Path

REVISION = "21f501611b0b28dbdeb2849e8443ce90ec9517ff"
HARNESS = """
import com.luka.carplay.rgd.ManeuverMapper;
public final class ReferenceMapperExport {
    public static void main(String[] args) {
        int[] angles={-180,-113,-90,-67,-45,-1,0,1,45,67,90,113,180,1000};
        for(int type=0;type<=53;type++)for(int angle:angles)
        for(int junction=0;junction<3;junction++)for(int side=0;side<2;side++) {
            int[] result=ManeuverMapper.map(type,angle,junction,side,angle!=1000);
            System.out.println(type+" "+angle+" "+junction+" "+side+" "+result[0]+" "+result[1]);
        }
    }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--jdk", type=Path, required=True, help="JDK bin directory")
    args = parser.parse_args()
    revision = subprocess.check_output(
        ["git", "-C", str(args.reference), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != REVISION:
        raise SystemExit("Reference revision changed; review it before replacing the oracle")
    mapper = "java_patch/com/luka/carplay/rgd/ManeuverMapper.java"
    # Use the pinned Git object, even when the reference checkout is dirty.
    source = subprocess.check_output(["git", "-C", str(args.reference), "show", REVISION + ":" + mapper])
    def tool(name):
        path = args.jdk / name
        return str(path if path.exists() else path.with_suffix(".exe"))
    with tempfile.TemporaryDirectory(prefix="porsche-reference-") as folder:
        root = Path(folder)
        (root / "ManeuverMapper.java").write_bytes(source)
        (root / "ReferenceMapperExport.java").write_text(HARNESS, encoding="utf-8")
        subprocess.run([tool("javac"), "-d", str(root), str(root / "ManeuverMapper.java"), str(root / "ReferenceMapperExport.java")], check=True)
        result = subprocess.check_output([tool("java"), "-cp", str(root), "ReferenceMapperExport"])
    result = result.replace(b"\r\n", b"\n")
    if len(result.splitlines()) != 4536:
        raise SystemExit("Unexpected reference case count")
    target = Path(__file__).resolve().parents[1] / "tests/fixtures/rgi-map-reference.tsv"
    target.write_bytes(result)
    print("REFERENCE_MAPPING_EXPORTED", REVISION, "4536 cases")


if __name__ == "__main__":
    main()
