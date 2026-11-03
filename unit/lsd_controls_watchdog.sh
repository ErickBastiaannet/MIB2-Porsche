#!/bin/sh
# One-probe-boot HMI wrapper. An unconfirmed candidate automatically falls
# back to the stock HMI on the next boot, so a bad bridge cannot loop forever.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
JAR=$ROOT/PorscheCarPlayBridge.experimental.jar

if [ -s "$ROOT/confirmed" ] && [ -s "$JAR" ]; then
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
    export VMOPTIONS
elif [ -s "$ROOT/pending" ] && [ -s "$JAR" ]; then
    rm -f "$ROOT/pending"
    echo attempted > "$ROOT/attempted"
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"
    export VMOPTIONS
fi

exec /bin/sh "$STOCK" "$@"
