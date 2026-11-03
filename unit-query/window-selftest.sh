#!/bin/sh
# Standalone diagnostics. No installation, remount, route switch or HMI restart.
set -u
if [ "${1:-}" != --mmx-child ] && [ -r /net/mmx/ifs/lsd.jxe ]; then
    SELF=$0
    case "$SELF" in /net/mmx/*) SELF=${SELF#/net/mmx};; esac
    exec on -f mmx /bin/sh "$SELF" --mmx-child
fi
[ -r /ifs/lsd.jxe ] || { echo 'ERROR: MMX firmware unavailable'; exit 1; }
case "$0" in */*) BASE=${0%/*};; *) echo 'ERROR: Use the full script path'; exit 1;; esac
LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib
export LD_LIBRARY_PATH
IPL_CONFIG_DIR=/etc/eso/production
export IPL_CONFIG_DIR
TOOL="$BASE/porsche-carplay"
[ -x "$TOOL" ] || { echo 'ERROR: Verifier unavailable'; exit 1; }
[ "$("$TOOL" --hash "$TOOL")" = '@TOOL_SHA@' ] || { echo 'ERROR: Verifier checksum differs'; exit 1; }
[ "$("$TOOL" --hash "$BASE/cw-window-selftest")" = '@TEST_SHA@' ] || { echo 'ERROR: Test checksum differs'; exit 1; }
[ "$("$TOOL" --hash "$BASE/libcw-query-stdio.so")" = '@QUERY_SHA@' ] || { echo 'ERROR: Query helper checksum differs'; exit 1; }
"$TOOL" --check-firmware || exit 1
exec "$BASE/cw-window-selftest" "$BASE" --window-selftest
