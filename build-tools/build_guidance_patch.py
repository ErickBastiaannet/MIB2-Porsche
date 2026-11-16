"""Build a guidance-only MU1417 trial. No display/zoom/launcher payloads."""
from pathlib import Path
import argparse, hashlib, json, subprocess, zipfile
ROOT=Path(__file__).resolve().parents[1]
FILES={'cw-rgi.so':ROOT/'build/qnx/libcw-porsche-rgi.so','PorscheCarPlayGuidance.experimental.jar':ROOT/'build/PorscheCarPlayGuidance.experimental.jar'}
BASE={'cw-rgi.so':'791a8673bf198599fd261d6cdfd85f256bdc27537a072b045ee101e57e77d31e','PorscheCarPlayGuidance.experimental.jar':'fae18ec437ea7b479777859df649c28a8becfdc7b33b4cb2c7e1e385aaeeadbd'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['presentation','checklist'],default='presentation')
    args=parser.parse_args()
    protected={}
    if args.profile=='checklist':
        protected=json.loads((ROOT/'tests/fixtures/guidance-processing-boundary.json').read_text())
        for name,expected in protected.items():
            if sha(ROOT/name)!=expected:raise SystemExit('Protected receiving/map/startup source changed: '+name)
    hashes={n:sha(p) for n,p in FILES.items()}
    if args.profile=='presentation' and hashes != {
        'cw-rgi.so':'1a75449ff62787599fdfd2a4afa517b3e4dd7779770cd5e1430333cf306f2b65',
        'PorscheCarPlayGuidance.experimental.jar':'a5176788f8bc3f9bc8a868c5b8f23723395757203da43b8faf102fc53641fccd'}:
        raise SystemExit('Earlier presentation profile is preserved; use --profile checklist for processing changes')
    script='''#!/bin/ksh
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
STATE=/mnt/persist/connectwow-carplay
BACKUP=$ROOT/before-presentation-only-20261116
cd "$(dirname "$0")"
function cw_hash { "$ROOT/cw-window-candidate" --hash "$1"; }
RW=0
SWAPPED=0
function cw_cleanup {
 trap - 0
 set +e
 if [ "$SWAPPED" = 1 ]; then
  for F in cw-rgi.so PorscheCarPlayGuidance.experimental.jar; do
   cp -p "$BACKUP/$F" "$ROOT/$F.rollback" && mv -f "$ROOT/$F.rollback" "$ROOT/$F"
  done
  cp -p "$BACKUP/native.confirmed" "$STATE/guidance-native/confirmed"
  cp -p "$BACKUP/java.confirmed" "$STATE/guidance-probe/confirmed"
  rm -f "$STATE/guidance-native/pending" "$STATE/guidance-probe/pending" /ramdisk/cw-guidance-native-trial
 fi
 [ "$RW" = 0 ] || mount -ur /mnt/app
}
trap cw_cleanup 0
'''
    for n in FILES:
        script+=f'[ "$(cw_hash "{n}")" = {hashes[n]} ] || exit 1\n'
        script+=f'[ "$(cw_hash "$ROOT/{n}")" = {BASE[n]} ] || exit 1\n'
    script+='''[ ! -e "$BACKUP" ] || exit 1
[ -s "$STATE/guidance-native/confirmed" ] && [ -s "$STATE/guidance-probe/confirmed" ] || exit 1
mount -uw /mnt/app
RW=1
mkdir "$BACKUP"
cp -p "$STATE/guidance-native/confirmed" "$BACKUP/native.confirmed"
cp -p "$STATE/guidance-probe/confirmed" "$BACKUP/java.confirmed"
for F in cw-rgi.so PorscheCarPlayGuidance.experimental.jar; do
 cp -p "$ROOT/$F" "$BACKUP/$F"
 [ "$(cw_hash "$ROOT/$F")" = "$(cw_hash "$BACKUP/$F")" ] || exit 1
 cp -p "$F" "$ROOT/$F.new"
 [ "$(cw_hash "$F")" = "$(cw_hash "$ROOT/$F.new")" ] || exit 1
done
chmod 755 "$ROOT/cw-rgi.so.new"
chmod 644 "$ROOT/PorscheCarPlayGuidance.experimental.jar.new"
SWAPPED=1
for F in cw-rgi.so PorscheCarPlayGuidance.experimental.jar; do mv -f "$ROOT/$F.new" "$ROOT/$F"; done
rm -f "$STATE/guidance-native/confirmed" "$STATE/guidance-probe/confirmed" /ramdisk/cw-guidance-native-trial
echo pending > "$STATE/guidance-native/pending"
echo pending > "$STATE/guidance-probe/pending"
mount -ur /mnt/app
RW=0
SWAPPED=0
trap - 0
echo GUIDANCE_PRESENTATION_TRIAL_READY_NO_REBOOT
'''
    restore='''#!/bin/ksh
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
B=$ROOT/before-presentation-only-20261116
S=/mnt/persist/connectwow-carplay
function cw_hash { "$ROOT/cw-window-candidate" --hash "$1"; }
'''
    for n in FILES:restore+=f'[ "$(cw_hash "$B/{n}")" = {BASE[n]} ] || exit 1\n'
    restore+='''[ -s "$B/native.confirmed" ] && [ -s "$B/java.confirmed" ] || exit 1
mount -uw /mnt/app
trap 'mount -ur /mnt/app' 0
for F in cw-rgi.so PorscheCarPlayGuidance.experimental.jar; do
 cp -p "$B/$F" "$ROOT/$F.restore"
 [ "$(cw_hash "$B/$F")" = "$(cw_hash "$ROOT/$F.restore")" ] || exit 1
done
for F in cw-rgi.so PorscheCarPlayGuidance.experimental.jar; do mv -f "$ROOT/$F.restore" "$ROOT/$F"; done
cp -p "$B/native.confirmed" "$S/guidance-native/confirmed"
cp -p "$B/java.confirmed" "$S/guidance-probe/confirmed"
rm -f "$S/guidance-native/pending" "$S/guidance-probe/pending" /ramdisk/cw-guidance-native-trial
mount -ur /mnt/app
trap - 0
echo GUIDANCE_BASELINE_RESTORED_NO_REBOOT
'''
    readme='''GUIDANCE PRESENTATION ONLY - K5137/MU1417
Status: lokaal getest; NIET fysiek bevestigd. Niet automatisch installeren.
Alleen de parser/presentatie en guidance-JAR; geen kaart-, zoom-, menu- of starterwijziging.
Bestemmingsadres via referentie-BAP DestinationInfo (functie 46), maximaal 50 UTF-8-bytes; behouden bij aankomst en gewist bij stoppen. Huidige positie blijft een apart veld. De plaats van de tekst op de echte teller moet nog fysiek worden bevestigd.
De iAP2-ontvangst/verzendcode is gelijk aan commit 288175f, afgezien van passieve lifecycle-expiratie na bestaande RX-traffic.
Dit behoudt ook het bestaande synchrone verzendpad. Dit pakket bewijst NIET dat die transportcode onder alle omstandigheden stabiel is.

Uitpakken in een eigen map op SD of /ramdisk. Eerst op MMX:
/bin/ksh -n /pad/naar/install.sh
/bin/ksh /pad/naar/install.sh
Installeren herstart NIET. Alleen doorgaan na GUIDANCE_PRESENTATION_TRIAL_READY_NO_REBOOT.
Daarna een afgesproken PCM-herstart; native en Java zijn een one-boot proef, geen bevestigde installatie.
Volgende boot zonder bevestiging laadt OEM-guidance. Bevestig NIET voordat kaart, actuele manoeuvre, afstand, stoppen en appwissel fysiek slagen.
Handmatig terugzetten: /bin/ksh /pad/naar/restore.sh, daarna afgesproken herstart.
Installatie vereist exact de twee baselinehashes uit manifest.json en aanwezige confirmed-markers; anders stopt zij zonder vervanging.

Bekende grens: 800ms stopgrace en 5s aankomsthold verlopen bij bestaande RX-traffic; bij totale stilte geldt de bestaande Java freshness-fallback, niet een nieuwe timerthread.
Niet met een ander CWRG4-pakket of oude JAR mengen.
'''
    manifest={'firmware':'MHI2_ER_POG24_K5137_MU1417_971919360T','baseline_commit':'288175f624c6b62468b174451505af19111f1ed1','payload_sha256':hashes,'required_live_sha256':BASE,'physical_validation':False,'auto_reboot':False,'changes':['current maneuver selection, mapping, lane semantics, lifecycle, presentation, OEM DestinationInfo with reference UTF-8 bound'],'excluded':['video','zoom','launchers','menus','new TX callback','new worker threads']}
    if args.profile=='checklist':
        script=script.replace('before-presentation-only-20261116','before-processing-checklist-20261116')
        restore=restore.replace('before-presentation-only-20261116','before-processing-checklist-20261116')
        readme=readme.replace('CWRG4','CWRG5')
        script=script.replace('GUIDANCE_PRESENTATION_TRIAL_READY_NO_REBOOT','GUIDANCE_PROCESSING_TRIAL_READY_NO_REBOOT')
        readme=readme.replace('GUIDANCE_PRESENTATION_TRIAL_READY_NO_REBOOT','GUIDANCE_PROCESSING_TRIAL_READY_NO_REBOOT').replace('GUIDANCE PRESENTATION ONLY','GUIDANCE PROCESSING CHECKLIST')
        readme=readme.replace('Bekende grens: 800ms stopgrace en 5s aankomsthold verlopen bij bestaande RX-traffic; bij totale stilte geldt de bestaande Java freshness-fallback, niet een nieuwe timerthread.',
            'Stop- en aankomstdeadlines worden door de bestaande Java-poll afgehandeld, ook zonder vervolgpacket. Het native transport is ongewijzigd; er zijn geen nieuwe receive/send-hooks of threads.')
        readme+='\nCHECKLIST-PROFIEL: rotonde/kruispuntzijtakken uit LuKa-referentie, actionblink, 32 lane-events, volgende straat/signpost via OEM TurnToInfo, absolute ETA via HU-klok/lokale tijd, stille stop/aankomst.\nCWRG5 is uitsluitend de interne native/Java-snapshot, niet een nieuw iAP2-protocol. Native en JAR samen bijwerken. De bestaande ontvangstketen en kaart zijn niet gewijzigd.\nNiet alle referentiemenu/renderer/takeover-functies zijn onderdeel van deze verwerkingscorrectie.\n'
        manifest['internal_snapshot']='CWRG5'
        manifest['protected_source_sha256']=protected
        manifest['changes']=['current instruction/distance','reference junction side streets','action blink and distance replay','32 lane events','OEM next-road/signpost/destination','HU absolute/local ETA','stop/arrival deadlines on existing Java poll']
        manifest['reference']='luka-dev/mib2q-carplay-rgi@21f501611b0b28dbdeb2849e8443ce90ec9517ff'
        out=ROOT/'build/guidance-processing-checklist-MU1417.zip'
    else:
        out=ROOT/'build/guidance-presentation-MU1417.zip'

    def add_entry(archive,name,data):
        info=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,data)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,p in FILES.items():add_entry(z,n,p.read_bytes())
        if args.profile=='checklist':add_entry(z,'LICENSE.upstream',(ROOT/'LICENSE.upstream').read_bytes())
        for n,b in {'install.sh':script,'restore.sh':restore,'LEESMIJ.txt':readme,'manifest.json':json.dumps(manifest,indent=2)+'\n'}.items():add_entry(z,n,b.encode())
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for n,h in hashes.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
    print(out);print(sha(out))
if __name__=='__main__':main()
