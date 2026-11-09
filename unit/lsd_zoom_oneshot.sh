#!/bin/ksh
# Isolated zoom probe: consume the persistent ticket before starting the JVM.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/zoom-oneshot
STATE=/mnt/persist/connectwow-carplay/zoom-oneshot
STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
TOOL=/mnt/app/eso/hmi/connectwow-carplay/controls-v15/cw-window-candidate
OLD=/mnt/app/eso/hmi/lsd/jars/ConnectWowZoom.experimental.jar
JAR=$ROOT/PorscheCarPlayZoom.experimental.jar
EXPECTED=264f4231e69c1ab24cf036b7e9a518d25374a3a5723b82b31647371c86779a82
STOCK_SHA=7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091
if [ "$("$TOOL" --hash "$STOCK")" != "$STOCK_SHA" ]; then
    echo "ZOOM_STOCK_HASH_FAILED"
    exit 1
fi
MODE=stock-fallback
if [ ! -e "$OLD" ] && [ -s "$STATE/pending" ] && [ "$("$TOOL" --hash "$JAR")" = "$EXPECTED" ]; then
    if mv "$STATE/pending" "$STATE/attempted" && [ ! -e "$STATE/pending" ]; then
        VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
        export VMOPTIONS
        MODE=zoom-one-shot
    fi
fi
# One short record per boot; no phone data or unbounded log.
echo "$MODE" > "$STATE/hmi-boot.status"
exec /bin/ksh "$STOCK" "$@"
