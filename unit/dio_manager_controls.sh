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

if [ ! -s "$CW_PERSIST/enabled" ] || [ ! -s "$CW_PERSIST/installed.manifest" ] ||
   [ ! -x "$CW_PERSIST/cw-window-candidate" ] ||
   [ ! -s "$CW_PERSIST/cw-receiver-controls.so" ] ||
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
cp "$CW_PERSIST/libcw-query-stdio.so" "$CW_ROOT/libcw-query-stdio.so" || exec "$CW_STOCK" "$@"
chmod 755 "$CW_ROOT/cw-window-candidate" || exec "$CW_STOCK" "$@"
rm -f "$CW_ROOT/cw-carplay-live-v14.log" "$CW_ROOT/cw-airplay-live-v14.log" "$CW_ROOT/cw-porsche-prime.log"
echo "START profile=15 launcher=$$" > "$CW_LOG_ROOT/session.status"
[ -z "$CW_SD_LOG" ] || cp "$CW_LOG_ROOT/session.status" "$CW_SD_LOG/session.status"
echo "DYNAMIC_PREFLIGHT enabled" > "$CW_ROOT/cw-porsche-prime.log"

# Bind lifetime to the actual OEM receiver. The receiver constructor starts
# the video supervisor; no shell parent survives with a stale child PID.
CARPLAY_ALTSCREEN_ENABLE=1
CARPLAY_ALTSCREEN_LOG=$CW_ROOT/cw-airplay-live-v14.log
CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture
CW_AUTO_ALT_WAKE=1
CW_PROCESS_SUPERVISOR=1
LD_PRELOAD="$CW_ROOT/cw-receiver-controls.so${LD_PRELOAD:+:$LD_PRELOAD}"
export CARPLAY_ALTSCREEN_ENABLE CARPLAY_ALTSCREEN_LOG CARPLAY_ALTSCREEN_CAPTURE_DIR
export CW_AUTO_ALT_WAKE CW_PROCESS_SUPERVISOR LD_PRELOAD
exec "$CW_STOCK" "$@"
