#!/bin/ksh
# Transactional profile switcher for Porsche K5137/MU1417.
set -u
umask 077
ACTION=${1:-status}

if [ "${2:-}" != --mmx-child ] && [ -r /net/mmx/ifs/lsd.jxe ]; then
    command -v on >/dev/null 2>&1 || { echo "ERROR: MMX dispatch unavailable"; exit 1; }
    SCRIPT=$0
    case "$SCRIPT" in /net/mmx/*) SCRIPT=${SCRIPT#/net/mmx};; esac
    exec on -f mmx /bin/ksh "$SCRIPT" "$ACTION" --mmx-child
fi

APP=/mnt/app
DIO=$APP/eso/bin/apps/dio_manager
LSD=$APP/eso/hmi/lsd/lsd.sh
ROOT=$APP/eso/hmi/connectwow-carplay
STABLE=$ROOT/v14
V145=$ROOT/v14-5
V146=$ROOT/v14-6
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

function fail { echo "ERROR: $*"; exit 1; }
function rw { mount -uw "$APP"; }
function ro { mount -ur "$APP"; }
function reboot_unit {
    # Never keep the engineering-menu Java caller waiting for the RCC reboot.
    # The detached command gets no menu pipes, so the wrapper can return at once.
    echo "Installatie geslaagd. Herstartopdracht wordt verzonden."
    on -f rcc /usr/apps/mib2_ioc_flash reboot </dev/null >/dev/null 2>&1 &
    echo "Herstartopdracht verzonden; het menu mag nu worden gesloten"
    exit 0
}

if [ "$ACTION" = status ]; then
    if [ -s "$CONTROLS/confirmed" ]; then echo "Profiel: Controls V15 bevestigd"
    elif [ -s "$CONTROLS/attempted" ]; then echo "Profiel: Controls V15 proefboot niet bevestigd; volgende boot gebruikt stock-HMI"
    elif [ -s "$CONTROLS/pending" ]; then echo "Profiel: Controls V15 klaar voor eenmalige proefboot"
    elif [ -s "$V146/confirmed" ]; then echo "Profiel: V14.6 meldingen bevestigd"
    elif [ -s "$V146/attempted" ]; then echo "Profiel: V14.6 proefboot niet bevestigd; volgende boot gebruikt stock-HMI"
    elif [ -s "$V146/pending" ]; then echo "Profiel: V14.6 klaar voor eenmalige proefboot"
    elif [ -s "$V145/enabled" ]; then echo "Profiel: V14.5 dag/nacht, beginzoom en logging"
    elif [ -s "$STABLE/enabled" ]; then echo "Profiel: Stable V14"
    else echo "Profiel: OEM"; fi
    [ ! -s /mnt/persist/connectwow-carplay/session.status ] || cat /mnt/persist/connectwow-carplay/session.status
    exit 0
fi

[ -n "$PAYLOAD" ] || fail "CarPlay-profielen ontbreken op SD"
TOOL=$PAYLOAD/stable/cw-window-candidate
[ -x "$TOOL" ] || fail "Verifier ontbreekt"
function hash_file { "$TOOL" --hash "$1"; }
function verify_payload {
    BASE=$1
    EXPECTED_MANIFEST=$2
    [ "$(hash_file "$BASE/payload.manifest")" = "$EXPECTED_MANIFEST" ] || return 1
    while IFS=' ' read -r EXPECTED NAME; do
        case "$NAME" in */*|*..*) return 1;; esac
        [ "$(hash_file "$BASE/$NAME")" = "$EXPECTED" ] || return 1
    done < "$BASE/payload.manifest"
}
[ "$(hash_file "$TOOL")" = '@VERIFIER_SHA@' ] || fail "Onbekende verifier"

case "$ACTION" in
install-stable) verify_payload "$PAYLOAD/stable" '@STABLE_MANIFEST_SHA@' || fail "Stable V14-payload beschadigd";;
install-v145) verify_payload "$PAYLOAD/v145" '@V145_MANIFEST_SHA@' || fail "V14.5-payload beschadigd";;
install-v146) verify_payload "$PAYLOAD/v146" '@V146_MANIFEST_SHA@' || fail "V14.6-payload beschadigd";;
install-controls) verify_payload "$PAYLOAD/controls" '@CONTROLS_MANIFEST_SHA@' || fail "Controls V15-payload beschadigd";;
esac

function ensure_stock {
    [ -s "$DIO.cw-stock" ] || fail "OEM DIO-back-up ontbreekt"
    [ -s "$LSD.cw-stock" ] || fail "OEM HMI-back-up ontbreekt"
    [ "$(hash_file "$DIO.cw-stock")" = "$DIO_STOCK_SHA" ] || fail "OEM DIO-back-up ongeldig"
    [ "$(hash_file "$LSD.cw-stock")" = "$LSD_STOCK_SHA" ] || fail "OEM HMI-back-up ongeldig"
}
function stage_file {
    SOURCE=$1
    TARGET=$2
    cp -p "$SOURCE" "$TARGET.cw-new" || return 1
    mv -f "$TARGET.cw-new" "$TARGET" || return 1
}
function copy_checked {
    SOURCE=$1
    TARGET=$2
    cp -p "$SOURCE" "$TARGET" || return 1
    [ "$(hash_file "$TARGET")" = "$(hash_file "$SOURCE")" ] || return 1
}
function begin_switch {
    cp -p "$DIO" "$ROOT/.switch-dio" || return 1
    cp -p "$LSD" "$ROOT/.switch-lsd" || { rm -f "$ROOT/.switch-dio"; return 1; }
}
function rollback_switch {
    stage_file "$ROOT/.switch-lsd" "$LSD" 2>/dev/null
    stage_file "$ROOT/.switch-dio" "$DIO" 2>/dev/null
    rm -f "$ROOT/.switch-lsd" "$ROOT/.switch-dio"
}
function finish_switch {
    rm -f "$ROOT/.switch-lsd" "$ROOT/.switch-dio"
}

case "$ACTION" in
collect-logs)
    SDROOT=${PAYLOAD%/online/carplay-profiles}
    OUT=$SDROOT/connectwow-carplay-logs/diagnostics-latest
    mkdir -p "$OUT" || fail "Diagnostiekmap op SD kon niet worden gemaakt"
    {
        echo "firmware=MHI2_ER_POG24_K5137_MU1417"
        echo "action=collect-logs"
        if [ -s "$CONTROLS/confirmed" ]; then echo "profile=v15-confirmed"
        elif [ -s "$CONTROLS/attempted" ]; then echo "profile=v15-attempted"
        elif [ -s "$CONTROLS/pending" ]; then echo "profile=v15-pending"
        elif [ -s "$V146/confirmed" ]; then echo "profile=v14.6-confirmed"
        elif [ -s "$V146/attempted" ]; then echo "profile=v14.6-attempted"
        elif [ -s "$V146/pending" ]; then echo "profile=v14.6-pending"
        elif [ -s "$V145/enabled" ]; then echo "profile=v14.5"
        elif [ -s "$STABLE/enabled" ]; then echo "profile=v14"
        else echo "profile=oem"; fi
        [ ! -s "$DIO" ] || echo "dio_sha=$(hash_file "$DIO")"
        [ ! -s "$LSD" ] || echo "lsd_sha=$(hash_file "$LSD")"
    } > "$OUT/profile.txt"
    for NAME in session.status renderer.log capture.log geometry.log; do
        [ ! -s "/mnt/persist/connectwow-carplay/$NAME" ] || cp "/mnt/persist/connectwow-carplay/$NAME" "$OUT/$NAME"
    done
    command -v pidin >/dev/null 2>&1 && pidin ar > "$OUT/processes.txt" 2>&1
    for PROFILE_LOG in v14-5 v14-6 v15; do
        [ ! -d "$SDROOT/connectwow-carplay-logs/$PROFILE_LOG" ] || cp -r "$SDROOT/connectwow-carplay-logs/$PROFILE_LOG" "$OUT/$PROFILE_LOG"
    done
    echo "Diagnostiek opgeslagen in connectwow-carplay-logs/diagnostics-latest"
    exit 0
    ;;
install-stable)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$STABLE" || { ro; fail "Stable-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-v6.so libcw-query-stdio.so stable-launcher.sh payload.manifest; do
        copy_checked "$PAYLOAD/stable/$NAME" "$STABLE/$NAME" || { ro; fail "Kopieren of nacontrole mislukt: $NAME"; }
    done
    mv -f "$STABLE/stable-launcher.sh" "$STABLE/launcher.sh" || { ro; fail "Stable-launcher ontbreekt"; }
    chmod 755 "$STABLE/cw-window-candidate" "$STABLE/launcher.sh"
    echo enabled > "$STABLE/enabled"
    rm -f "$V145/enabled" "$V146/enabled" "$V146/pending" "$V146/attempted" "$V146/confirmed" "$CONTROLS/enabled" "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    begin_switch || { ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    stage_file "$LSD.cw-stock" "$LSD" || { rollback_switch; ro; fail "OEM HMI-herstel mislukt"; }
    stage_file "$STABLE/launcher.sh" "$DIO" || { rollback_switch; ro; fail "Stable DIO-installatie mislukt"; }
    finish_switch
    ro || fail "Appvolume niet read-only"
    echo "Stable V14 actief na herstart"
    ;;
install-v145)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$V145" || { ro; fail "V14.5-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-v145.so libcw-query-stdio.so v145-launcher.sh payload.manifest; do
        copy_checked "$PAYLOAD/v145/$NAME" "$V145/$NAME" || { ro; fail "Kopieren of nacontrole mislukt: $NAME"; }
    done
    mv -f "$V145/v145-launcher.sh" "$V145/launcher.sh" || { ro; fail "V14.5-launcher ontbreekt"; }
    chmod 755 "$V145/cw-window-candidate" "$V145/launcher.sh"
    echo enabled > "$V145/enabled"
    rm -f "$V146/enabled" "$V146/pending" "$V146/attempted" "$V146/confirmed" "$CONTROLS/enabled" "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    begin_switch || { ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    stage_file "$LSD.cw-stock" "$LSD" || { rollback_switch; ro; fail "OEM HMI-herstel mislukt"; }
    stage_file "$V145/launcher.sh" "$DIO" || { rollback_switch; ro; fail "V14.5 DIO-installatie mislukt"; }
    finish_switch
    ro || fail "Appvolume niet read-only"
    echo "V14.5 actief na herstart: native dag/nacht, een begin-zoom-out en SD-logging"
    reboot_unit
    ;;
install-v146)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$V146" || { ro; fail "V14.6-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-v145.so libcw-query-stdio.so v145-launcher.sh lsd-notifications.sh PorscheCarPlayNotifications.experimental.jar payload.manifest; do
        copy_checked "$PAYLOAD/v146/$NAME" "$V146/$NAME" || { ro; fail "Kopieren of nacontrole mislukt: $NAME"; }
    done
    mv -f "$V146/v145-launcher.sh" "$V146/launcher.sh" || { ro; fail "V14.6-launcher ontbreekt"; }
    chmod 755 "$V146/cw-window-candidate" "$V146/launcher.sh" "$V146/lsd-notifications.sh"
    echo enabled > "$V146/enabled"
    echo pending > "$V146/pending"
    rm -f "$V146/attempted" "$V146/confirmed" "$CONTROLS/enabled" "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    begin_switch || { ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    stage_file "$V146/lsd-notifications.sh" "$LSD" || { rollback_switch; ro; fail "V14.6 HMI-starter mislukt"; }
    stage_file "$V146/launcher.sh" "$DIO" || { rollback_switch; ro; fail "V14.6 DIO-installatie mislukt"; }
    finish_switch
    ro || fail "Appvolume niet read-only"
    echo "V14.6 klaar voor eenmalige notificatieproef"
    reboot_unit
    ;;
confirm-v146)
    [ -s "$V146/enabled" ] || fail "V14.6 niet geinstalleerd"
    rw || fail "Appvolume niet schrijfbaar"
    echo confirmed > "$V146/confirmed" || { ro; fail "Bevestiging mislukt"; }
    rm -f "$V146/pending" "$V146/attempted"
    ro || fail "Appvolume niet read-only"
    echo "V14.6 bevestigd voor volgende boots"
    ;;
install-controls)
    ensure_stock
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$CONTROLS" || { ro; fail "Controls-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-controls.so cw-rgi.so libcw-query-stdio.so controls-launcher.sh lsd-controls.sh PorscheCarPlayBridge.experimental.jar payload.manifest; do
        copy_checked "$PAYLOAD/controls/$NAME" "$CONTROLS/$NAME" || { ro; fail "Kopieren of nacontrole mislukt: $NAME"; }
    done
    mv -f "$CONTROLS/controls-launcher.sh" "$CONTROLS/launcher.sh" || { ro; fail "Controls-launcher ontbreekt"; }
    chmod 755 "$CONTROLS/cw-window-candidate" "$CONTROLS/launcher.sh" "$CONTROLS/lsd-controls.sh"
    echo enabled > "$CONTROLS/enabled"
    echo pending > "$CONTROLS/pending"
    rm -f "$V146/enabled" "$V146/pending" "$V146/attempted" "$V146/confirmed" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    begin_switch || { ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    stage_file "$CONTROLS/lsd-controls.sh" "$LSD" || { rollback_switch; ro; fail "Controls HMI-starter mislukt"; }
    stage_file "$CONTROLS/launcher.sh" "$DIO" || { rollback_switch; ro; fail "Controls DIO-starter mislukt"; }
    finish_switch
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
    rm -f "$STABLE/enabled" "$V145/enabled" "$V146/enabled" "$V146/pending" "$V146/attempted" "$V146/confirmed" "$CONTROLS/enabled" "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS/confirmed"
    begin_switch || { ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    stage_file "$LSD.cw-stock" "$LSD" || { rollback_switch; ro; fail "OEM HMI-herstel mislukt"; }
    stage_file "$DIO.cw-stock" "$DIO" || { rollback_switch; ro; fail "OEM DIO-herstel mislukt"; }
    finish_switch
    ro || fail "Appvolume niet read-only"
    echo "Volledig OEM actief na herstart"
    ;;
*) fail "Onbekende actie: $ACTION";;
esac
