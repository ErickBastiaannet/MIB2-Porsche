#!/bin/ksh
# Transactional installer for the isolated MU1417 zoom probe staged in RAM.
set -u

APP=/mnt/app
ROOT=$APP/eso/hmi/connectwow-carplay/zoom-oneshot
STATE=/mnt/persist/connectwow-carplay/zoom-oneshot
LSD=$APP/eso/hmi/lsd/lsd.sh
STOCK=$LSD.cw-stock
OLD=$APP/eso/hmi/lsd/jars/ConnectWowZoom.experimental.jar
TOOL=$APP/eso/hmi/connectwow-carplay/v14/cw-window-candidate
SOURCE_JAR=/ramdisk/cw-zoom-ftp.jar
SOURCE_WRAPPER=/ramdisk/cw-zoom-ftp-wrapper.sh
JAR_SHA=264f4231e69c1ab24cf036b7e9a518d25374a3a5723b82b31647371c86779a82
WRAPPER_SHA=07473a80065f010d0ca4fbe743071abc995d5ed3a98d7e293e59fb8f03c5e69a
STOCK_SHA=7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091
OK=1
OLD_MOVED=0

[ -x "$TOOL" ] || OK=0
[ "$OK" -eq 0 ] || [ "$($TOOL --hash "$SOURCE_JAR")" = "$JAR_SHA" ] || OK=0
[ "$OK" -eq 0 ] || [ "$($TOOL --hash "$SOURCE_WRAPPER")" = "$WRAPPER_SHA" ] || OK=0
[ "$OK" -eq 0 ] || [ "$($TOOL --hash "$LSD")" = "$STOCK_SHA" ] || OK=0
[ "$OK" -eq 0 ] || [ "$($TOOL --hash "$STOCK")" = "$STOCK_SHA" ] || OK=0
if [ "$OK" -eq 0 ]; then
    echo "ZOOM_ONESHOT_PREFLIGHT_FAILED"
    exit 1
fi

mount -uw "$APP" || { echo "ZOOM_ONESHOT_RW_FAILED"; exit 1; }
mkdir -p "$ROOT" "$STATE" || OK=0

if [ "$OK" -eq 1 ]; then
    cp -p "$SOURCE_JAR" "$ROOT/PorscheCarPlayZoom.experimental.jar.cw-new" || OK=0
fi
if [ "$OK" -eq 1 ]; then
    [ "$($TOOL --hash "$ROOT/PorscheCarPlayZoom.experimental.jar.cw-new")" = "$JAR_SHA" ] || OK=0
fi
if [ "$OK" -eq 1 ]; then
    mv -f "$ROOT/PorscheCarPlayZoom.experimental.jar.cw-new" "$ROOT/PorscheCarPlayZoom.experimental.jar" || OK=0
fi
if [ "$OK" -eq 1 ]; then
    cp -p "$SOURCE_WRAPPER" "$ROOT/lsd_zoom_oneshot.sh" || OK=0
    chmod 755 "$ROOT/lsd_zoom_oneshot.sh" || OK=0
fi
if [ "$OK" -eq 1 ]; then
    [ "$($TOOL --hash "$ROOT/lsd_zoom_oneshot.sh")" = "$WRAPPER_SHA" ] || OK=0
fi
if [ "$OK" -eq 1 ] && [ -e "$OLD" ]; then
    [ ! -e "$ROOT/ConnectWowZoom.previous.jar" ] || OK=0
    if [ "$OK" -eq 1 ]; then
        mv "$OLD" "$ROOT/ConnectWowZoom.previous.jar" && OLD_MOVED=1 || OK=0
    fi
fi
if [ "$OK" -eq 1 ]; then
    cp -p "$ROOT/lsd_zoom_oneshot.sh" "$LSD.cw-new" || OK=0
    chmod 755 "$LSD.cw-new" || OK=0
fi
if [ "$OK" -eq 1 ]; then
    echo probe > "$STATE/pending.cw-new" || OK=0
    mv -f "$STATE/pending.cw-new" "$STATE/pending" || OK=0
    rm -f "$STATE/attempted" "$STATE/hmi-boot.status"
fi
if [ "$OK" -eq 1 ]; then
    mv -f "$LSD.cw-new" "$LSD" || OK=0
fi

if [ "$OK" -ne 1 ]; then
    rm -f "$LSD.cw-new" "$STATE/pending" "$STATE/pending.cw-new"
    cp -p "$STOCK" "$LSD"
    if [ "$OLD_MOVED" -eq 1 ] && [ ! -e "$OLD" ]; then
        mv "$ROOT/ConnectWowZoom.previous.jar" "$OLD"
    fi
fi

mount -ur "$APP" || { echo "ZOOM_ONESHOT_RO_FAILED"; exit 1; }
if [ "$OK" -eq 1 ]; then
    echo "ZOOM_ONESHOT_INSTALLED"
    exit 0
fi
echo "ZOOM_ONESHOT_INSTALL_FAILED"
exit 1
