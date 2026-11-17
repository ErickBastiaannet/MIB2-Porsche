#!/bin/ksh
# MU1417: parser-only repair plus inherited diagnostics; no process restart.
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
START=/mnt/app/eso/bin/apps/cw-carplay-start
BACK=$ROOT/before-apple-source-20261117
STAGE=/ramdisk/cw-source-repair-20261117
function cw_hash { "$ROOT/cw-window-candidate" --hash "$1"; }
function check { [ "$(cw_hash "$1")" = "$2" ]; }
check "$STAGE/cw-rgi.so" a033051e84926c9a6912970771f5dbb5ee7dd124f6953898c4fdaf9f143e000e
check "$STAGE/carplay_receiver_start.sh" 19728746c841f472e37df42aa1ff617d3bca2f37fefac35486e5d0b03d4a8118
check "$ROOT/cw-rgi.so" c917554dc9027d8d0fc8044dbccf71c1ef7f5689966427b7bf122df86701e2e9
check "$START" f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e
[ ! -e "$BACK" ]
RW=0
CHANGED=0
function cleanup {
 trap - 0
 set +e
 if [ "$CHANGED" = 1 ]; then
  cp -p "$BACK/cw-rgi.so" "$ROOT/cw-rgi.so.rollback" && mv -f "$ROOT/cw-rgi.so.rollback" "$ROOT/cw-rgi.so"
  cp -p "$BACK/cw-carplay-start" "$START.rollback" && mv -f "$START.rollback" "$START"
 fi
 [ "$RW" = 0 ] || mount -ur /mnt/app
}
trap cleanup 0
mount -uw /mnt/app
RW=1
mkdir "$BACK"
cp -p "$ROOT/cw-rgi.so" "$BACK/cw-rgi.so"
cp -p "$START" "$BACK/cw-carplay-start"
check "$BACK/cw-rgi.so" c917554dc9027d8d0fc8044dbccf71c1ef7f5689966427b7bf122df86701e2e9
check "$BACK/cw-carplay-start" f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e
cp "$STAGE/cw-rgi.so" "$ROOT/cw-rgi.so.new"
cp "$STAGE/carplay_receiver_start.sh" "$START.new"
chmod 755 "$ROOT/cw-rgi.so.new" "$START.new"
check "$ROOT/cw-rgi.so.new" a033051e84926c9a6912970771f5dbb5ee7dd124f6953898c4fdaf9f143e000e
check "$START.new" 19728746c841f472e37df42aa1ff617d3bca2f37fefac35486e5d0b03d4a8118
CHANGED=1
mv -f "$ROOT/cw-rgi.so.new" "$ROOT/cw-rgi.so"
mv -f "$START.new" "$START"
check "$ROOT/cw-rgi.so" a033051e84926c9a6912970771f5dbb5ee7dd124f6953898c4fdaf9f143e000e
check "$START" 19728746c841f472e37df42aa1ff617d3bca2f37fefac35486e5d0b03d4a8118
mount -ur /mnt/app
RW=0
CHANGED=0
trap - 0
echo SOURCE_ALIAS_REPAIR_INSTALLED_RESTART_REQUIRED
