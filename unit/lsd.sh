#!/bin/sh
# MU1417 wrapper. The installer accepts this only with the exact stock lsd.sh
# hash and retains that original as lsd.sh.cw-stock.
CW_ROOT=/mnt/app/eso/hmi/connectwow-carplay
CW_STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
if [ -s "$CW_ROOT/installed.manifest" ] && [ -s "$CW_ROOT/ConnectWowCarPlay.jar" ]; then
    VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$CW_ROOT/ConnectWowCarPlay.jar"
    export VMOPTIONS
fi
exec /bin/sh "$CW_STOCK" "$@"
