"""Exercise the actual portable SD manager with QNX ksh and isolated filesystems.
Run: docker ... qnx65-armv7:4.9 python3 tests/portable_install_transaction.py
No connected unit is changed. J9 linkage itself is mocked (already checked on MU1417).
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path('/src')
KSH = '/opt/qnx650/host/linux/x86/usr/bin/ksh'
sha = lambda b: hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(ROOT/'build/porsche-carplay-MU1417-portable.zip') as z:
    raw = {n: z.read(n) for n in z.namelist()}
source_manager = raw['install/scripts/cwrel.sh'].decode()
source_manifest = raw['online/cw-release/payload.manifest']
for row in source_manifest.decode().splitlines():
    digest, name = row.split(' ')
    assert sha(raw['online/cw-release/'+name]) == digest


def scenario(mode):
    with tempfile.TemporaryDirectory() as folder:
        top = Path(folder)
        app, system, sd, ram, persist = [top/n for n in ('app','system','sd','ram','persist')]
        ram.mkdir()
        originals = {
            app/'eso/bin/apps/dio_manager': b'#!/bin/sh\n# OEM DIO fixture\nexit 0\n',
            app/'eso/hmi/lsd/lsd.sh': b'#!/bin/sh\n# OEM HMI fixture\nprint -r -- "$VMOPTIONS"\n',
            app/'armle/usr/sbin/mm-ipod': b'#!/bin/sh\n# OEM iPod fixture\nexit 0\n',
            system/'etc/eso/production/smartphone_integrator.json': b'OEM SI fixture',
            system/'etc/mm/iap2.cfg': b'OEM iAP fixture',
            system/'etc/eso/production/displaymanager.json': b'OEM display fixture',
        }
        paths = {
            '/mnt/app':str(app), '/mnt/system':str(system), '/mnt/persist':str(persist),
            '/ramdisk':str(ram), '/fs/sda0':str(sd), '/fs/sdb0':str(top/'absent-sd'),
        }
        for p, b in originals.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b);p.chmod(0o755)
        stock_digests = [
            '9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8',
            '7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091',
            'd5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464',
            'a1ac27b4f405346548e8e1bec82b1f5c3483dc73050d682ad4c9a80808f7cbc7',
            'd6d50af974a82feec2add942d3d8e6e88f96a2c25c469f747a11954b1c3445d7',
            '115df2ffd860a6adccd4dd10c643a13b575a439922b272942025df8c7c246202',
        ]
        hashes = {h:sha(b) for h,b in zip(stock_digests, originals.values())}
        payload = sd/'online/cw-release';payload.mkdir(parents=True)
        verifier = b'#!/bin/sh\nsha256sum "$2" | cut -d " " -f 1\n'
        hashes[sha(raw['online/cw-release/cw-window-candidate'])] = sha(verifier)
        for path, data in raw.items():
            if not path.startswith('online/cw-release/') or path.endswith('payload.manifest'):continue
            name=path.rsplit('/',1)[1]
            changed = data
            if name == 'cw-window-candidate':changed=verifier
            elif name == 'hmi-start.sh':
                text=data.decode()
                for a,b in {**paths, **hashes}.items():text=text.replace(a,b)
                text=text.replace('/bin/ksh',KSH)
                changed=text.encode()
            elif name == 'mm-ipod.sh':
                text=data.decode()
                for a,b in paths.items():text=text.replace(a,b)
                changed=text.encode()
            if changed!=data:hashes[sha(data)]=sha(changed)
            (payload/name).write_bytes(changed);(payload/name).chmod(0o755)
        manifest=''.join(sha(p.read_bytes())+' '+p.name+'\n' for p in sorted(payload.iterdir())).encode()
        (payload/'payload.manifest').write_bytes(manifest)
        hashes[sha(source_manifest)] = sha(manifest)
        text=source_manager
        for a,b in {**paths,**hashes}.items():text=text.replace(a,b)
        text=text.replace('/bin/ksh',KSH)
        text=text.replace(KSH+' "$PAYLOAD/link-check.sh"', "print MOCK_J9_LINK_VERIFIED")
        mountlog=top/'mount.log'
        injection='function mount { echo "$*" >> "'+str(mountlog)+'";'
        if mode=='mount-failure':injection+=' if [ "$1" = -uw ] && [ "$2" = "'+str(system)+'" ]; then return 19; fi;'
        injection+=' return 0; }\n'
        if mode=='rename-failure':
            injection+='function mv { if [ "$2" = "'+str(system/'etc/eso/production/smartphone_integrator.json')+'.cw-new" ]; then return 17; fi; /bin/mv "$@"; }\n'
        if mode in ('late-rename-failure','restore-failure'):
            when='[ "$ACTION" = restore ] && ' if mode=='restore-failure' else ''
            injection+='FAILED_ONCE=0\nfunction mv { if '+when+'[ "$FAILED_ONCE" = 0 ] && [ "$2" = "'+str(system/'etc/mm/iap2.cfg')+'.cw-new" ]; then FAILED_ONCE=1; return 17; fi; /bin/mv "$@"; }\n'
        if mode=='copy-failure':
            injection+='function cp { if [ "$3" = "'+str(app/'eso/hmi/connectwow-carplay/controls-v15/cw-rgi.so')+'" ]; then return 17; fi; /bin/cp "$@"; }\n'
        if mode=='rollback-failure':
            injection+='LSD_MOVES=0\nfunction mv { if [ "$2" = "'+str(app/'eso/hmi/lsd/lsd.sh')+'.cw-new" ]; then LSD_MOVES=$((LSD_MOVES+1)); [ "$LSD_MOVES" -lt 2 ] || return 18; fi; if [ "$2" = "'+str(system/'etc/eso/production/smartphone_integrator.json')+'.cw-new" ]; then return 17; fi; /bin/mv "$@"; }\n'
        text=text.replace('set -eu\n','set -eu\n'+injection,1)
        manager=top/'manager.sh';manager.write_text(text)
        def run(action):
            return subprocess.run([KSH,str(manager),action],capture_output=True,text=True,env=dict(os.environ,PATH='/usr/bin:/bin'))
        def untouched():
            for p,b in originals.items():assert p.read_bytes()==b,(mode,p)
        if mode=='corrupt-payload':(payload/'cw-rgi.so').write_bytes(b'bad')
        if mode=='wrong-oem':(system/'etc/mm/iap2.cfg').write_bytes(b'other OEM')
        result=run('install' if mode in ('rename-failure','mount-failure','late-rename-failure','copy-failure','rollback-failure') else 'check')
        if mode in ('corrupt-payload','wrong-oem'):
            assert result.returncode and not mountlog.exists(),result.stdout+result.stderr
            print('PASS',mode);return
        if mode=='rollback-failure':
            assert result.returncode and 'herstel niet volledig' in result.stdout,(result.stdout,result.stderr)
            assert (app/'eso/hmi/connectwow-carplay/controls-v15').exists()
            assert (payload/'recovery/lsd.sh').read_bytes()==originals[app/'eso/hmi/lsd/lsd.sh']
            print('PASS',mode);return
        if mode in ('rename-failure','mount-failure','late-rename-failure','copy-failure'):
            assert result.returncode,result.stdout+result.stderr
            untouched()
            assert mountlog.read_text().splitlines()[-1].startswith('-ur'),mountlog.read_text()
            print('PASS',mode);return
        assert result.returncode==0,(result.stdout,result.stderr)
        assert not mountlog.exists();untouched()
        result=run('install');assert result.returncode==0,(result.stdout,result.stderr)
        state=persist/'connectwow-carplay/portable'
        assert (state/'pending').exists()
        assert (payload/'recovery/lsd.sh').read_bytes()==originals[app/'eso/hmi/lsd/lsd.sh']
        # No inherited network/vehicle data and no accidental automatic reboot.
        assert not (app/'eso/hmi/connectwow-carplay/controls-v15/before-navigation-priority-20261116').exists()
        assert 'mib2_ioc_flash reboot' not in result.stdout
        def boot():
            return subprocess.run([KSH,str(app/'eso/hmi/lsd/lsd.sh')],capture_output=True,text=True,env=dict(os.environ,PATH='/usr/bin:/bin',VMOPTIONS=''))
        b=boot();assert b.returncode==0,(b.stdout,b.stderr)
        assert b.stdout.count('-Xbootclasspath/p:')==1 and 'navigationPriority=porsche-first' in b.stdout,b.stdout
        assert (ram/'cw-nav-priority.enabled').exists()
        if mode=='fallback':
            b=boot();assert b.returncode==0 and '-Xbootclasspath/p:' not in b.stdout
            assert not(ram/'cw-nav-priority.enabled').exists()
        else:
            r=run('confirm');assert r.returncode==0,(r.stdout,r.stderr)
            for unused in range(2):
                b=boot();assert b.returncode==0 and b.stdout.count('-Xbootclasspath/p:')==1,(b.stdout,b.stderr)
        if mode=='restore-failure':
            r=run('restore');assert r.returncode!=0,(r.stdout,r.stderr)
            for target in ('eso/hmi/lsd/lsd.sh','armle/usr/sbin/mm-ipod'):
                assert (app/target).read_bytes()!=originals[app/target]
            assert (state/'confirmed').exists()
            print('PASS',mode);return
        if mode=='corrupt-installed':
            (app/'eso/hmi/connectwow-carplay/controls-v15/cw-rgi.so').write_bytes(b'corrupt installed library')
        r=run('restore');assert r.returncode==0,(r.stdout,r.stderr)
        untouched()
        assert not(state/'confirmed').exists()
        assert mountlog.read_text().splitlines()[-1].startswith('-ur')
        print('PASS',mode)

for mode in ('wrong-oem','corrupt-payload','mount-failure','rename-failure','late-rename-failure','copy-failure','rollback-failure','fallback','confirmed','restore-failure','corrupt-installed'):
    scenario(mode)
print('PORTABLE_TRANSACTION_PASS')
