#!/bin/ksh
# Isolated Porsche MU1417 zoom hook; does not replace lsd.sh or DIO.
set -u
ACTION=${1:-status}
if [ "${2:-}" != --mmx-child ] && [ -r /net/mmx/ifs/lsd.jxe ]; then
    exec on -f mmx /bin/ksh "$0" "$ACTION" --mmx-child
fi

APP=/mnt/app
JARS=$APP/eso/hmi/lsd/jars
TARGET=$JARS/ConnectWowZoom.experimental.jar
MARKER=$APP/eso/hmi/connectwow-carplay/zoom-test-installed
PAYLOAD=
for SD in /fs/sda0 /fs/sdb0; do
    if [ -s "$SD/online/carplay-zoom/PorscheCarPlayZoom.experimental.jar" ]; then
        PAYLOAD=$SD/online/carplay-zoom/PorscheCarPlayZoom.experimental.jar
        break
    fi
done

function fail { echo "ERROR: $*"; exit 1; }
function reboot_unit {
    echo "Zoomproef bijgewerkt; RCC-herstart wordt aangevraagd."
    sleep 2
    on -f rcc /usr/apps/mib2_ioc_flash reboot || fail "RCC-herstart mislukt"
}

case "$ACTION" in
status)
    if [ -s "$TARGET" ] && [ -s "$MARKER" ]; then echo "Zoomproef: geinstalleerd"
    else echo "Zoomproef: niet geinstalleerd"; fi
    ;;
install)
    [ -n "$PAYLOAD" ] || fail "Zoompayload ontbreekt op SD"
    [ -s "$APP/eso/hmi/lsd/lsd.sh.cw-stock" ] || fail "OEM HMI-back-up ontbreekt"
    mount -uw "$APP" || fail "Appvolume niet schrijfbaar"
    mkdir -p "$JARS" "${MARKER%/*}" || { mount -ur "$APP"; fail "Doelmap ontbreekt"; }
    cp -p "$PAYLOAD" "$TARGET.new" || { mount -ur "$APP"; fail "Kopieren mislukt"; }
    [ -s "$TARGET.new" ] || { mount -ur "$APP"; fail "Gekopieerde JAR is leeg"; }
    mv -f "$TARGET.new" "$TARGET" || { mount -ur "$APP"; fail "Activeren mislukt"; }
    echo isolated-zoom > "$MARKER" || { mount -ur "$APP"; fail "Marker mislukt"; }
    chmod 644 "$TARGET" "$MARKER"
    mount -ur "$APP" || fail "Appvolume niet read-only"
    reboot_unit
    ;;
restore)
    mount -uw "$APP" || fail "Appvolume niet schrijfbaar"
    rm -f "$TARGET" "$TARGET.new" "$MARKER"
    mount -ur "$APP" || fail "Appvolume niet read-only"
    reboot_unit
    ;;
*) fail "Gebruik: status, install of restore";;
esac
