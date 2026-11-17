#!/bin/ksh
# Exact-profile fresh installation; no implicit reboot and no hard-coded vehicle identity.
set -eu
umask 077
ACTION=${1:-status}
if [ "${2:-}" != --mmx-child ] && [ -r /net/mmx/ifs/lsd.jxe ]; then
 SCRIPT=$0
 case "$SCRIPT" in /net/mmx/*) SCRIPT=${SCRIPT#/net/mmx};; esac
 exec on -f mmx /bin/ksh "$SCRIPT" "$ACTION" --mmx-child
fi
APP=/mnt/app
SYSTEM=/mnt/system
BASE=$APP/eso/hmi/connectwow-carplay
ROOT=$BASE/controls-v15
STATE=/mnt/persist/connectwow-carplay/portable
GSTATE=/mnt/persist/connectwow-carplay/guidance-native
DIO=$APP/eso/bin/apps/dio_manager
LSD=$APP/eso/hmi/lsd/lsd.sh
START=$APP/eso/bin/apps/cw-carplay-start
IPOD=$APP/armle/usr/sbin/mm-ipod
REAL=$APP/armle/usr/sbin/connectwow-rgi/mm-ipod
SI=$SYSTEM/etc/eso/production/smartphone_integrator.json
IAP=$SYSTEM/etc/mm/iap2.cfg
DISPLAY=$SYSTEM/etc/eso/production/displaymanager.json
PAYLOAD=
for SD in /fs/sda0 /fs/sdb0; do
 if [ -s "$SD/online/cw-release/payload.manifest" ]; then PAYLOAD=$SD/online/cw-release; break; fi
done
function fail { print "ERROR: $*"; exit 1; }
[ -n "$PAYLOAD" ] || fail 'Release ontbreekt op SD'
TOOL=$PAYLOAD/cw-window-candidate
function cw_hash { "$TOOL" --hash "$1"; }
function check { [ "$(cw_hash "$1")" = "$2" ] || fail "Onbekend of beschadigd: $1"; }
function copy_checked { cp -p "$1" "$2" && [ "$(cw_hash "$1")" = "$(cw_hash "$2")" ]; }
function stage { copy_checked "$1" "$2.cw-new" && mv -f "$2.cw-new" "$2"; }
check "$PAYLOAD/payload.manifest" @MANIFEST_SHA@
while IFS=' ' read -r EXPECTED NAME; do
 case "$NAME" in ''|*/*|*..*) fail 'Ongeldige payloadnaam';; esac
 check "$PAYLOAD/$NAME" "$EXPECTED"
done < "$PAYLOAD/payload.manifest"
RECOVERY=$PAYLOAD/recovery
case "$ACTION" in
status)
 if [ -s "$STATE/confirmed" ]; then print 'Portable release permanent bevestigd'
 elif [ -s "$STATE/attempted" ]; then print 'Eenmalige proef gestart; nog niet bevestigd'
 elif [ -s "$STATE/pending" ]; then print 'Eenmalige proef klaar; herstart vereist'
 else print 'Portable release niet geinstalleerd'; fi
 exit 0;;
reboot)
 print 'Alleen stilstaand gebruiken: volledige PCM-herstart'
 exec on -f rcc /usr/apps/mib2_ioc_flash reboot;;
logs)
 OUT=$PAYLOAD/diagnostics
 mkdir -p "$OUT"
 for F in cw-navigation-priority.log cw-nav-priority.v1 cw-nav-priority.applied cw-porsche-rgi-java.log cw-porsche-rgi.log cw-carplay-ready.v1; do
  [ ! -f "/ramdisk/$F" ] || cp "/ramdisk/$F" "$OUT/$F"
 done
 for F in cw-carplay-live-v14.log receiver-start.log; do
  [ ! -f "/ramdisk/cw-link-probe-20261102/$F" ] || cp "/ramdisk/cw-link-probe-20261102/$F" "$OUT/$F"
 done
 print 'Diagnostiek op SD: online/cw-release/diagnostics'
 exit 0;;
confirm)
 [ -s "$STATE/attempted" ] || fail 'Eerst een proefboot uitvoeren en fysiek controleren'
 @INSTALLED_CHECKS@
 for TARGET in "$STATE" "$GSTATE"; do
  print confirmed > "$TARGET/confirmed.new"
  mv -f "$TARGET/confirmed.new" "$TARGET/confirmed"
 done
 print 'Permanent bevestigd; geen herstart nodig'
 exit 0;;
install|check|restore) :;;
*) fail 'Onbekende actie';;
esac
APP_RW=0
SYS_RW=0
CHANGED=0
RESTORING=0
NEW_DIO=0
NEW_LSD=0
LOCK=/ramdisk/cw-portable-install.lock
function cleanup {
 RC=$?
 trap - 0
 set +e
 ROLLBACK_OK=1
 if [ "$CHANGED" = 1 ]; then
  mount -uw "$APP" || ROLLBACK_OK=0; APP_RW=1
  mount -uw "$SYSTEM" || ROLLBACK_OK=0; SYS_RW=1
  if [ "$RESTORING" = 1 ]; then
   stage "$LOCK/lsd.sh" "$LSD" || ROLLBACK_OK=0
   stage "$LOCK/mm-ipod" "$IPOD" || ROLLBACK_OK=0
   stage "$LOCK/si.json" "$SI" || ROLLBACK_OK=0
   stage "$LOCK/iap2.cfg" "$IAP" || ROLLBACK_OK=0
  else
  stage "$RECOVERY/lsd.sh" "$LSD" || ROLLBACK_OK=0
  stage "$RECOVERY/mm-ipod" "$IPOD" || ROLLBACK_OK=0
  stage "$RECOVERY/smartphone_integrator.json" "$SI" || ROLLBACK_OK=0
  stage "$RECOVERY/iap2.cfg" "$IAP" || ROLLBACK_OK=0
  if [ "$ROLLBACK_OK" = 1 ]; then
  rm -f "$START"
  rm -rf "$BASE" "$APP/armle/usr/sbin/connectwow-rgi"
  [ "$NEW_DIO" = 0 ] || rm -f "$DIO.cw-stock"
  [ "$NEW_LSD" = 0 ] || rm -f "$LSD.cw-stock"
  rm -rf "$STATE" "$GSTATE"
  fi
  fi
  if [ "$ROLLBACK_OK" = 1 ]; then
   print 'Actie afgebroken; oorspronkelijke bestanden teruggezet'
  else
   print 'ERROR: herstel niet volledig; behoud SD-herstelmap en controleer de unit'
  fi
 fi
 rm -f "$LSD.cw-new" "$SI.cw-new" "$IAP.cw-new" "$IPOD.cw-new"
 [ "$SYS_RW" = 0 ] || mount -ur "$SYSTEM"
 [ "$APP_RW" = 0 ] || mount -ur "$APP"
 rm -rf "$LOCK"
 exit "$RC"
}
# Both configuration contents and ABI are firmware-specific. Unknown targets fail before mount.
check "$DISPLAY" 115df2ffd860a6adccd4dd10c643a13b575a439922b272942025df8c7c246202
if [ "$ACTION" = restore ]; then
 check "$RECOVERY/lsd.sh" 7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091
 check "$RECOVERY/mm-ipod" d5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464
 check "$RECOVERY/smartphone_integrator.json" a1ac27b4f405346548e8e1bec82b1f5c3483dc73050d682ad4c9a80808f7cbc7
 check "$RECOVERY/iap2.cfg" d6d50af974a82feec2add942d3d8e6e88f96a2c25c469f747a11954b1c3445d7
 @RESTORE_CHECKS@
 mkdir "$LOCK" || fail 'Installatie/herstel al actief'
 trap cleanup 0
 trap 'exit 1' 1 2 15
 copy_checked "$LSD" "$LOCK/lsd.sh"
 copy_checked "$IPOD" "$LOCK/mm-ipod"
 copy_checked "$SI" "$LOCK/si.json"
 copy_checked "$IAP" "$LOCK/iap2.cfg"
 RESTORING=1
 mount -uw "$APP"; APP_RW=1
 mount -uw "$SYSTEM"; SYS_RW=1
 CHANGED=1
 stage "$RECOVERY/lsd.sh" "$LSD"
 stage "$RECOVERY/mm-ipod" "$IPOD"
 stage "$RECOVERY/smartphone_integrator.json" "$SI"
 stage "$RECOVERY/iap2.cfg" "$IAP"
 mount -ur "$SYSTEM"; SYS_RW=0
 mount -ur "$APP"; APP_RW=0
 CHANGED=0
 rm -f "$STATE/confirmed" "$STATE/pending" "$GSTATE/confirmed" "$GSTATE/pending"
 print 'Porsche OEM-startbestanden hersteld; kies afzonderlijk Herstart PCM'
 exit 0
fi
check "$DIO" 9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8
check "$LSD" 7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091
check "$IPOD" d5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464
check "$SI" a1ac27b4f405346548e8e1bec82b1f5c3483dc73050d682ad4c9a80808f7cbc7
check "$IAP" d6d50af974a82feec2add942d3d8e6e88f96a2c25c469f747a11954b1c3445d7
[ ! -e "$BASE" ] && [ ! -e "$START" ] && [ ! -e "$APP/armle/usr/sbin/connectwow-rgi" ] || fail 'Bestaande installatie: dit pakket is uitsluitend voor een schone unit'
[ ! -e "$STATE" ] && [ ! -e "$GSTATE" ] || fail 'Bestaande activatiestatus; niet overschrijven'
[ ! -e "$DIO.cw-stock" ] || check "$DIO.cw-stock" 9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8
[ ! -e "$LSD.cw-stock" ] || check "$LSD.cw-stock" 7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091
/bin/ksh -n "$PAYLOAD/hmi-start.sh"
/bin/ksh -n "$PAYLOAD/cw-carplay-start"
/bin/ksh -n "$PAYLOAD/mm-ipod.sh"
/bin/ksh "$PAYLOAD/link-check.sh"
if [ "$ACTION" = check ]; then print 'PROFIEL EN J9 CONTROLE GESLAAGD; niets geinstalleerd'; exit 0; fi
[ ! -e "$RECOVERY" ] || fail 'Herstelmap op SD bestaat al; niet overschrijven'
mkdir "$LOCK" || fail 'Installatie/herstel al actief'
trap cleanup 0
trap 'exit 1' 1 2 15
mkdir "$RECOVERY"
copy_checked "$LSD" "$RECOVERY/lsd.sh"
copy_checked "$IPOD" "$RECOVERY/mm-ipod"
copy_checked "$SI" "$RECOVERY/smartphone_integrator.json"
copy_checked "$IAP" "$RECOVERY/iap2.cfg"
mount -uw "$APP"; APP_RW=1
mount -uw "$SYSTEM"; SYS_RW=1
CHANGED=1
mkdir -p "$ROOT" "$APP/armle/usr/sbin/connectwow-rgi"
for F in cw-window-candidate cw-receiver-controls.so cw-rgi.so libcw-query-stdio.so PorscheNavigationPriority.test.jar; do
 copy_checked "$PAYLOAD/$F" "$ROOT/$F"
done
chmod 755 "$ROOT/cw-window-candidate"
copy_checked "$PAYLOAD/payload.manifest" "$ROOT/installed.manifest"
if [ ! -e "$DIO.cw-stock" ]; then NEW_DIO=1; copy_checked "$DIO" "$DIO.cw-stock"; fi
if [ ! -e "$LSD.cw-stock" ]; then NEW_LSD=1; copy_checked "$LSD" "$LSD.cw-stock"; fi
copy_checked "$IPOD" "$REAL"
copy_checked "$PAYLOAD/cw-carplay-start" "$START"
chmod 755 "$START" "$REAL" "$DIO.cw-stock"
CHANGED=1
stage "$PAYLOAD/hmi-start.sh" "$LSD"
stage "$PAYLOAD/mm-ipod.sh" "$IPOD"
stage "$PAYLOAD/smartphone_integrator.json" "$SI"
stage "$PAYLOAD/iap2.cfg" "$IAP"
chmod 755 "$LSD" "$IPOD"
@INSTALLED_CHECKS@
mkdir -p "$STATE" "$GSTATE"
print enabled > "$ROOT/enabled"
print pending > "$STATE/pending"
print pending > "$GSTATE/pending"
mount -ur "$SYSTEM"; SYS_RW=0
mount -ur "$APP"; APP_RW=0
CHANGED=0
print 'INSTALLATIE GESLAAGD: eenmalige proef klaar. Kies afzonderlijk Herstart PCM.'
