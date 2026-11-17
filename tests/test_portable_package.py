"""Portable package reproducibility and refusal guards; no vehicle connection."""
import importlib.util
from pathlib import Path
import shutil
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portable_builder',ROOT/'build-tools/build_portable_sd.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

@pytest.fixture
def efs(tmp_path):
    package=ROOT/'build/porsche-carplay-MU1417-portable.zip'
    if not package.exists():pytest.skip('Build the portable ZIP with original firmware configuration first')
    with zipfile.ZipFile(package) as z:
        si=z.read('online/cw-release/smartphone_integrator.json').replace(b'"exec":"cw-carplay-start",',b'"exec":"dio_manager",')
        iap=z.read('online/cw-release/iap2.cfg')
    insertion=(b'# ConnectWow iAP2 Route Guidance message registration.\n'
               b'[ident]\nrecvmsgs=0x5201,0x5202,0x5204\nsendmsgs=0x5200,0x5203\n\n')
    assert iap.count(insertion)==1
    values={'etc/eso/production/smartphone_integrator.json':si,'etc/mm/iap2.cfg':iap.replace(insertion,b'')}
    for name,data in values.items():
        p=tmp_path/'efs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    return tmp_path/'efs'

def test_deterministic_and_no_test_unit_dependency(efs,tmp_path):
    first=tmp_path/'one.zip';second=tmp_path/'two.zip'
    assert builder.build(efs,first)['sha256']==builder.build(efs,second)['sha256']
    with zipfile.ZipFile(first) as z:
        text=z.read('online/cw-release/hmi-start.sh').decode()
        for bad in ('before-navigation-priority','172.16.250.248','217.154.19.25','kuaRoJgY','BAUIEE4HZ09012808'):
            assert bad not in text
        assert 'PorscheNavigationPriority.test.jar' in text
        assert b'exec /bin/ksh "$STOCK"' in z.read('online/cw-release/hmi-start.sh')
        for row in z.read('online/cw-release/payload.manifest').decode().splitlines():
            expected,name=row.split(' ')
            assert builder.SHA(z.read('online/cw-release/'+name))==expected

def test_unknown_oem_is_refused(efs,tmp_path):
    (efs/'etc/mm/iap2.cfg').write_bytes(b'unknown firmware')
    output=tmp_path/'refused.zip'
    with pytest.raises(ValueError,match='Unknown firmware'):
        builder.build(efs,output)
    assert not output.exists()

def test_changed_verified_binary_is_refused(efs,tmp_path,monkeypatch):
    copy=tmp_path/'release';shutil.copytree(builder.RELEASE,copy)
    (copy/'cw-receiver-controls.so').write_bytes(b'unverified rebuild')
    monkeypatch.setattr(builder,'RELEASE',copy)
    with pytest.raises(ValueError,match='Changed verified'):
        builder.build(efs,tmp_path/'bad.zip')
