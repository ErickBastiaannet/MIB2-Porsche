"""Select the explicit MU1417 video bootstrap, preserving every other SI child."""
import hashlib,json,re
from pathlib import Path
VALUES=['CARPLAY_ALTSCREEN_ENABLE=1','CARPLAY_ALTSCREEN_LOG=/ramdisk/cw-link-probe-20261102/cw-airplay-live-v14.log','CARPLAY_ALTSCREEN_CAPTURE_DIR=/ramdisk/cw-no-raw-capture','CW_AUTO_ALT_WAKE=1','CW_PROCESS_SUPERVISOR=1','LD_PRELOAD=/mnt/app/eso/hmi/connectwow-carplay/controls-v15/cw-receiver-controls.so']
def patch(data):
 text=data.decode('utf-8');before=json.loads(re.sub(r'(?m)^\s*#.*$','',text))
 child=before['children']['carplay']
 if child['exec']!='dio_manager.cw-stock' or child['path']!='/mnt/app/eso/bin/apps':raise ValueError('Unknown current CarPlay child')
 if text.count('"exec":"dio_manager.cw-stock"')!=1:raise ValueError('Ambiguous child executable')
 for value in VALUES:
  needle=', '+json.dumps(value)
  if text.count(needle)!=1:raise ValueError('Unknown child environment layout')
  text=text.replace(needle,'')
 text=text.replace('"exec":"dio_manager.cw-stock"','"exec":"cw-carplay-start"')
 after=json.loads(re.sub(r'(?m)^\s*#.*$','',text));expected=json.loads(json.dumps(before))
 child=expected['children']['carplay'];child['exec']='cw-carplay-start';child['envs']=[v for v in child['envs'] if v not in VALUES]
 if after!=expected:raise ValueError('Unrelated configuration changed')
 return text.encode('utf-8')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('target',type=Path);a=p.parse_args()
 data=patch(a.source.read_bytes());a.target.write_bytes(data);print(hashlib.sha256(data).hexdigest())
