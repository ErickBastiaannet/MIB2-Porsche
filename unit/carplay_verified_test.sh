#!/bin/sh
# Persistent Online Menu controller for Porsche K5137/MU1417 CarPlay cluster projection.
set -u
umask 077
ACTION=${1:-status}

if [ "${2:-}" != --mmx-child ] && command -v on >/dev/null 2>&1; then
    SCRIPT=$0
    case "$SCRIPT" in /net/mmx/*) SCRIPT=${SCRIPT#/net/mmx};; esac
    exec on -f mmx /bin/sh "$SCRIPT" "$ACTION" --mmx-child
fi

APP=/mnt/app
DIO=$APP/eso/bin/apps/dio_manager
LSD=$APP/eso/hmi/lsd/lsd.sh
PERSIST=$APP/eso/hmi/connectwow-carplay/v14
ROOT=/ramdisk/cw-link-probe-20261102
LOGROOT=/mnt/persist/connectwow-carplay
STOCK_SHA=9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8
LSD_STOCK_SHA=7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091

PAYLOAD=
for SD in /fs/sda0 /fs/sdb0; do
    if [ -s "$SD/online/carplay-verified/payload.manifest" ]; then PAYLOAD=$SD/online/carplay-verified; break; fi
done
TOOL=
if [ -n "$PAYLOAD" ] && [ -x "$PAYLOAD/cw-window-candidate" ]; then TOOL=$PAYLOAD/cw-window-candidate; fi
if [ -z "$TOOL" ] && [ -x "$PERSIST/cw-window-candidate" ]; then TOOL=$PERSIST/cw-window-candidate; fi

if [ "$ACTION" = status ]; then
    if [ -s "$PERSIST/enabled" ]; then echo "STATUS: permanent ingeschakeld"; else echo "STATUS: uitgeschakeld"; fi
    [ ! -s "$LOGROOT/session.status" ] || { echo "Laatste sessie:"; cat "$LOGROOT/session.status"; }
    [ ! -s "$LOGROOT/geometry.log" ] || { echo "Geometrie:"; cat "$LOGROOT/geometry.log"; }
    [ ! -s "$LOGROOT/renderer.log" ] || { echo "Renderer:"; tail -20 "$LOGROOT/renderer.log"; }
    exit 0
fi

[ "$ACTION" = enable ] || [ "$ACTION" = disable ] || { echo "ERROR: onbekende actie $ACTION"; exit 1; }
[ -n "$TOOL" ] || { echo "ERROR: geen verifier beschikbaar"; exit 1; }
[ -s "$DIO.cw-stock" ] || { echo "ERROR: OEM DIO-back-up ontbreekt"; exit 1; }
[ "$("$TOOL" --hash "$DIO.cw-stock")" = "$STOCK_SHA" ] || { echo "ERROR: OEM DIO-back-up heeft verkeerde checksum"; exit 1; }

if [ "$ACTION" = disable ]; then
    if [ -s "$ROOT/cw-supervisor.pid" ]; then read -r SUPERVISOR < "$ROOT/cw-supervisor.pid"; [ -z "$SUPERVISOR" ] || kill -TERM "$SUPERVISOR" 2>/dev/null || true; fi
    mount -uw "$APP" || { echo "ERROR: app-volume niet schrijfbaar"; exit 1; }
    cp -p "$DIO.cw-stock" "$DIO.cw-disable-restore" && mv -f "$DIO.cw-disable-restore" "$DIO" || { mount -ur "$APP"; echo "ERROR: OEM-herstel mislukt"; exit 1; }
    rm -f "$PERSIST/enabled"
    mount -ur "$APP" || { echo "ERROR: app-volume kon niet read-only worden"; exit 1; }
    rm -f "$ROOT/enabled"
    echo "UITGESCHAKELD: OEM DIO hersteld; diagnostische logs en payload bewaard."
    exit 0
fi

[ -n "$PAYLOAD" ] || { echo "ERROR: SD-payload ontbreekt voor installatie"; exit 1; }
while IFS=' ' read -r EXPECTED NAME; do
    [ "$("$TOOL" --hash "$PAYLOAD/$NAME")" = "$EXPECTED" ] || { echo "ERROR: payload beschadigd: $NAME"; exit 1; }
done < "$PAYLOAD/payload.manifest"
[ -s "$LSD" ] || { echo "ERROR: HMI-starter ontbreekt"; exit 1; }
if [ "$("$TOOL" --hash "$LSD")" != "$LSD_STOCK_SHA" ]; then
    [ -s "$LSD.cw-stock" ] && [ "$("$TOOL" --hash "$LSD.cw-stock")" = "$LSD_STOCK_SHA" ] || { echo "ERROR: OEM HMI-back-up ongeldig"; exit 1; }
fi

mount -uw "$APP" || { echo "ERROR: app-volume niet schrijfbaar"; exit 1; }
mkdir -p "$PERSIST" || { mount -ur "$APP"; echo "ERROR: persistente map kon niet worden gemaakt"; exit 1; }
cp -p "$PAYLOAD/cw-window-candidate" "$PERSIST/cw-window-candidate.new" &&
cp -p "$PAYLOAD/cw-receiver-v6.so" "$PERSIST/cw-receiver-v6.so.new" &&
cp -p "$PAYLOAD/libcw-query-stdio.so" "$PERSIST/libcw-query-stdio.so.new" &&
cp -p "$PAYLOAD/dio_manager_verified_test.sh" "$PERSIST/launcher.sh.new" &&
cp -p "$PAYLOAD/payload.manifest" "$PERSIST/payload.manifest.new" || { mount -ur "$APP"; echo "ERROR: persistente kopie mislukt"; exit 1; }
chmod 755 "$PERSIST/cw-window-candidate.new" "$PERSIST/launcher.sh.new"
while IFS=' ' read -r EXPECTED NAME; do
    TARGET=$PERSIST/$NAME.new
    [ "$NAME" != dio_manager_verified_test.sh ] || TARGET=$PERSIST/launcher.sh.new
    [ "$("$TOOL" --hash "$TARGET")" = "$EXPECTED" ] || { mount -ur "$APP"; echo "ERROR: installatiecheck mislukt: $NAME"; exit 1; }
done < "$PAYLOAD/payload.manifest"
mv -f "$PERSIST/cw-window-candidate.new" "$PERSIST/cw-window-candidate"
mv -f "$PERSIST/cw-receiver-v6.so.new" "$PERSIST/cw-receiver-v6.so"
mv -f "$PERSIST/libcw-query-stdio.so.new" "$PERSIST/libcw-query-stdio.so"
mv -f "$PERSIST/launcher.sh.new" "$PERSIST/launcher.sh"
mv -f "$PERSIST/payload.manifest.new" "$PERSIST/payload.manifest"
echo enabled > "$PERSIST/enabled"
cp -p "$PERSIST/launcher.sh" "$DIO.cw-persistent-new" && mv -f "$DIO.cw-persistent-new" "$DIO" || { rm -f "$PERSIST/enabled"; mount -ur "$APP"; echo "ERROR: launcher activeren mislukt"; exit 1; }
mount -ur "$APP" || { echo "ERROR: app-volume kon niet read-only worden"; exit 1; }
[ "$("$PERSIST/cw-window-candidate" --hash "$DIO")" = "$("$PERSIST/cw-window-candidate" --hash "$PERSIST/launcher.sh")" ] || { echo "ERROR: actieve launcher checksum klopt niet"; exit 1; }
mkdir -p "$LOGROOT"
echo "INSTALLED persistent-v14" > "$LOGROOT/session.status"
echo "INGESCHAKELD: CarPlay-clusterprojectie start voortaan automatisch bij iedere verbinding."
echo "Uitschakelen herstelt de originele Porsche DIO; status toont de laatste begrensde logs."
