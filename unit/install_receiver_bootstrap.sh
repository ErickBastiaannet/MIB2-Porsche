#!/bin/ksh
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
CONFIG=/mnt/system/etc/eso/production/smartphone_integrator.json
BACKUP=$ROOT/before-video-bootstrap-20261116
START=/mnt/app/eso/bin/apps/cw-carplay-start
function cw_hash { "$ROOT/cw-window-candidate" --hash "$1"; }
cd "$(dirname "$0")"
[ "$(cw_hash "$CONFIG")" = e042e65da4f366fef35c700528c7054fcf7f6e38dba23f7c291928895d91cb86 ] || exit 1
[ "$(cw_hash smartphone-video-bootstrap.json)" = 722b47123494e22b8fa4b4e50b3cce07f5b0399f1f31c7fd5e8f51ff981350d9 ] || exit 1
[ "$(cw_hash carplay_receiver_start.sh)" = f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e ] || exit 1
[ "$(cw_hash "$ROOT/cw-window-candidate")" = 41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce ] || exit 1
[ "$(cw_hash "$ROOT/cw-receiver-controls.so")" = c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847 ] || exit 1
[ ! -e "$BACKUP" ] && [ ! -e "$START" ] || exit 1
APP_RW=0
SYS_RW=0
START_CHANGED=0
CONFIG_CHANGED=0
function cw_cleanup {
 trap - 0
 set +e
 if [ "$CONFIG_CHANGED" = 1 ]; then
  cp -p "$BACKUP/smartphone_integrator.json" "$CONFIG.rollback" && mv -f "$CONFIG.rollback" "$CONFIG"
 fi
 if [ "$START_CHANGED" = 1 ]; then rm -f "$START"; fi
 [ "$SYS_RW" = 0 ] || mount -ur /mnt/system
 [ "$APP_RW" = 0 ] || mount -ur /mnt/app
}
trap cw_cleanup 0
mount -uw /mnt/app
APP_RW=1
mount -uw /mnt/system
SYS_RW=1
mkdir "$BACKUP"
cp -p "$CONFIG" "$BACKUP/smartphone_integrator.json"
[ "$(cw_hash "$BACKUP/smartphone_integrator.json")" = e042e65da4f366fef35c700528c7054fcf7f6e38dba23f7c291928895d91cb86 ] || exit 1
cp carplay_receiver_start.sh "$START.new"
chmod 755 "$START.new"
cp -p smartphone-video-bootstrap.json "$CONFIG.new"
chmod 644 "$CONFIG.new"
[ "$(cw_hash "$START.new")" = f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e ] || exit 1
[ "$(cw_hash "$CONFIG.new")" = 722b47123494e22b8fa4b4e50b3cce07f5b0399f1f31c7fd5e8f51ff981350d9 ] || exit 1
START_CHANGED=1
mv -f "$START.new" "$START"
CONFIG_CHANGED=1
mv -f "$CONFIG.new" "$CONFIG"
[ "$(cw_hash "$START")" = f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e ] || exit 1
[ "$(cw_hash "$CONFIG")" = 722b47123494e22b8fa4b4e50b3cce07f5b0399f1f31c7fd5e8f51ff981350d9 ] || exit 1
mount -ur /mnt/system
SYS_RW=0
mount -ur /mnt/app
APP_RW=0
CONFIG_CHANGED=0
START_CHANGED=0
trap - 0
echo VIDEO_BOOTSTRAP_INSTALLED_RESTART_REQUIRED
