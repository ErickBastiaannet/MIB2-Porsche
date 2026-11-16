#!/bin/ksh
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
STATE=/mnt/persist/connectwow-carplay/satellite-logo-probe
BACKUP=$ROOT/before-logo-probe-20261116
function cw_hash { "$ROOT/cw-window-candidate" --hash "$1"; }
cd "$(dirname "$0")"
[ "$(cw_hash "$LSD")" = 52e32b89ffee426b71c6836356ce684eaf102b884ebddbde066c05fc3e335f08 ] || exit 1
[ "$(cw_hash lsd-logo-confirmed.sh)" = 5a7f5a087afb6699f2ba5ecb2297e2235f403db0e591164dd0749178dda2a368 ] || exit 1
[ "$(cw_hash /mnt/app/eso/hmi/connectwow-carplay/zoom-probe/PorscheCarPlayZoomLogo.probe.jar)" = 59842f9e68060680a93dcbb2eba6dbeb184dfd1295a626782b832c9905bcf542 ] || exit 1
[ "$(cw_hash "$BACKUP/lsd.sh")" = 93d7fed1102c20727a24acefbf43380001f5c9ef32319800bcbe74206d13e59e ] || exit 1
[ -s "$STATE/attempted" ] && [ ! -e "$STATE/confirmed" ] && [ ! -e "$BACKUP/lsd-logo-oneshot.sh" ] || exit 1
/bin/ksh -n lsd-logo-confirmed.sh
RW=0
CHANGED=0
function cw_cleanup {
 trap - 0
 set +e
 if [ "$CHANGED" = 1 ]; then
  cp -p "$BACKUP/lsd-logo-oneshot.sh" "$LSD.restore" && mv -f "$LSD.restore" "$LSD"
  rm -f "$STATE/confirmed"
 fi
 [ "$RW" = 0 ] || mount -ur /mnt/app
}
trap cw_cleanup 0
mount -uw /mnt/app
RW=1
cp -p "$LSD" "$BACKUP/lsd-logo-oneshot.sh"
[ "$(cw_hash "$BACKUP/lsd-logo-oneshot.sh")" = 52e32b89ffee426b71c6836356ce684eaf102b884ebddbde066c05fc3e335f08 ] || exit 1
cp -p lsd-logo-confirmed.sh "$LSD.new"
/bin/ksh -n "$LSD.new"
[ "$(cw_hash "$LSD.new")" = 5a7f5a087afb6699f2ba5ecb2297e2235f403db0e591164dd0749178dda2a368 ] || exit 1
CHANGED=1
mv -f "$LSD.new" "$LSD"
echo confirmed > "$STATE/confirmed.new"
mv -f "$STATE/confirmed.new" "$STATE/confirmed"
[ "$(cw_hash "$LSD")" = 5a7f5a087afb6699f2ba5ecb2297e2235f403db0e591164dd0749178dda2a368 ] || exit 1
[ -s "$STATE/confirmed" ] || exit 1
mount -ur /mnt/app
RW=0
CHANGED=0
trap - 0
echo SATELLITE_LOGO_CONFIRMED_NO_REBOOT
