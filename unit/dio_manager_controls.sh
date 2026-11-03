#!/bin/sh
# Fail-safe launcher for the opt-in controls/route-guidance candidate.
CW_PERSIST=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
CW_ROOT=/ramdisk/cw-link-probe-20261102
CW_LOG_ROOT=/mnt/persist/connectwow-carplay
CW_STOCK=/mnt/app/eso/bin/apps/dio_manager.cw-stock
CW_SD_LOG=
for CW_SD in /fs/sda0 /fs/sdb0; do
    if [ -d "$CW_SD" ]; then CW_SD_LOG=$CW_SD/connectwow-carplay-logs/v15; break; fi
done
[ -z "$CW_SD_LOG" ] || mkdir -p "$CW_SD_LOG"

if [ ! -s "$CW_PERSIST/enabled" ] || [ ! -x "$CW_PERSIST/cw-window-candidate" ] ||
   [ ! -s "$CW_PERSIST/cw-receiver-controls.so" ] || [ ! -s "$CW_PERSIST/cw-rgi.so" ] ||
   [ ! -s "$CW_PERSIST/libcw-query-stdio.so" ]; then
    exec "$CW_STOCK" "$@"
fi

mkdir -p "$CW_ROOT" "$CW_LOG_ROOT" || exec "$CW_STOCK" "$@"
# The supervisor deliberately requires a per-session opt-in marker before it
# may take over the cluster context.  The persistent controller writes its
# marker below /mnt/app, but every fresh RAM runtime needs its own marker too.
# Without this file the capture path still receives valid 800x480 frames while
# the renderer remains in alive=0 and never opens the cluster window.
echo enabled > "$CW_ROOT/enabled" || exec "$CW_STOCK" "$@"
cp "$CW_PERSIST/cw-window-candidate" "$CW_ROOT/cw-window-candidate" || exec "$CW_STOCK" "$@"
cp "$CW_PERSIST/cw-receiver-controls.so" "$CW_ROOT/cw-receiver-controls.so" || exec "$CW_STOCK" "$@"
cp "$CW_PERSIST/cw-rgi.so" "$CW_ROOT/cw-rgi.so" || exec "$CW_STOCK" "$@"
cp "$CW_PERSIST/libcw-query-stdio.so" "$CW_ROOT/libcw-query-stdio.so" || exec "$CW_STOCK" "$@"
chmod 755 "$CW_ROOT/cw-window-candidate" || exec "$CW_STOCK" "$@"
rm -f "$CW_ROOT/cw-carplay-live-v14.log" "$CW_ROOT/cw-airplay-live-v14.log" "$CW_ROOT/cw-porsche-prime.log"
echo "START profile=15 launcher=$$" > "$CW_LOG_ROOT/session.status"
[ -z "$CW_SD_LOG" ] || cp "$CW_LOG_ROOT/session.status" "$CW_SD_LOG/session.status"

LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib \
    "$CW_ROOT/cw-window-candidate" --prime-geometry "$CW_ROOT" \
    >"$CW_ROOT/cw-porsche-prime.log" 2>&1 || {
        echo "FALLBACK geometry" >> "$CW_LOG_ROOT/session.status"
        exec "$CW_STOCK" "$@"
    }

(
    CARPLAY_ALTSCREEN_ENABLE=1
    CARPLAY_ALTSCREEN_LOG=$CW_ROOT/cw-airplay-live-v14.log
    CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture
    CW_RGI_ENABLE=1
    LD_PRELOAD="$CW_ROOT/cw-rgi.so:$CW_ROOT/cw-receiver-controls.so${LD_PRELOAD:+:$LD_PRELOAD}"
    export CARPLAY_ALTSCREEN_ENABLE CARPLAY_ALTSCREEN_LOG CARPLAY_ALTSCREEN_CAPTURE_DIR CW_RGI_ENABLE LD_PRELOAD
    exec "$CW_STOCK" "$@"
) &
CW_CHILD=$!
(
    unset LD_PRELOAD
    LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib
    export LD_LIBRARY_PATH
    CW_SOURCE_READY=/ramdisk/cw-porsche-altstream.ready
    CW_RING=/ramdisk/cw-porsche-alt-ring.bin
    CW_PREFLIGHT=$CW_ROOT/cw-display-preflight.log
    CW_LAST_TIMESTAMP=
    CW_STABLE=0
    echo "WAITING_FOR_READY_STREAM child=$CW_CHILD" > "$CW_PREFLIGHT"
    while kill -0 "$CW_CHILD" 2>/dev/null; do
        CW_READY_PID=
        CW_READY_TIMESTAMP=
        if [ -s "$CW_SOURCE_READY" ] && [ -s "$CW_RING" ]; then
            read -r CW_READY_PID CW_READY_TIMESTAMP < "$CW_SOURCE_READY"
        fi
        if [ "$CW_READY_PID" = "$CW_CHILD" ] && [ -n "$CW_READY_TIMESTAMP" ] &&
           [ "$CW_READY_TIMESTAMP" != "$CW_LAST_TIMESTAMP" ] &&
           "$CW_ROOT/cw-window-candidate" --inspect "$CW_ROOT" > "$CW_PREFLIGHT.new" 2>&1 &&
           grep 'context=72' "$CW_PREFLIGHT.new" >/dev/null 2>&1; then
            CW_STABLE=$((CW_STABLE + 1))
            CW_LAST_TIMESTAMP=$CW_READY_TIMESTAMP
            cat "$CW_PREFLIGHT.new" > "$CW_PREFLIGHT"
            echo "READY_SAMPLE count=$CW_STABLE timestamp=$CW_READY_TIMESTAMP" >> "$CW_PREFLIGHT"
            if [ "$CW_STABLE" -ge 3 ]; then
                echo "READY_TO_RENDER child=$CW_CHILD" >> "$CW_PREFLIGHT"
                break
            fi
        else
            CW_STABLE=0
            CW_LAST_TIMESTAMP=$CW_READY_TIMESTAMP
        fi
        sleep 1
    done
    rm -f "$CW_PREFLIGHT.new"
    kill -0 "$CW_CHILD" 2>/dev/null || exit 0
    exec "$CW_ROOT/cw-window-candidate" --run "$CW_ROOT" "$CW_CHILD"
) >>"$CW_ROOT/cw-carplay-live-v14.log" 2>&1 &
CW_SUPERVISOR=$!
echo $$ > "$CW_ROOT/cw-launcher.pid"
echo "$CW_CHILD" > "$CW_ROOT/cw-dio-child.pid"
echo "$CW_SUPERVISOR" > "$CW_ROOT/cw-supervisor.pid"
echo "RUNNING child=$CW_CHILD supervisor=$CW_SUPERVISOR" >> "$CW_LOG_ROOT/session.status"
[ -z "$CW_SD_LOG" ] || cp "$CW_LOG_ROOT/session.status" "$CW_SD_LOG/session.status"

CW_CLOSING=0
trap 'CW_CLOSING=1; kill -TERM "$CW_CHILD" "$CW_SUPERVISOR" 2>/dev/null' HUP INT TERM
wait "$CW_CHILD"
CW_RESULT=$?
kill -TERM "$CW_SUPERVISOR" 2>/dev/null
wait "$CW_SUPERVISOR" 2>/dev/null
echo "STOP result=$CW_RESULT closing=$CW_CLOSING" >> "$CW_LOG_ROOT/session.status"
tail -200 "$CW_ROOT/cw-carplay-live-v14.log" > "$CW_LOG_ROOT/renderer.log" 2>/dev/null
grep 'event=' "$CW_ROOT/cw-airplay-live-v14.log" | tail -200 > "$CW_LOG_ROOT/capture.log" 2>/dev/null
cp "$CW_ROOT/cw-porsche-prime.log" "$CW_LOG_ROOT/geometry.log" 2>/dev/null
[ -z "$CW_SD_LOG" ] || {
    cp "$CW_LOG_ROOT/session.status" "$CW_SD_LOG/session.status"
    cp "$CW_LOG_ROOT/renderer.log" "$CW_SD_LOG/renderer.log" 2>/dev/null
    cp "$CW_LOG_ROOT/capture.log" "$CW_SD_LOG/capture.log" 2>/dev/null
    cp "$CW_LOG_ROOT/geometry.log" "$CW_SD_LOG/geometry.log" 2>/dev/null
}
rm -f "$CW_ROOT/cw-launcher.pid" "$CW_ROOT/cw-dio-child.pid" "$CW_ROOT/cw-supervisor.pid"
if [ "$CW_CLOSING" -eq 0 ] && [ "$CW_RESULT" -ne 0 ]; then exec "$CW_STOCK" "$@"; fi
exit "$CW_RESULT"
