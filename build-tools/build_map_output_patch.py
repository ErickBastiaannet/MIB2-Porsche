"""Package only the MU1417 video supervisor repair; never upload or reboot."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE='0cf0e784063396004f65d71195649815e467f197a1a9dc2aeb66506c4d412afa'
CAPTURE='c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    payload=ROOT/'build/qnx/porsche-carplay-window-candidate';new=digest(payload)
    prefix='''#!/bin/ksh
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
BACKUP=$ROOT/before-map-lease-20261116
FILE=$ROOT/cw-window-candidate
function cw_hash { "$FILE" --hash "$1"; }
'''
    install=prefix+f'''cd "$(dirname "$0")"
[ "$(cw_hash cw-window-candidate)" = {new} ] || exit 1
[ "$(cw_hash "$FILE")" = {BASE} ] || exit 1
[ "$(cw_hash "$ROOT/cw-receiver-controls.so")" = {CAPTURE} ] || exit 1
[ "$(cw_hash /ifs/lsd.jxe)" = a7c5e723904be98a349b5fcdb9e04846f1306b64ef1ef538d9ee08502864c04d ] || exit 1
[ ! -e "$BACKUP" ] || exit 1
RW=0
SWAPPED=0
function cw_cleanup {{
 trap - 0
 set +e
 if [ "$SWAPPED" = 1 ]; then
  cp -p "$BACKUP/cw-window-candidate" "$FILE.rollback" && mv -f "$FILE.rollback" "$FILE"
 fi
 [ "$RW" = 0 ] || mount -ur /mnt/app
}}
trap cw_cleanup 0
mount -uw /mnt/app
RW=1
mkdir "$BACKUP"
cp -p "$FILE" "$BACKUP/cw-window-candidate"
[ "$(cw_hash "$BACKUP/cw-window-candidate")" = {BASE} ] || exit 1
cp -p cw-window-candidate "$FILE.new"
chmod 755 "$FILE.new"
[ "$(cw_hash "$FILE.new")" = {new} ] || exit 1
SWAPPED=1
mv -f "$FILE.new" "$FILE"
[ "$(cw_hash "$FILE")" = {new} ] || exit 1
mount -ur /mnt/app
RW=0
SWAPPED=0
trap - 0
echo MAP_LEASE_REPAIR_INSTALLED_NO_REBOOT
'''
    restore=prefix+f'''[ "$(cw_hash "$BACKUP/cw-window-candidate")" = {BASE} ] || exit 1
[ "$(cw_hash "$FILE")" = {new} ] || exit 1
mount -uw /mnt/app
trap 'mount -ur /mnt/app' 0
cp -p "$BACKUP/cw-window-candidate" "$FILE.restore"
[ "$(cw_hash "$FILE.restore")" = {BASE} ] || exit 1
mv -f "$FILE.restore" "$FILE"
mount -ur /mnt/app
trap - 0
echo MAP_BASELINE_RESTORED_NO_REBOOT
'''
    readme='''KAARTUITVOER - K5137/MU1417 - lokale kandidaat, niet fysiek bevestigd

Dit pakket vervangt alleen cw-window-candidate. Geen capture/preload,
DIO-starter, Java, zoom, menu of guidance wordt veranderd.
Het is een apart pakket naast guidance-presentation-MU1417.zip.

Correctie: gevalideerde geometrie kan een verse bron met dezelfde PID blijven
volgen tijdens een trage displayquery. Sessiewatchdog gebruikt de echte timestamp
van de gedecodeerde pixels. Actieve displaycontrole heeft een gedeeld budget
binnen de bestaande 1s-pollcyclus; koude preflight houdt zijn gewone allowance.
Leases worden niet verlengd door hetzelfde oude frame opnieuw te lezen.
Verbroken verbinding, gewijzigde afmetingen en zwart/stilgevallen beeld blijven
terugval naar de Porsche-kaart geven.

Dit bewijst niet dat alle USB/opstartproblemen zijn opgelost. De eerdere
experimentele capture-/supervisor-startwijziging is uitdrukkelijk NIET inbegrepen.

Uitpakken in eigen map op SD of /ramdisk. Niet automatisch uitvoeren.
Controle op MMX: /bin/ksh -n /pad/naar/install.sh
Installatie op MMX: /bin/ksh /pad/naar/install.sh
Alleen doorgaan na MAP_LEASE_REPAIR_INSTALLED_NO_REBOOT.
Er is geen automatische herstart of live proceswissel. Plan de functietest apart.
Terugzetten: /bin/ksh /pad/naar/restore.sh, daarna afgesproken herstart.
Installer vereist exacte baselinewindow/capture en HMI-hash; onbekende unit weigert.
Deze native vervanging is NIET one-boot: bij een mislukte fysieke proef restore.sh
gebruiken. De volledige gehashte backup staat op de unit in before-map-lease-20261116.
'''
    manifest={'firmware':'MHI2_ER_POG24_K5137_MU1417_971919360T','payload_sha256':new,'required_window_sha256':BASE,'required_capture_sha256':CAPTURE,'physical_validation':False,'auto_reboot':False,'changes':['source-backed geometry','decoded frame timestamp watchdog','bounded live display maintenance'],'excluded':['capture library','DIO/Java launchers','guidance','zoom','menus'],'sources':{n:digest(ROOT/n) for n in ['native/porsche_unit.c','native/porsche_geometry.c','native/porsche_session.c','native/porsche_dm.c']}}
    out=ROOT/'build/map-output-repair-MU1417.zip'
    files={'cw-window-candidate':payload.read_bytes(),'install.sh':install.encode(),'restore.sh':restore.encode(),'LEESMIJ.txt':readme.encode(),'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():
            info=zipfile.ZipInfo(n,(2026,11,16,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None and hashlib.sha256(z.read('cw-window-candidate')).hexdigest()==new
    print(out);print(digest(out));print('window',new)
if __name__=='__main__':main()
