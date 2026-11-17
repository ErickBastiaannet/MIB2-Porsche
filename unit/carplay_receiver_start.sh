#!/bin/sh
# MU1417 video-only receiver bootstrap. Immediate exec preserves SI PID/watchdog.
# Pattern: pinned LuKa deploy/smartphone_integrator/carplay_startup.sh.
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
STOCK=/mnt/app/eso/bin/apps/dio_manager.cw-stock
RUNTIME=/ramdisk/cw-link-probe-20261102
if [ ! -s "$ROOT/enabled" ] || [ ! -s "$ROOT/installed.manifest" ] ||
   [ ! -x "$ROOT/cw-window-candidate" ] || [ ! -s "$ROOT/cw-receiver-controls.so" ] ||
   [ ! -s "$ROOT/libcw-query-stdio.so" ]; then
    exec "$STOCK" "$@"
fi
if ! mkdir -p "$RUNTIME"; then exec "$STOCK" "$@"; fi
if ! echo enabled > "$RUNTIME/enabled"; then exec "$STOCK" "$@"; fi
echo "RECEIVER_VIDEO_BOOTSTRAP pid=$$" >> "$RUNTIME/receiver-start.log"
CARPLAY_ALTSCREEN_ENABLE=1
CARPLAY_ALTSCREEN_LOG=$RUNTIME/cw-airplay-live-v14.log
CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture
CW_AUTO_ALT_WAKE=1
CW_PROCESS_SUPERVISOR=1
# SI must start the script without this preload. Only the final receiver gets it.
LD_PRELOAD=$ROOT/cw-receiver-controls.so
export CARPLAY_ALTSCREEN_ENABLE CARPLAY_ALTSCREEN_LOG CARPLAY_ALTSCREEN_CAPTURE_DIR
export CW_AUTO_ALT_WAKE CW_PROCESS_SUPERVISOR LD_PRELOAD
# QNX's live spawn path left the supervisor's stdout/stderr on /dev/ser1.
# Establish inherited output here, before the unchanged receiver is exec'd.
# Failure to open diagnostics must never prevent stock CarPlay from starting.
if ( : >> "$RUNTIME/cw-carplay-live-v14.log" ) 2>/dev/null; then
    exec "$STOCK" "$@" >> "$RUNTIME/cw-carplay-live-v14.log" 2>&1
fi
exec "$STOCK" "$@"
