"""Generate confirmed logo selection from the exact live MU1417 zoom/guidance launcher."""
import argparse,hashlib
from pathlib import Path
BASE='93d7fed1102c20727a24acefbf43380001f5c9ef32319800bcbe74206d13e59e'
OUTPUT='5a7f5a087afb6699f2ba5ecb2297e2235f403db0e591164dd0749178dda2a368'
ANCHOR='if [ "$CW_PROBE_ENABLE" -eq 1 ]; then\n'
SNIPPET='    CW_LOGO_STATE=/mnt/persist/connectwow-carplay/satellite-logo-probe\n    CW_LOGO_JAR=/mnt/app/eso/hmi/connectwow-carplay/zoom-probe/PorscheCarPlayZoomLogo.probe.jar\n    CW_LOGO_ENABLE=0\n    if [ -s "$CW_LOGO_STATE/confirmed" ] && [ -s "$CW_LOGO_JAR" ]; then\n        CW_LOGO_ENABLE=1\n    elif [ -s "$CW_LOGO_STATE/pending" ] && [ -s "$CW_LOGO_JAR" ]; then\n        if mv "$CW_LOGO_STATE/pending" "$CW_LOGO_STATE/attempted"; then\n            CW_LOGO_ENABLE=1\n        fi\n    fi\n    if [ "$CW_LOGO_ENABLE" -eq 1 ]; then\n        CW_PROBE_JAR=$CW_LOGO_JAR\n        VMOPTIONS="$VMOPTIONS -Dconnectwow.carplay.satelliteLogo=hide-during-carplay"\n    fi\n'
def patch(payload):
 if hashlib.sha256(payload).hexdigest()!=BASE:raise ValueError('Unknown live launcher')
 text=payload.decode('ascii')
 if text.count(ANCHOR)!=1:raise ValueError('Ambiguous zoom activation')
 result=text.replace(ANCHOR,ANCHOR+SNIPPET).encode('ascii')
 if hashlib.sha256(result).hexdigest()!=OUTPUT:raise ValueError('Unexpected generated launcher')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('target',type=Path);a=p.parse_args()
 a.target.write_bytes(patch(a.source.read_bytes()));print(OUTPUT)
