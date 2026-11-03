"""Build an update-only SD overlay from locally verified Porsche artifacts."""
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent.parent
FILES = {
    'porsche-carplay': 'build/qnx/porsche-carplay-window-candidate',
    'libcw-porsche-capture_receiver.so': 'build/qnx/libcw-porsche-capture_receiver.so',
    'libcw-porsche-rgi.so': 'build/qnx/libcw-porsche-rgi.so',
    'libcw-query-stdio.so': 'build/qnx/libcw-query-stdio.so',
    'dio_manager.sh': 'unit/dio_manager.sh',
}
INSTRUCTIONS = '''ConnectWow CarPlay - Panamera K5137 / MU1417
================================================
Dit is de volledige MU1417-portkandidaat. De lokale controles slagen en
CarPlay-video met veilige kaartterugval is fysiek op de Panamera aangetoond.
Geen Android Auto, geen wijziging van de centrale CarPlay-bediening.

1. Maak een kopie van je bestaande online-menu-SD-kaart.
2. Pak deze ZIP uit OVER de bestaande SD-kaart. Bewaar de bestaande
   online/server-ip.txt, certificaten, metainfo2.txt en overige bestanden.
3. Gebruik in het bestaande online menu de functie om menu/scripts bij te
   werken. Dit is GEEN volledige firmware- of SWDL-installatie.
4. Open daarna OnlineMenu > CarPlay > Install CarPlay cluster (MU1417).
   De installatie controleert firmware, payload en originele startbestanden.
   Bij een afwijzing wordt niet alsnog een ander firmwareprofiel geprobeerd.
5. Herstart PCM. Laat eerst de originele kaart rechts in het instrumenten-
   paneel zien. Verbind vervolgens de iPhone met CarPlay en open Apple Kaarten.
   De tweede CarPlay-stroom wordt pas aangeboden na geldige runtime-geometrie.
6. OnlineMenu > CarPlay > Status toont geometrie en goedgekeurde videolease.
   CARPLAY_ACTIVE betekent dat decoder, beeldkwaliteit en displaymanager de
   koppeling accepteerden.

De standaard zoomrol werkt ook op de CarPlay-kaart. De Porsche levert signed
MapScale-stappen; ConnectWow stuurt deze als semantische zoom-in/zoom-uit naar
de actieve clusterkaart. iOS/de kaart-app kiest de zichtbare meterschaal. Snelle
stappen worden begrensd en gepaced; omkeren en opnieuw verbinden wissen oude
input. Apple Kaarten en Google Maps ondersteunen deze opdracht. Waze kan hem
ontvangen maar app-zijdig negeren; dat is geen fout in de Porsche-bediening.

Original Porsche map schakelt de clusterkaart terug. CarPlay map schakelt
automatische overname weer in. De telefoon kan opnieuw verbinden nodig hebben.
Met CarPlay verbonden mogen ondersteunde iOS-appmeldingen het centrale MMI
tijdelijk lenen, ook als de Porsche-interface zichtbaar is. Dit vereist dat de
melding op de iPhone voor CarPlay is toegestaan; de patch omzeilt geen privacy.
Restore original DIO herstelt de oorspronkelijke DIO-starter; herstart
PCM daarna. Back-ups blijven op SD en unit bewaard. Verwijder die niet.

De poort gebruikt een eigen videolaag 78 en een eigen kaartcontext 70.
Alleen de originele DIO-starter wordt vervangen en zowel op SD als op de unit
bewaard. De HMI/Java-starter blijft byte-voor-byte origineel; deze kandidaat
kan daardoor het laden van de oorspronkelijke Porsche-kaart niet blokkeren.
Bij een installatiefout wordt de DIO-starter direct teruggezet.
Andere instrumentpagina's blijven behouden. Zonder geldige videolease wordt
de originele kaart gekozen. Certificaten, hosts, satellietproxy en verkeers-
diensten worden niet gewijzigd. Er wordt geen ruwe telefoonvideo opgeslagen.

Installeer bij stilstaande auto. Dit pakket voegt geen CarPlay-licentie toe.
De semantische manoeuvre-, afstand-, rijstrook- en meldingsuitbreidingen zijn
bewust niet actief in deze native-only videokandidaat. Ze volgen pas nadat de
clusterstream met een echte route stabiel is bevestigd.
Bij problemen: gebruik Status; bewaar /ramdisk/cw-porsche-carplay.log en
/ramdisk/cw-porsche-airplay.log voordat PCM opnieuw wordt opgestart.
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_hmi_class_versions(data, maximum=48):
    """Enforce the Java limit observed in the physical MU1417 runtime.

    Java 17 verification does not establish compatibility with J9 Foundation.
    Apply this check to every OEM override as well as the helper classes.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
        for name in jar.namelist():
            if not name.endswith('.class'):
                continue
            bytecode = jar.read(name)
            if len(bytecode) < 10 or bytecode[:4] != b'\xca\xfe\xba\xbe':
                raise ValueError('Invalid Java class: ' + name)
            major = struct.unpack_from('>H', bytecode, 6)[0]
            if major > maximum:
                raise ValueError('Incompatible Porsche J9 class version '
                                 + str(major) + ' (maximum ' + str(maximum) + '): ' + name)


def main():
    profile = json.loads((ROOT / 'firmware-profile.json').read_text())
    if not profile.get('sd_candidate_available', False):
        raise SystemExit('SD installation is withdrawn: visible CarPlay stream and display routing '
                         'still require validation. Hidden decoder acceptance is insufficient.')
    for manifest_path in ['build/qnx/sources.sha256', 'build/qnx/artifacts.sha256']:
        for line in (ROOT / manifest_path).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            if digest((ROOT / name).read_bytes()) != expected:
                raise SystemExit('Stale QNX build; rebuild before packaging: ' + name)
    payload = {name: (ROOT / path).read_bytes() for name, path in FILES.items()}
    for name, data in payload.items():
        if name.endswith('.so') or name == 'porsche-carplay':
            if data[:7] != b'\x7fELF\x01\x01\x01' or struct.unpack_from('<H', data, 18)[0] != 40:
                raise SystemExit('Not little-endian ARM ELF: ' + name)
    manifest = ''.join(digest(data) + ' ' + name + '\n' for name, data in payload.items()).encode()
    manage = (ROOT / 'unit/carplay_manage.sh').read_text(encoding='utf-8')
    manage = manage.replace('@VERIFIER_SHA256@', digest(payload['porsche-carplay']))
    manage = manage.replace('@MANIFEST_SHA256@', digest(manifest))
    menu = (REPO / 'resources/online-setup/source/install/esd/OnlineMenu.esd').read_text(encoding='utf-8')
    menu += '\n# Porsche CarPlay cluster; no changes to existing online services\nscreen CarPlay OnlineMenu\n'
    archive = ROOT / 'build/porsche-carplay-native-MU1417-candidate.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        def write(name, data, executable=False):
            info = zipfile.ZipInfo(name, (2026, 10, 28, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, data)
        for action, label in [
            ('install', 'Install CarPlay cluster (MU1417)'),
            ('status', 'Status (read only)'),
            ('enable', 'CarPlay map'),
            ('disable', 'Original Porsche map'),
            ('restore', 'Restore original launchers'),
        ]:
            name = 'carplay_' + action + '.sh'
            launcher = '#!/bin/sh\nBASE=${0%/*}\nexec /bin/sh "$BASE/carplay_manage.sh" ' + action + ' "$@"\n'
            write('install/scripts/' + name, launcher.encode(), True)
            menu += '\nscript\n   value sys 1 0x0100 "/scripts/online/' + name + '"\n   label "' + label + '"\n'
        write('install/scripts/carplay_manage.sh', manage.encode(), True)
        write('install/esd/OnlineMenu.esd', menu.encode())
        for name, data in payload.items():
            write('online/carplay/' + name, data, name == 'porsche-carplay' or name.endswith('.sh'))
        write('online/carplay/payload.manifest', manifest)
        write('LEESMIJ-CARPLAY.txt', INSTRUCTIONS.encode('utf-8'))
        write('online/carplay/LICENSE.upstream', (ROOT / 'LICENSE.upstream').read_bytes())
        write('online/carplay/build-info.json', json.dumps({
            'firmware': 'MHI2_ER_POG24_K5137_MU1417_971919360T',
            'status': 'native-only MU1417 video candidate; HMI/Java remains stock; semantic guidance disabled pending physical validation',
            'upstream': 'omonob/MHI2-Carplay-Maps c645c379f26ed5db7e252f80297d6f7cb4468a34',
            'payload_sha256': digest(manifest),
            'right_display_physically_verified': True,
            'semantic_guidance_physically_verified': False,
            'background_carplay_notifications': False,
            'notification_scope': 'CarPlay connected; app and iOS permission required',
            'unit_changed_by_builder': False,
        }, indent=2).encode())
    (ROOT / 'build/sd-package.json').write_text(json.dumps({
        'path': archive.name, 'sha256': digest(archive.read_bytes()),
        'status': 'candidate', 'right_display_physically_verified': True,
        'semantic_guidance_physically_verified': False,
    }, indent=2) + '\n')
    (ROOT / 'build/LEESMIJ-CARPLAY.txt').write_text(INSTRUCTIONS, encoding='utf-8', newline='\n')
    print(str(archive))
    print('SD overlay built; right display proven, semantic guidance awaits an in-car route test')


if __name__ == '__main__':
    main()
