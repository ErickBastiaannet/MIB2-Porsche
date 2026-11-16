#!/bin/sh
# K5137/MU1417 mm-ipod wrapper. The installer keeps the untouched OEM binary
# as connectwow-rgi/mm-ipod so argv[0] remains mm-ipod.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
REAL=/mnt/app/armle/usr/sbin/connectwow-rgi/mm-ipod
STATE=/mnt/persist/connectwow-carplay/guidance-native
HOOK=$ROOT/cw-rgi.so
TRIAL=/ramdisk/cw-guidance-native-trial

CW_RGI_ENABLE=0
if [ -s "$STATE/confirmed" ]; then
    CW_RGI_ENABLE=1
elif [ -s "$STATE/pending" ]; then
    if mv "$STATE/pending" "$STATE/attempted"; then
        if echo trial > "$TRIAL"; then CW_RGI_ENABLE=1; fi
    fi
elif [ -s "$TRIAL" ] && [ -s "$STATE/attempted" ]; then
    # iAP2 restarts mm-ipod on USB reconnect. Keep a one-BOOT trial alive
    # across those restarts; RAM is cleared on the next complete PCM boot.
    CW_RGI_ENABLE=1
fi

if [ "$CW_RGI_ENABLE" -eq 1 ] && [ -s "$HOOK" ]; then
    LD_PRELOAD="$HOOK${LD_PRELOAD:+:$LD_PRELOAD}"
    export CW_RGI_ENABLE LD_PRELOAD
else
    unset CW_RGI_ENABLE
    unset LD_PRELOAD
fi
exec "$REAL" "$@"
