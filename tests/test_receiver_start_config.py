import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('receiver_start',ROOT/'build-tools/prepare_receiver_start_config.py');M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_only_carplay_bootstrap_changes():
 child={'exec':'dio_manager.cw-stock','path':'/mnt/app/eso/bin/apps','envs':['LD_LIBRARY_PATH=/stock','IPL_CONFIG_DIR_DIO_MANAGER=/etc/eso/production']+M.VALUES,'watchdogTimeout':60000}
 before={'children':{'carplay':child,'other':{'exec':'untouched','envs':['original']}},'usb':{'original':True}}
 raw=json.dumps(before,separators=(',',':')).replace(',"CARPLAY_',', "CARPLAY_').replace(',"CW_',', "CW_').replace(',"LD_PRELOAD=',', "LD_PRELOAD=').encode()
 after=json.loads(M.patch(raw));assert after['children']['other']==before['children']['other'];assert after['usb']==before['usb']
 actual=after['children']['carplay'];assert actual['exec']=='cw-carplay-start';assert actual['envs']==child['envs'][:2];assert actual['watchdogTimeout']==60000
 with pytest.raises(ValueError):M.patch(M.patch(raw))
def test_refuses_unexpected_child():
 with pytest.raises((ValueError,KeyError)):M.patch(b'{"children":{}}')
