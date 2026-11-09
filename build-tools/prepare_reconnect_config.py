"""Generate an exact-layout MU1417 CarPlay child environment update."""
import argparse
import hashlib
import json
import re
from pathlib import Path

def patch(data: bytes) -> bytes:
    text=data.decode('utf-8')
    anchor='"IPL_CONFIG_DIR_DIO_MANAGER=/etc/eso/production"'
    if text.count(anchor)!=1 or text.count('"exec":"dio_manager"')!=1:
        raise ValueError('Unknown/already modified smartphone_integrator layout')
    if 'CW_PROCESS_SUPERVISOR=' in text:
        raise ValueError('Reconnect configuration already installed')
    values=[
        'CARPLAY_ALTSCREEN_ENABLE=1',
        'CARPLAY_ALTSCREEN_LOG=/ramdisk/cw-link-probe-20261102/cw-airplay-live-v14.log',
        'CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture',
        'CW_AUTO_ALT_WAKE=1','CW_PROCESS_SUPERVISOR=1',
        'LD_PRELOAD=/mnt/app/eso/hmi/connectwow-carplay/controls-v15/cw-receiver-controls.so',
    ]
    changed=text.replace(anchor,anchor+', '+', '.join(json.dumps(v) for v in values))
    changed=changed.replace('"exec":"dio_manager"','"exec":"dio_manager.cw-stock"')
    before=json.loads(re.sub(r'(?m)^\s*#.*$','',text))
    after=json.loads(re.sub(r'(?m)^\s*#.*$','',changed))
    expected=json.loads(json.dumps(before))
    child=expected['children']['carplay']
    child['exec']='dio_manager.cw-stock';child['envs'].extend(values)
    if after!=expected:raise ValueError('Unexpected configuration changes')
    return changed.encode('utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('target',type=Path)
    args=parser.parse_args();original=args.source.read_bytes();updated=patch(original)
    args.target.write_bytes(updated)
    print('SOURCE',hashlib.sha256(original).hexdigest())
    print('TARGET',hashlib.sha256(updated).hexdigest())
