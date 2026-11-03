"""Build a small Online Menu overlay for the isolated MU1417 zoom test."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "build/PorscheCarPlayZoom.experimental.jar"
SCRIPT = ROOT / "unit/zoom_test.sh"


def main():
    if not JAR.is_file() or not SCRIPT.is_file():
        raise SystemExit("Build the split HMI jars first")
    menu = '''

# Porsche isolated CarPlay zoom test
screen CarPlayZoomTest OnlineMenu
script
   value sys 1 0x0100 "/scripts/online/carplay_zoom_install.sh"
   label "CarPlay: installeer losse zoomproef"
script
   value sys 1 0x0100 "/scripts/online/carplay_zoom_restore.sh"
   label "CarPlay: verwijder zoomproef"
script
   value sys 1 0x0100 "/scripts/online/carplay_zoom_status.sh"
   label "CarPlay: status zoomproef"
'''
    readme = '''Porsche MU1417 - geisoleerde zoomproef
================================================
Deze proef laat de werkende native V15-installatie ongemoeid en voegt alleen
de MapScale-zoomhook toe via Porsche's bestaande lsd/jars-loader.

Installeer de zoomproef, wacht op de reboot en controleer eerst of de originele
navigatie normaal opent. Start daarna CarPlay en test in- en uitzoomen. Zonder
actieve, actuele native CarPlay-lease worden alle zoomacties aan Porsche gelaten.

Bij een vastlopende HMI: gebruik Telnet en voer uit:
  /bin/ksh /fs/sda0/install/scripts/cwzoom.sh restore
Gebruik /fs/sdb0 wanneer de kaart daar is gekoppeld.
'''
    output = ROOT / "build/porsche-carplay-zoom-test-MU1417.zip"
    base_menu = (ROOT / "templates/OnlineMenu.esd").read_text(encoding="utf-8")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        def put(name, data, executable=False):
            info = zipfile.ZipInfo(name, (2026, 11, 3, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
        put("install/scripts/cwzoom.sh", SCRIPT.read_bytes(), True)
        for suffix, action in (("install", "install"), ("restore", "restore"), ("status", "status")):
            put(f"install/scripts/carplay_zoom_{suffix}.sh",
                f'#!/bin/ksh\nBASE=${{0%/*}}\nexec /bin/ksh "$BASE/cwzoom.sh" {action}\n'.encode(), True)
        put("install/esd/OnlineMenu.esd", (base_menu + menu).encode())
        put("online/carplay-zoom/PorscheCarPlayZoom.experimental.jar", JAR.read_bytes())
        put("LEESMIJ-ZOOMPROEF.txt", readme.encode("utf-8"))
    print(output)
    print(hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
