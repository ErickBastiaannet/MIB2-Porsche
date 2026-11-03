#!/bin/sh
# Transactional profile switcher for Porsche K5137/MU1417.
set -u
umask 077
ACTION=${1:-status}

if [ "${2:-}" != --mmx-child ] && [ -r /net/mmx/ifs/lsd.jxe ]; then
    command -v on >/dev/null 2>&1 || { echo "ERROR: MMX dispatch unavailable"; exit 1; }
    SCRIPT=$0
    case "$SCRIPT" in /net/mmx/*) SCRIPT=${SCRIPT#/net/mmx};; esac
    exec on -f mmx /bin/sh "$SCRIPT" "$ACTION" --mmx-child
fi

APP=/mnt/app
DIO=$APP/eso/bin/apps/dio_manager
LSD=$APP/eso/hmi/lsd/lsd.sh
ROOT=$APP/eso/hmi/connectwow-carplay
STABLE=$ROOT/v14
CONTROLS=$ROOT/controls-v15
DIO_STOCK_SHA=9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8
LSD_STOCK_SHA=7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091
PAYLOAD=
for SD in /fs/sda0 /fs/sdb0; do
    if [ -s "$SD/online/carplay-profiles/stable/payload.manifest" ]; then
        PAYLOAD=$SD/online/carplay-profiles
        break
    fi
done

fail() { echo "ERROR: $*"; exit 1; }
rw() { mount -uw "$APP"; }
ro() { mount -ur "$APP"; }
reboot_unit() {
    echo "Installatie geslaagd. De unit herstart over 5 seconden."
    echo "5"; sleep 1
    echo "4"; sleep 1
    echo "3"; sleep 1
    echo "2"; sleep 1
    echo "1"; sleep 1
    on -f rcc /usr/apps/mib2_ioc_flash reboot || fail "Herstartopdracht mislukt; herstart de unit handmatig"
    echo "Herstartopdracht verzonden"
}

if [ "$ACTION" = status ]; then
    if [ -s "$CONTROLS/confirmed" ]; then echo "Profiel: Controls V15 bevestigd"
    elif [ -s "$CONTROLS/attempted" ]; then echo "Profiel: Controls V15 proefboot niet bevestigd; volgende boot gebruikt stock-HMI"
    elif [ -s "$CONTROLS/pending" ]; then echo "Profiel: Controls V15 klaar voor eenmalige proefboot"
    elif [ -s "$STABLE/enabled" ]; then echo "Profiel: Stable V14"
    else echo "Profiel: OEM"; fi
    [ ! -s /mnt/persist/connectwow-carplay/session.status ] || cat /mnt/persist/connectwow-carplay/session.status
    exit 0
fi

[ -n "$PAYLOAD" ] || fail "CarPlay-profielen ontbreken op SD"
TOOL=$PAYLOAD/stable/cw-window-candidate
[ -x "$TOOL" ] || fail "Verifier ontbreekt"
hash() { "$TOOL" --hash "$1"; }
verify_payload() {
    BASE=$1
    EXPECTED_MANIFEST=$2
    [ "$(hash "$BASE/payload.manifest")" = "$EXPECTED_MANIFEST" ] || return 1
    while IFS=' ' read -r EXPECTED NAME; do
        case "$NAME" in */*|*..*) return 1;; esac
        [ "$(hash "$BASE/$NAME")" = "$EXPECTED" ] || return 1
    done < "$BASE/payload.manifest"
}
verify_payload "$PAYLOAD/stable" '@STABLE_MANIFEST_SHA@' || fail "Stable V14-payload beschadigd"
verify_payload "$PAYLOAD/controls" '@CONTROLS_MANIFEST_SHA@' || fail "Controls V15-payload beschadigd"
[ "$(hash "$TOOL")" = '@VERIFIER_SHA@' ] || fail "Onbekende verifier"

ensure_stock() {
    [ -s "$DIO.cw-stock" ] || fail "OEM DIO-back-up ontbreekt"
    [ -s "$LSD.cw-stock" ] || fail "OEM HMI-back-up ontbreekt"
    [ "$(hash "$DIO.cw-stock")" = "$DIO_STOCK_SHA" ] || fail "OEM DIO-back-up ongeldig"
    [ "$(hash "$LSD.cw-stock")" = "$LSD_STOCK_SHA" ] || fail "OEM HMI-back-up ongeldig"
}
stage_file() {
    SOURCE=$1
    TARGET=$2
    cp -p "$SOURCE" "$TARGET.cw-new" || return 1
    mv -f "$TARGET.cw-new" "$TARGET" || return 1
}

case "$ACTION" in
install-stable)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$STABLE" || { ro; fail "Stable-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-v6.so libcw-query-stdio.so stable-launcher.sh payload.manifest; do
        cp -p "$PAYLOAD/stable/$NAME" "$STABLE/$NAME" || { ro; fail "Kopieren mislukt: $NAME"; }
    done
    mv -f "$STABLE/stable-launcher.sh" "$STABLE/launcher.sh" || { ro; fail "Stable-launcher ontbreekt"; }
    chmod 755 "$STABLE/cw-window-candidate" "$STABLE/launcher.sh"
    echo enabled > "$STABLE/enabled"
    rm -f "$CONTROLS/enabled" "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    stage_file "$LSD.cw-stock" "$LSD" || { ro; fail "OEM HMI-herstel mislukt"; }
    stage_file "$STABLE/launcher.sh" "$DIO" || { ro; fail "Stable DIO-installatie mislukt"; }
    ro || fail "Appvolume niet read-only"
    echo "Stable V14 actief na herstart"
    ;;
install-controls)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$CONTROLS" || { ro; fail "Controls-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-controls.so cw-rgi.so libcw-query-stdio.so controls-launcher.sh lsd-controls.sh PorscheCarPlayBridge.experimental.jar payload.manifest; do
        cp -p "$PAYLOAD/controls/$NAME" "$CONTROLS/$NAME" || { ro; fail "Kopieren mislukt: $NAME"; }
    done
    mv -f "$CONTROLS/controls-launcher.sh" "$CONTROLS/launcher.sh" || { ro; fail "Controls-launcher ontbreekt"; }
    chmod 755 "$CONTROLS/cw-window-candidate" "$CONTROLS/launcher.sh" "$CONTROLS/lsd-controls.sh"
    echo enabled > "$CONTROLS/enabled"
    echo pending > "$CONTROLS/pending"
    rm -f "$CONTROLS/attempted" "$CONTROLS/confirmed"
    stage_file "$CONTROLS/lsd-controls.sh" "$LSD" || { ro; fail "Controls HMI-starter mislukt"; }
    stage_file "$CONTROLS/launcher.sh" "$DIO" || { ro; fail "Controls DIO-starter mislukt"; }
    ro || fail "Appvolume niet read-only"
    echo "Controls V15 klaar voor de proefboot. Bevestig alleen als PCM, CarPlay, zoom en pijlen werken."
    reboot_unit
    ;;
confirm-controls)
    [ -s "$CONTROLS/enabled" ] || fail "Controls V15 niet geinstalleerd"
    rw || fail "Appvolume niet schrijfbaar"
    echo confirmed > "$CONTROLS/confirmed" || { ro; fail "Bevestiging mislukt"; }
    rm -f "$CONTROLS/pending" "$CONTROLS/attempted"
    ro || fail "Appvolume niet read-only"
    echo "Controls V15 bevestigd voor volgende boots"
    ;;
restore-oem)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    rm -f "$STABLE/enabled" "$CONTROLS/enabled" "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    stage_file "$LSD.cw-stock" "$LSD" || { ro; fail "OEM HMI-herstel mislukt"; }
    stage_file "$DIO.cw-stock" "$DIO" || { ro; fail "OEM DIO-herstel mislukt"; }
    ro || fail "Appvolume niet read-only"
    echo "Volledig OEM actief na herstart"
    ;;
*) fail "Onbekende actie: $ACTION";;
esac
