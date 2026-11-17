"""Build a deterministic Online Menu overlay for a fresh, exact-match MU1417 unit."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'verified/mu1417-20261117'
SHA = lambda b: hashlib.sha256(b).hexdigest()
STOCK_SI = 'a1ac27b4f405346548e8e1bec82b1f5c3483dc73050d682ad4c9a80808f7cbc7'
STOCK_IAP = 'd6d50af974a82feec2add942d3d8e6e88f96a2c25c469f747a11954b1c3445d7'

def build(efs: Path, output: Path) -> dict:
    provenance = json.loads((RELEASE / 'manifest.json').read_text())
    files = {}
    for name, expected in provenance['files'].items():
        data = (RELEASE / name).read_bytes()
        if SHA(data) != expected:
            raise ValueError('Changed verified release artifact: ' + name)
        files[name] = data
    si = (efs / 'etc/eso/production/smartphone_integrator.json').read_bytes()
    iap = (efs / 'etc/mm/iap2.cfg').read_bytes()
    if SHA(si) != STOCK_SI or SHA(iap) != STOCK_IAP:
        raise ValueError('Unknown firmware configuration; no generic conversion')
    old = b'"exec":"dio_manager",'
    if si.count(old) != 1:
        raise ValueError('Ambiguous CarPlay executable')
    files['smartphone_integrator.json'] = si.replace(old, b'"exec":"cw-carplay-start",')
    insertion = (b'# ConnectWow iAP2 Route Guidance message registration.\n'
                 b'[ident]\nrecvmsgs=0x5201,0x5202,0x5204\nsendmsgs=0x5200,0x5203\n\n')
    if iap.count(b'[commands]\n') != 1 or b'\n[ident]\n' in iap:
        raise ValueError('Unexpected iAP2 registration layout')
    files['iap2.cfg'] = iap.replace(b'[commands]\n', insertion + b'[commands]\n')
    if SHA(files['smartphone_integrator.json']) != '722b47123494e22b8fa4b4e50b3cce07f5b0399f1f31c7fd5e8f51ff981350d9':
        raise ValueError('SI differs from physically tested content')
    if SHA(files['iap2.cfg']) != '5ca0a762dcf24bef3661f77dc4641433767026e4500a2a60f2c60ed0cc77af41':
        raise ValueError('iAP2 differs from physically tested content')
    for name, source in [('cw-carplay-start', 'carplay_receiver_start.sh'),
                         ('mm-ipod.sh', 'mm_ipod_rgi.sh'), ('link-check.sh', 'portable_link_check.sh')]:
        files[name] = (ROOT / 'unit' / source).read_bytes().replace(b'\r\n', b'\n')
    if SHA(files['cw-carplay-start']) != '19728746c841f472e37df42aa1ff617d3bca2f37fefac35486e5d0b03d4a8118':
        raise ValueError('Receiver bootstrap is no longer the verified version')
    hmi = (ROOT / 'unit/portable_hmi.sh').read_text()
    for tag, name in [('@JAR_SHA@', 'PorscheNavigationPriority.test.jar'), ('@WINDOW_SHA@', 'cw-window-candidate')]:
        hmi = hmi.replace(tag, SHA(files[name]))
    files['hmi-start.sh'] = hmi.encode('ascii')
    manifest = ''.join(SHA(b) + ' ' + name + '\n' for name, b in sorted(files.items())).encode()
    manager = (ROOT / 'unit/portable_install.sh').read_text()
    checks = []
    targets = {'cw-window-candidate': '$ROOT/cw-window-candidate',
               'cw-receiver-controls.so': '$ROOT/cw-receiver-controls.so',
               'cw-rgi.so': '$ROOT/cw-rgi.so', 'libcw-query-stdio.so': '$ROOT/libcw-query-stdio.so',
               'PorscheNavigationPriority.test.jar': '$ROOT/PorscheNavigationPriority.test.jar',
               'hmi-start.sh': '$LSD', 'mm-ipod.sh': '$IPOD', 'cw-carplay-start': '$START',
               'smartphone_integrator.json': '$SI', 'iap2.cfg': '$IAP'}
    for name, target in targets.items():
        checks.append('check "' + target + '" ' + SHA(files[name]))
    checks.extend(['check "$DIO.cw-stock" 9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8',
                   'check "$LSD.cw-stock" 7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091',
                   'check "$REAL" d5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464'])
    restore_checks = ['check "$ROOT/installed.manifest" ' + SHA(manifest)]
    for name, target, stock in [
        ('hmi-start.sh', '$LSD', '7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091'),
        ('mm-ipod.sh', '$IPOD', 'd5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464'),
        ('smartphone_integrator.json', '$SI', STOCK_SI), ('iap2.cfg', '$IAP', STOCK_IAP)]:
        restore_checks.append('CURRENT=$(cw_hash "' + target + '")')
        restore_checks.append('[ "$CURRENT" = ' + SHA(files[name]) + ' ] || [ "$CURRENT" = ' + stock + ' ] || fail "Onbekend hersteldoel: ' + target + '"')
    manager = manager.replace('@MANIFEST_SHA@', SHA(manifest)).replace('@INSTALLED_CHECKS@', '\n'.join(checks))
    manager = manager.replace('@RESTORE_CHECKS@', '\n'.join(restore_checks))
    for name, data in [('manager', manager), ('hmi', hmi)]:
        if '@' in data.replace('"$@"', '') or re.search(r'^\s*\w+\s*\(\)\s*\{', data, re.M):
            raise ValueError('Unresolved template or unsupported ksh syntax: ' + name)
    actions = {'cwck': ('check', 'Controleer unit (zonder installatie)'),
               'cwin': ('install', 'Installeer geteste MU1417-versie (eenmalige proef)'),
               'cwok': ('confirm', 'Bevestig na geslaagde schermproef'),
               'cwback': ('restore', 'Herstel originele Porsche-startbestanden'),
               'cwboot': ('reboot', 'Herstart PCM (alleen stilstaand)'),
               'cwlog': ('logs', 'Kopieer diagnostiek naar SD'),
               'cwstat': ('status', 'Toon installatiestatus')}
    menu = (ROOT / 'templates/OnlineMenu.esd').read_text() + '\n\nscreen CWRelease OnlineMenu\n'
    for name, (_, label) in actions.items():
        menu += '\nscript\n   value sys 1 0x0100 "/scripts/online/' + name + '.sh"\n   label "' + label + '"\n'
    readme = (ROOT / 'docs/PORTABLE_INSTALL.md').read_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        def put(name, data, executable=False):
            info = zipfile.ZipInfo(name, (2026, 11, 17, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
        put('install/scripts/cwrel.sh', manager.encode(), True)
        put('install/esd/OnlineMenu.esd', menu.encode())
        for name, (action, _) in actions.items():
            body = '#!/bin/ksh\nBASE=${0%/*}\nexec /bin/ksh "$BASE/cwrel.sh" ' + action + '\n'
            put('install/scripts/' + name + '.sh', body.encode(), True)
        for name, data in sorted(files.items()):
            put('online/cw-release/' + name, data, name.endswith('.sh') or name in ('cw-window-candidate', 'cw-carplay-start'))
        put('online/cw-release/payload.manifest', manifest)
        put('LEESMIJ-INSTALLATIE.md', readme)
        put('release.json', json.dumps({'profile': provenance, 'fresh_installer_physically_verified': False,
                                      'payload': {n: SHA(b) for n, b in files.items()}}, indent=2).encode())
    return {'path': str(output), 'sha256': SHA(output.read_bytes()), 'files': len(files)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--efs-root', type=Path, required=True, help='Uitgepakte originele efs-system-configuratie')
    p.add_argument('--output', type=Path, default=ROOT / 'build/porsche-carplay-MU1417-portable.zip')
    args = p.parse_args()
    print(json.dumps(build(args.efs_root, args.output), indent=2))
if __name__ == '__main__':
    main()
