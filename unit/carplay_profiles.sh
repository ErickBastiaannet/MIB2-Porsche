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
CONTROLS_STATE=/mnt/persist/connectwow-carplay/controls-v15
GUIDANCE_STATE=/mnt/persist/connectwow-carplay/guidance-native
MMIPOD=$APP/armle/usr/sbin/mm-ipod
MMIPOD_REAL_DIR=$APP/armle/usr/sbin/connectwow-rgi
MMIPOD_STOCK=$MMIPOD.cw-guidance-stock
MMIPOD_STOCK_SHA=d5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464
IAP2_CFG=/mnt/system/etc/mm/iap2.cfg
IAP2_STOCK_SHA=d6d50af974a82feec2add942d3d8e6e88f96a2c25c469f747a11954b1c3445d7
IAP2_GUIDANCE_SHA=5ca0a762dcf24bef3661f77dc4641433767026e4500a2a60f2c60ed0cc77af41
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
    echo "Installatie geslaagd. Volledige RCC-herstart wordt aangevraagd."
    sleep 2
    on -f rcc /usr/apps/mib2_ioc_flash reboot || fail "RCC-herstartopdracht mislukt"
}

if [ "$ACTION" = status ]; then
    if [ -s "$CONTROLS/confirmed" ]; then echo "Profiel: Controls V15 bevestigd"
    elif [ -s "$CONTROLS/attempted" ]; then echo "Profiel: Controls V15 proefboot niet bevestigd; volgende boot gebruikt stock-HMI"
    elif [ -s "$CONTROLS/pending" ]; then echo "Profiel: Controls V15 klaar voor eenmalige proefboot"
    elif [ -s "$V146/confirmed" ]; then echo "Profiel: V14.6 meldingen bevestigd"
    elif [ -s "$V146/attempted" ]; then echo "Profiel: V14.6 proefboot niet bevestigd; volgende boot gebruikt stock-HMI"
    elif [ -s "$V146/pending" ]; then echo "Profiel: V14.6 klaar voor eenmalige proefboot"
    elif [ -s "$V145/enabled" ]; then echo "Profiel: V14.5 automatische start en logging"
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
install-controls|test-guidance) verify_payload "$PAYLOAD/controls" '@CONTROLS_MANIFEST_SHA@' || fail "Controls V15-payload beschadigd";;
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
function restore_iap2_config {
    [ -s "$IAP2_CFG.cw-guidance-stock" ] || return 0
    mount -uw /mnt/system || return 1
    if [ "$(hash_file "$IAP2_CFG.cw-guidance-stock")" != "$IAP2_STOCK_SHA" ]; then
        mount -ur /mnt/system
        return 1
    fi
    cp -p "$IAP2_CFG.cw-guidance-stock" "$IAP2_CFG.cw-new" || { mount -ur /mnt/system; return 1; }
    mv -f "$IAP2_CFG.cw-new" "$IAP2_CFG" || { mount -ur /mnt/system; return 1; }
    mount -ur /mnt/system
}
function patch_iap2_config {
    CURRENT=$(hash_file "$IAP2_CFG")
    if [ "$CURRENT" = "$IAP2_GUIDANCE_SHA" ]; then
        [ -s "$IAP2_CFG.cw-guidance-stock" ] || return 1
        [ "$(hash_file "$IAP2_CFG.cw-guidance-stock")" = "$IAP2_STOCK_SHA" ] || return 1
        return 0
    fi
    [ "$CURRENT" = "$IAP2_STOCK_SHA" ] || return 1
    mount -uw /mnt/system || return 1
    cp -p "$IAP2_CFG" "$IAP2_CFG.cw-guidance-stock" || { mount -ur /mnt/system; return 1; }
    IAP2_NEW=$IAP2_CFG.cw-new
    : > "$IAP2_NEW" || { mount -ur /mnt/system; return 1; }
    IAP2_ADDED=0
    while IFS= read -r LINE || [ -n "$LINE" ]; do
        if [ "$LINE" = "[commands]" ] && [ "$IAP2_ADDED" -eq 0 ]; then
            echo "# ConnectWow iAP2 Route Guidance message registration." >> "$IAP2_NEW"
            echo "[ident]" >> "$IAP2_NEW"
            echo "recvmsgs=0x5201,0x5202,0x5204" >> "$IAP2_NEW"
            echo "sendmsgs=0x5200,0x5203" >> "$IAP2_NEW"
            echo >> "$IAP2_NEW"
            IAP2_ADDED=1
        fi
        echo "$LINE" >> "$IAP2_NEW"
    done < "$IAP2_CFG"
    if [ "$IAP2_ADDED" -ne 1 ] || [ "$(hash_file "$IAP2_NEW")" != "$IAP2_GUIDANCE_SHA" ]; then
        rm -f "$IAP2_NEW"
        mount -ur /mnt/system
        return 1
    fi
    mv -f "$IAP2_NEW" "$IAP2_CFG" || { mount -ur /mnt/system; return 1; }
    mount -ur /mnt/system
}
function rollback_guidance {
    rw 2>/dev/null
    [ ! -s "$MMIPOD_STOCK" ] || stage_file "$MMIPOD_STOCK" "$MMIPOD" 2>/dev/null
    [ ! -s "$LSD.cw-stock" ] || stage_file "$LSD.cw-stock" "$LSD" 2>/dev/null
    rm -f "$GUIDANCE_STATE/pending" "$GUIDANCE_STATE/attempted" "$GUIDANCE_STATE/confirmed"
    rm -f /mnt/persist/connectwow-carplay/guidance-probe/pending
    rm -f /mnt/persist/connectwow-carplay/guidance-probe/attempted
    rm -f /mnt/persist/connectwow-carplay/guidance-probe/confirmed
    ro 2>/dev/null
    restore_iap2_config 2>/dev/null
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
    echo "V14.5 actief na herstart: automatische CarPlay-start en SD-logging"
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
    CONTROLS_NEW=$ROOT/.controls-v15-new
    CONTROLS_OLD=$ROOT/.controls-v15-old
    rm -rf "$CONTROLS_NEW" "$CONTROLS_OLD"
    mkdir -p "$CONTROLS_NEW" || { ro; fail "Tijdelijke Controls-map niet beschikbaar"; }
    for NAME in cw-window-candidate cw-receiver-controls.so cw-rgi.so libcw-query-stdio.so controls-launcher.sh lsd-controls.sh lsd-guidance.sh mm-ipod-rgi.sh PorscheCarPlayBridge.experimental.jar PorscheCarPlayGuidance.experimental.jar payload.manifest; do
        copy_checked "$PAYLOAD/controls/$NAME" "$CONTROLS_NEW/$NAME" || { rm -rf "$CONTROLS_NEW"; ro; fail "Kopieren of nacontrole mislukt: $NAME"; }
    done
    mv -f "$CONTROLS_NEW/controls-launcher.sh" "$CONTROLS_NEW/launcher.sh" || { rm -rf "$CONTROLS_NEW"; ro; fail "Controls-launcher ontbreekt"; }
    cp -p "$CONTROLS_NEW/payload.manifest" "$CONTROLS_NEW/installed.manifest" || { rm -rf "$CONTROLS_NEW"; ro; fail "Installatiemanifest kon niet worden vastgelegd"; }
    chmod 755 "$CONTROLS_NEW/cw-window-candidate" "$CONTROLS_NEW/launcher.sh" "$CONTROLS_NEW/lsd-controls.sh" "$CONTROLS_NEW/lsd-guidance.sh" "$CONTROLS_NEW/mm-ipod-rgi.sh"
    echo enabled > "$CONTROLS_NEW/enabled" || { rm -rf "$CONTROLS_NEW"; ro; fail "Controls kon niet worden geactiveerd"; }
    echo native-only > "$CONTROLS_NEW/hmi-mode" || { rm -rf "$CONTROLS_NEW"; ro; fail "Veilige HMI-modus kon niet worden vastgelegd"; }
    [ ! -d "$CONTROLS" ] || mv "$CONTROLS" "$CONTROLS_OLD" || { rm -rf "$CONTROLS_NEW"; ro; fail "Bestaande Controls-map kon niet worden geborgd"; }
    mv "$CONTROLS_NEW" "$CONTROLS" || { [ ! -d "$CONTROLS_OLD" ] || mv "$CONTROLS_OLD" "$CONTROLS"; ro; fail "Nieuwe Controls-map kon niet atomair worden geactiveerd"; }
    begin_switch || { ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    # The native CarPlay path is physically verified. Keep Porsche's HMI
    # launcher stock until each Java hook has passed an isolated unit test;
    # loading the combined experimental JAR blocks MU1417 navigation startup.
    stage_file "$LSD.cw-stock" "$LSD" || { rollback_switch; rm -rf "$CONTROLS"; [ ! -d "$CONTROLS_OLD" ] || mv "$CONTROLS_OLD" "$CONTROLS"; ro; fail "OEM HMI-starter kon niet worden behouden"; }
    stage_file "$CONTROLS/launcher.sh" "$DIO" || { rollback_switch; rm -rf "$CONTROLS"; [ ! -d "$CONTROLS_OLD" ] || mv "$CONTROLS_OLD" "$CONTROLS"; ro; fail "Controls DIO-starter mislukt"; }
    finish_switch
    rm -rf "$CONTROLS_OLD"
    rm -f "$STABLE/enabled" "$V145/enabled" "$V146/enabled" "$V146/pending" "$V146/attempted" "$V146/confirmed"
    ro || fail "Appvolume niet read-only"
    echo "Native V15 actief met OEM HMI. Experimentele Java-controls zijn bewust uitgeschakeld."
    reboot_unit
    ;;
test-guidance)
    [ -s "$CONTROLS/enabled" ] || fail "Installeer eerst Controls V15"
    for REQUIRED in cw-rgi.so mm-ipod-rgi.sh lsd-guidance.sh PorscheCarPlayGuidance.experimental.jar; do
        [ -s "$CONTROLS/$REQUIRED" ] || fail "Guidance-onderdeel ontbreekt: $REQUIRED"
    done
    ensure_stock
    [ "$(hash_file "$LSD")" = "$LSD_STOCK_SHA" ] || fail "Guidance vereist de OEM HMI-starter"
    MMIPOD_CURRENT=$(hash_file "$MMIPOD")
    MMIPOD_WRAPPER_SHA=$(hash_file "$CONTROLS/mm-ipod-rgi.sh")
    if [ -s "$MMIPOD_STOCK" ]; then
        [ "$(hash_file "$MMIPOD_STOCK")" = "$MMIPOD_STOCK_SHA" ] || fail "mm-ipod-back-up ongeldig"
        if [ "$MMIPOD_CURRENT" != "$MMIPOD_STOCK_SHA" ] && [ "$MMIPOD_CURRENT" != "$MMIPOD_WRAPPER_SHA" ]; then
            fail "mm-ipod is door een andere modificatie vervangen; niets overschreven"
        fi
    elif [ "$MMIPOD_CURRENT" != "$MMIPOD_STOCK_SHA" ]; then
        fail "Onbekende mm-ipod; wrapper wordt niet geinstalleerd"
    fi
    patch_iap2_config || fail "iAP2-config onbekend of niet transactioneel patchbaar"
    rw || fail "Appvolume niet schrijfbaar"
    mkdir -p "$MMIPOD_REAL_DIR" "$GUIDANCE_STATE" || { rollback_guidance; fail "Guidance-mappen konden niet worden gemaakt"; }
    if [ ! -s "$MMIPOD_STOCK" ]; then
        copy_checked "$MMIPOD" "$MMIPOD_STOCK" || { rollback_guidance; fail "mm-ipod-back-up mislukt"; }
    fi
    [ "$(hash_file "$MMIPOD_STOCK")" = "$MMIPOD_STOCK_SHA" ] || { rollback_guidance; fail "mm-ipod-back-up ongeldig"; }
    copy_checked "$MMIPOD_STOCK" "$MMIPOD_REAL_DIR/mm-ipod" || { rollback_guidance; fail "OEM mm-ipod kon niet worden gestaged"; }
    chmod 755 "$MMIPOD_REAL_DIR/mm-ipod" || { rollback_guidance; fail "OEM mm-ipod kon niet uitvoerbaar worden gemaakt"; }
    stage_file "$CONTROLS/mm-ipod-rgi.sh" "$MMIPOD" || { rollback_guidance; fail "mm-ipod-wrapper kon niet worden geactiveerd"; }
    chmod 755 "$MMIPOD" || { rollback_guidance; fail "mm-ipod-wrapper kon niet uitvoerbaar worden gemaakt"; }
    rm -f "$GUIDANCE_STATE/confirmed" "$GUIDANCE_STATE/attempted"
    echo pending > "$GUIDANCE_STATE/pending" || { rollback_guidance; fail "Native guidance-ticket kon niet worden gemaakt"; }
    mkdir -p /mnt/persist/connectwow-carplay/guidance-probe || { rollback_guidance; fail "Java guidance-status ontbreekt"; }
    rm -f /mnt/persist/connectwow-carplay/guidance-probe/attempted /mnt/persist/connectwow-carplay/guidance-probe/confirmed
    echo pending > /mnt/persist/connectwow-carplay/guidance-probe/pending || { rollback_guidance; fail "Java guidance-ticket kon niet worden gemaakt"; }
    begin_switch || { rollback_guidance; fail "HMI-starter kon niet worden geborgd"; }
    stage_file "$CONTROLS/lsd-guidance.sh" "$LSD" || { rollback_switch; rollback_guidance; fail "Guidance HMI-starter kon niet worden geactiveerd"; }
    finish_switch
    ro || { rollback_guidance; fail "Appvolume niet read-only"; }
    echo "Guidance klaar voor een eenmalige, fail-closed proefboot"
    reboot_unit
    ;;
confirm-guidance)
    [ -s "$GUIDANCE_STATE/attempted" ] || fail "Native guidance is nog niet eenmalig gestart"
    [ -s /mnt/persist/connectwow-carplay/guidance-probe/attempted ] || fail "Java guidance is nog niet eenmalig gestart"
    mkdir -p "$GUIDANCE_STATE" || fail "Guidance-status ontbreekt"
    echo confirmed > "$GUIDANCE_STATE/confirmed" || fail "Guidance-bevestiging mislukt"
    mkdir -p /mnt/persist/connectwow-carplay/guidance-probe || fail "Java guidance-status ontbreekt"
    echo confirmed > /mnt/persist/connectwow-carplay/guidance-probe/confirmed || fail "Java guidance-bevestiging mislukt"
    rm -f "$GUIDANCE_STATE/pending" "$GUIDANCE_STATE/attempted"
    rm -f /mnt/persist/connectwow-carplay/guidance-probe/pending /mnt/persist/connectwow-carplay/guidance-probe/attempted
    echo "Guidance bevestigd; native transport en Java-weergave blijven actief"
    ;;
test-controls-java)
    [ -s "$CONTROLS/enabled" ] || fail "Installeer eerst Controls V15"
    [ -s "$CONTROLS/PorscheCarPlayBridge.experimental.jar" ] || fail "Gecombineerde Java-bridge ontbreekt"
    [ -s "$CONTROLS/lsd-controls.sh" ] || fail "Java one-shotstarter ontbreekt"
    rw || fail "Appvolume niet schrijfbaar"
    rm -f "$CONTROLS/confirmed" "$CONTROLS/attempted"
    mkdir -p "$CONTROLS_STATE" || { ro; fail "Persistente Java-proefstatus kon niet worden gemaakt"; }
    rm -f "$CONTROLS_STATE/attempted"
    echo combined > "$CONTROLS_STATE/pending" || { ro; fail "Java-proefticket kon niet worden gemaakt"; }
    begin_switch || { rm -f "$CONTROLS/pending"; ro; fail "Startbestanden konden niet transactioneel worden geborgd"; }
    stage_file "$CONTROLS/lsd-controls.sh" "$LSD" || { rollback_switch; rm -f "$CONTROLS_STATE/pending"; ro; fail "Java one-shotstarter kon niet worden geactiveerd"; }
    finish_switch
    ro || fail "Appvolume niet read-only"
    echo "Gecombineerde Java-bridge klaar voor eenmalige proefboot"
    reboot_unit
    ;;
confirm-controls)
    [ -s "$CONTROLS/enabled" ] || fail "Controls V15 niet geinstalleerd"
    [ -s "$CONTROLS_STATE/attempted" ] || fail "Gecombineerde Java-bridge is nog niet eenmalig getest"
    rw || fail "Appvolume niet schrijfbaar"
    echo confirmed > "$CONTROLS/confirmed" || { ro; fail "Bevestiging mislukt"; }
    rm -f "$CONTROLS/pending" "$CONTROLS/attempted" "$CONTROLS_STATE/pending" "$CONTROLS_STATE/attempted"
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
    if [ -s "$MMIPOD_STOCK" ]; then
        [ "$(hash_file "$MMIPOD_STOCK")" = "$MMIPOD_STOCK_SHA" ] || { rollback_switch; ro; fail "OEM mm-ipod-back-up ongeldig"; }
        stage_file "$MMIPOD_STOCK" "$MMIPOD" || { rollback_switch; ro; fail "OEM mm-ipod-herstel mislukt"; }
        chmod 755 "$MMIPOD"
    fi
    finish_switch
    ro || fail "Appvolume niet read-only"
    restore_iap2_config || fail "OEM iAP2-herstel mislukt"
    rm -f "$GUIDANCE_STATE/pending" "$GUIDANCE_STATE/attempted" "$GUIDANCE_STATE/confirmed"
    rm -f /mnt/persist/connectwow-carplay/guidance-probe/pending /mnt/persist/connectwow-carplay/guidance-probe/attempted /mnt/persist/connectwow-carplay/guidance-probe/confirmed
    echo "Volledig OEM actief na herstart"
    ;;
*) fail "Onbekende actie: $ACTION";;
esac
