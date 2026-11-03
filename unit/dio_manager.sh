#!/bin/sh
# Native-only projection. The Java/HMI startup files are never replaced.
CW_ROOT=/mnt/app/eso/hmi/connectwow-carplay
CW_STOCK=/mnt/app/eso/bin/apps/dio_manager.cw-stock
CW_ATTEMPT=/ramdisk/cw-porsche-native-attempted
if [ ! -s "$CW_ROOT/installed.manifest" ] || [ ! -x "$CW_ROOT/porsche-carplay" ] || [ -e "$CW_ATTEMPT" ]; then
    exec "$CW_STOCK" "$@"
fi
# One attempt per boot. A factory restart after any failure gets stock DIO.
: > "$CW_ATTEMPT" || exec "$CW_STOCK" "$@"
# Publish geometry before the iPhone's first capability request. Starting the
# supervisor only after DIO risks missing that request on a fast reconnect.
LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib \
    "$CW_ROOT/porsche-carplay" --prime-geometry "$CW_ROOT" \
    > /ramdisk/cw-porsche-prime.log 2>&1 || exec "$CW_STOCK" "$@"
(
    CARPLAY_ALTSCREEN_ENABLE=1
    CARPLAY_ALTSCREEN_LOG=/ramdisk/cw-porsche-airplay.log
    CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture
    # MU1417's loader has only accepted the physically observed two-library
    # preload order. Keep RGI loaded but explicitly passive during video
    # qualification; it forwards the stock call without patching the vtable.
    CW_RGI_ENABLE=0
    LD_PRELOAD="$CW_ROOT/libcw-porsche-rgi.so:$CW_ROOT/libcw-porsche-capture_receiver.so${LD_PRELOAD:+:$LD_PRELOAD}"
    export CARPLAY_ALTSCREEN_ENABLE CARPLAY_ALTSCREEN_LOG CARPLAY_ALTSCREEN_CAPTURE_DIR CW_RGI_ENABLE LD_PRELOAD
    exec "$CW_STOCK" "$@"
) &
CW_CHILD=$!
(
    unset LD_PRELOAD
    LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib
    export LD_LIBRARY_PATH
    exec "$CW_ROOT/porsche-carplay" --run "$CW_ROOT" "$CW_CHILD"
) >>/ramdisk/cw-porsche-carplay.log 2>&1 &
CW_SUPERVISOR=$!
CW_CLOSING=0
trap 'CW_CLOSING=1; kill -TERM "$CW_CHILD" "$CW_SUPERVISOR" 2>/dev/null' HUP INT TERM
wait "$CW_CHILD"
CW_RESULT=$?
echo "DIO_CAPTURE_EXIT result=$CW_RESULT child=$CW_CHILD" >>/ramdisk/cw-porsche-launcher.log
kill -TERM "$CW_SUPERVISOR" 2>/dev/null
wait "$CW_SUPERVISOR" 2>/dev/null
# The marker is a recursion guard for this invocation, not a per-boot lock.
# A later phone connection must always be allowed to attempt a fresh session.
rm -f "$CW_ATTEMPT"
if [ "$CW_CLOSING" -eq 0 ] && [ "$CW_RESULT" -ne 0 ]; then
    # The parent never inherited our preload; stock DIO can be retried safely.
    exec "$CW_STOCK" "$@"
fi
exit "$CW_RESULT"
