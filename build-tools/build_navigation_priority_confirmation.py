"""Generate guarded confirmation for the physically tested MU1417 priority trial."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'build/navigation-priority';m=json.loads((d/'manifest.json').read_text());f=m['files']
 script='''#!/bin/ksh
set -e
ROOT=/mnt/app/eso/hmi/connectwow-carplay/controls-v15
LSD=/mnt/app/eso/hmi/lsd/lsd.sh
STATE=/mnt/persist/connectwow-carplay/navigation-priority
TOOL=$ROOT/cw-window-candidate
SOURCE=/ramdisk/cw-navigation-priority-20261117/lsd-priority-trial.sh
function cw_hash { "$TOOL" --hash "$1"; }
[ "$(cw_hash "$ROOT/cw-window-candidate")" = @WINDOW@ ] || exit 1
[ "$(cw_hash "$ROOT/PorscheNavigationPriority.test.jar")" = @JAR@ ] || exit 1
[ "$(cw_hash "$SOURCE")" = @LSD@ ] || exit 1
OLD=$(cw_hash "$LSD")
[ "$OLD" = 476561e0e7a6b1977718c7edc32a23fc216df1efbf9172eaa56383913898db10 ] || [ "$OLD" = 8b838ceec57c693a92d5ffd4774912d050adf1dca2b8232fc32b62d1c4833f1f ] || [ "$OLD" = @LSD@ ] || exit 1
[ -s "$STATE/attempted" ] || [ -s "$STATE/confirmed" ] || exit 1
/bin/ksh -n "$SOURCE"
RW=0
CHANGED=0
function cleanup {
 trap - 0
 set +e
 if [ "$CHANGED" = 1 ]; then
  rm -f "$STATE/confirmed"
  cp -p "$STATE/lsd-before-confirm.sh" "$LSD.restore" && mv -f "$LSD.restore" "$LSD"
 fi
 [ "$RW" = 0 ] || mount -ur /mnt/app
}
trap cleanup 0
cp -p "$LSD" "$STATE/lsd-before-confirm.sh"
[ "$(cw_hash "$STATE/lsd-before-confirm.sh")" = "$OLD" ] || exit 1
mount -uw /mnt/app
RW=1
cp -p "$SOURCE" "$LSD.new"
chmod 755 "$LSD.new"
[ "$(cw_hash "$LSD.new")" = @LSD@ ] || exit 1
CHANGED=1
mv -f "$LSD.new" "$LSD"
print 'physically verified both directions 2026-11-17' > "$STATE/confirmed.new"
mv -f "$STATE/confirmed.new" "$STATE/confirmed"
mount -ur /mnt/app
RW=0
CHANGED=0
trap - 0
print NAVIGATION_PRIORITY_PERMANENT_CONFIRMED_NO_REBOOT
'''
 for a,b in [('@WINDOW@',f['cw-window-priority']),('@JAR@',f['PorscheNavigationPriority.test.jar']),('@LSD@',f['lsd-priority-trial.sh'])]:script=script.replace(a,b)
 (d/'confirm.sh').write_bytes(script.encode('ascii'))
 print('PRIORITY_CONFIRMATION_READY')
if __name__=='__main__':main()
