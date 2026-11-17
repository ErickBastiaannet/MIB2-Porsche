#!/bin/ksh
# MU1417 portable HMI wrapper. Stock HMI remains on the target unit.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
STATE=/mnt/persist/connectwow-carplay/portable
STOCK=/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
TOOL=$ROOT/cw-window-candidate
rm -f /ramdisk/cw-nav-priority.enabled /ramdisk/cw-nav-priority.v1 /ramdisk/cw-nav-priority.applied
ENABLE=0
if [ -s "$STATE/confirmed" ]; then
 ENABLE=1
elif [ -s "$STATE/pending" ]; then
 if mv "$STATE/pending" "$STATE/attempted"; then ENABLE=1; fi
fi
if [ "$ENABLE" = 1 ] && [ -s "$ROOT/enabled" ] &&
 [ "$("$TOOL" --hash "$ROOT/PorscheNavigationPriority.test.jar")" = @JAR_SHA@ ] &&
 [ "$("$TOOL" --hash "$TOOL")" = @WINDOW_SHA@ ]; then
 if echo enabled > /ramdisk/cw-nav-priority.enabled; then
  VMOPTIONS="$VMOPTIONS -Dconnectwow.carplay.satelliteLogo=hide-during-carplay -Dconnectwow.carplay.navigationPriority=porsche-first -Xbootclasspath/p:$ROOT/PorscheNavigationPriority.test.jar"
  export VMOPTIONS
 fi
fi
exec /bin/ksh "$STOCK" "$@"
