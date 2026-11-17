#!/bin/ksh
# Native startup-only replacement. Does not stop or restart any process.
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
TOOL=$ROOT/cw-window-candidate
STAGE=/ramdisk/cw-context-startup-20261117
BACK=$ROOT/before-context-startup-20261117
function cw_hash { "$TOOL" --hash "$1"; }
[ "$(cw_hash "$TOOL")" = 41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce ]
[ "$(cw_hash "$STAGE/cw-window-startup")" = 6e7fcdaad2aef40cf9381f6a08374b58501044d63d091ad64957921f8a426d9f ]
[ ! -e "$BACK" ]
RW=0
CHANGED=0
function cleanup {
 trap - 0
 set +e
 if [ "$CHANGED" = 1 ]; then
  cp -p "$BACK/cw-window-candidate" "$TOOL.rollback" && mv -f "$TOOL.rollback" "$TOOL"
 fi
 [ "$RW" = 0 ] || mount -ur /mnt/app
}
trap cleanup 0
mount -uw /mnt/app
RW=1
mkdir "$BACK"
cp -p "$TOOL" "$BACK/cw-window-candidate"
[ "$(cw_hash "$BACK/cw-window-candidate")" = 41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce ]
cp "$STAGE/cw-window-startup" "$TOOL.new"
chmod 755 "$TOOL.new"
[ "$(cw_hash "$TOOL.new")" = 6e7fcdaad2aef40cf9381f6a08374b58501044d63d091ad64957921f8a426d9f ]
CHANGED=1
mv -f "$TOOL.new" "$TOOL"
[ "$(cw_hash "$TOOL")" = 6e7fcdaad2aef40cf9381f6a08374b58501044d63d091ad64957921f8a426d9f ]
mount -ur /mnt/app
RW=0
CHANGED=0
trap - 0
echo CONTEXT_STARTUP_INSTALLED_NEXT_RECEIVER_START
