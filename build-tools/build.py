"""Build only local research artifacts; never contacts or modifies a unit."""
import argparse
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'de/audi/atip/base/IFrameworkAccess': 'cb27ed1bcfc808cd42c46464e936955e345c9a5dc1cd6bb35f8e25b05dbda393',
    'de/audi/tghu/navi/app/NavigationEnv': '8dc3b1dbd19f906bc40a91c2d5bdaab5ae59c858d541d91f43e445967432f0d5',
    'org/dsi/ifc/navigation/BapTurnToInfo': '5bd0bc8ce0543bdc433bd6a41c240b75837d4ef3ab57fcae5e9f96f836aab0f0',
    'de/audi/atip/interapp/combi/bap/navi/data/CombiBAPNaviDestination': '2623cd8b7703cd7f3c5c127d8275230057a804e42e1b8b965d3ff77c0d9c6e8b',
    'de/audi/atip/interapp/combi/bap/navi/data/CombiBAPDestinationInfo': '904cbe0bc273cfbd4e94e5831abc8b6f0c2649570a568dff22dca1138e2871dc',
    'de/audi/tghu/navi/app/map/gui/layout/LayoutProviderG22Kombi': 'a2b9e2c8912e50bb325a86fb4f522d44a3a9343d718e23172dac0677c36d54aa',
    'de/audi/tghu/navi/app/map/gui/layout/AbstractLayoutProvider': 'fc95fd5f2ca00ff2bfb7ad72b478431a8ce47be112322f3f69fd5b1fbf7599c7',
    'de/audi/tghu/navi/app/cluster/ClusterService': '30a7dff7d34f21491c950f9aa4f450a0f4cf5c4eba77a76a6a526ae1171f4fe9',
    'de/audi/app/terminalmode/smartphone/carplay/CarPlayDSIManager': '7121f859632c00374cfb79412b6b97e6f903dd7bd89f3c5bf05ca6c9b180943c',
    'org/dsi/ifc/map/Rect': 'c86bb78003e3af1d7ed4f5b5366bc9bc15c9eb8512595eea7ba41af0ad839435',
    'de/audi/tghu/fwhmi/DisplayManagerMIB2High': '2e40642a5dc09e97d0a586704704e61603a047d60dbdbcfe042babfb02371165',
    'de/audi/tghu/navi/app/cluster/CombiBAPListener': 'f4fa8fed034cd9d0b82850e7bb41b70aa2167711f2fe9f917f95ae6475e13166',
    'org/dsi/ifc/carplay/AppState': 'b498cd7fbfd0cda382aa43dbdf9748a480c1f0447d550100d727efa9a4903e21',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--oem-jar', type=Path, required=True)
    parser.add_argument('--jdk', type=Path, required=True, help='Directory containing java and javac')
    parser.add_argument('--display-jar', type=Path, required=True, help='Recovered Porsche display classes')
    parser.add_argument('--destination-jar', type=Path, default=ROOT / 'build/porsche-destination-api.jar', help='Exact recovered MU1417 destination classes; see recover_destination_api.py')
    args = parser.parse_args()
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    entries = {}
    for path in [args.oem_jar, args.display_jar, args.destination_jar]:
        with zipfile.ZipFile(path) as jar:
            for name in jar.namelist():
                data = jar.read(name)
                if name in entries and data != entries[name]:
                    raise SystemExit('Conflicting recovered class: ' + name)
                entries[name] = data
    for name, expected in EXPECTED.items():
        actual = hashlib.sha256(entries[name + '.class']).hexdigest()
        if actual != expected:
            raise SystemExit('Unsupported or changed recovered OEM class: ' + name)
    combined = build / 'recovered-input.jar'
    with zipfile.ZipFile(combined, 'w') as jar:
        for name, data in entries.items():
            jar.writestr(name, data)
    stubs = {
        'de/audi/atip/base/IFrameworkAccess':
        'package de.audi.atip.base; public interface IFrameworkAccess { long getUTCTime(); long convertUTCTimeToLocalTime(long value); }',
        'de/audi/tghu/navi/app/NavigationEnv':
        'package de.audi.tghu.navi.app; public class NavigationEnv { private de.audi.atip.base.IFrameworkAccess fw; public NavigationEnv(de.audi.atip.base.IFrameworkAccess fw){this.fw=fw;} public de.audi.atip.base.IFrameworkAccess getFramework(){return fw;} }',
        'de/audi/tghu/navi/app/map/gui/layout/AbstractLayoutProvider':
        'package de.audi.tghu.navi.app.map.gui.layout; public abstract class AbstractLayoutProvider { public abstract int getScreenWidth(); public abstract int getScreenHeight(); }',
        'org/dsi/ifc/map/Rect':
        'package org.dsi.ifc.map; public class Rect { public int kordX,kordY,diffX,diffY; }',
        'org/dsi/ifc/displaymanagement/DisplayContext':
        'package org.dsi.ifc.displaymanagement; public class DisplayContext { public int id; public int[] layers; public DisplayContext(int id, int[] layers) { this.id=id; this.layers=layers; } }',
        'org/dsi/ifc/navigation/BapManeuverDescriptor':
        'package org.dsi.ifc.navigation; public class BapManeuverDescriptor { public byte[] sideStreets; public BapManeuverDescriptor(int a,int b,int c,byte[] d){sideStreets=d;} }',
        'org/dsi/ifc/navigation/NavLaneGuidanceData':
        'package org.dsi.ifc.navigation; public class NavLaneGuidanceData { public short laneDirection; public byte[] laneSideStreets; public byte guidanceInfo; public NavLaneGuidanceData(short a,short b,byte[] c,short d,byte e,byte f,byte g,byte h){laneDirection=b;laneSideStreets=c;guidanceInfo=h;} }',
        'de/audi/tghu/navi/app/cluster/CombiBAPListener':
        'package de.audi.tghu.navi.app.cluster; import org.dsi.ifc.navigation.*; public class CombiBAPListener { int distanceCalls,destinationDistance,destinationTime,clearCalls; boolean rgActive,lanesShown,failNextLaneClear; int viewMode,maneuverPhase; de.audi.tghu.navi.app.NavigationEnv env; boolean destinationEta; org.dsi.ifc.navigation.BapTurnToInfo[] turnInfo; byte[] sideStreets; int emittedDistance,emittedBargraph; String currentStreet; de.audi.atip.interapp.combi.bap.navi.data.CombiBAPDestinationInfo destinationInfo; boolean failNextDestinationClear; public void setDestinationInfo(de.audi.atip.interapp.combi.bap.navi.data.CombiBAPDestinationInfo v){if(failNextDestinationClear && v.getDestination().getCity().length()==0){failNextDestinationClear=false;throw new RuntimeException("fixture destination clear");}destinationInfo=v;} void updateBapManeuverState(int v){maneuverPhase=v;} void setViewMode(int v){viewMode=v;} void setRgActive(boolean v){rgActive=v;} void setGALState(boolean v){if(!v)clearCalls++;} void setDistanceToNextManeuver(int a,boolean b,int c){distanceCalls++;emittedDistance=a;emittedBargraph=c;} void setManeuverDescriptor(BapManeuverDescriptor[] v){sideStreets=v.length>0?v[0].sideStreets:new byte[0];} void setTurnToInfo(org.dsi.ifc.navigation.BapTurnToInfo[] v){turnInfo=v;} void setLaneGuidance(NavLaneGuidanceData[] v,boolean e){if(!e&&failNextLaneClear){failNextLaneClear=false;throw new RuntimeException("fixture failure");}lanesShown=e;} void setCurrentStreet(String v){currentStreet=v;} void setRgDistanceToNextDestination(int v,boolean valid){destinationDistance=v;} void setRgTimeToNextDestination(long v,boolean eta,boolean valid){destinationTime=(int)(v/1000L);destinationEta=eta;} }',
    }
    sources = []
    for name, source in stubs.items():
        target = build / 'stubs' / (name + '.java')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding='utf-8')
        sources.append(str(target))
    def run(tool, *params):
        program = args.jdk / tool
        if not program.exists():
            program = args.jdk / (tool + '.exe')
        subprocess.run([str(program), *map(str, params)], check=True)
    classes = build / 'classes'
    run('javac', '--release', '8', '-cp', args.destination_jar, '-d', classes, *sources,
        *ROOT.joinpath('java').rglob('*.java'), *ROOT.joinpath('tests').rglob('*.java'))
    exports = [value for package in ['asm', 'asm.tree', 'asm.tree.analysis']
               for value in ['--add-exports', 'java.base/jdk.internal.org.objectweb.' + package + '=ALL-UNNAMED']]
    run('javac', *exports, '-d', build, ROOT / 'build-tools/BuildPorscheHooks.java')
    output = build / 'PorscheCarPlayBridge.experimental.jar'
    notifications = build / 'PorscheCarPlayNotifications.experimental.jar'
    run('java', *exports, '-cp', build, 'BuildPorscheHooks', combined, classes, output, notifications)
    run('java', '-cp', str(notifications) + os.pathsep + str(classes), 'NotificationFixture')
    run('java', '-cp', str(classes) + os.pathsep + str(args.destination_jar), 'de.audi.tghu.navi.app.cluster.RouteGuidanceTextFixture', str(build / 'guidance-fixture.state'))
    run('java', '-cp', str(output) + os.pathsep + str(classes), 'org.connectwow.tests.ClusterFixture', str(build / 'cluster-fixture'))
    run('java', '-cp', str(output) + os.pathsep + str(classes), 'org.connectwow.tests.ControlsFixture', str(build / 'fixture'))
    (build / 'build-manifest.json').write_text(json.dumps({
        'firmware': 'MHI2_ER_POG24_K5137_MU1417_971919360T',
        'source_classes_sha256': EXPECTED,
        'artifact_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'notifications_sha256': hashlib.sha256(notifications.read_bytes()).hexdigest(),
        'artifact_role': 'HMI bridge for alternate display, zoom and route guidance; requires native SD candidate package. Notification compatibility is a separate probe JAR.',
        'physical_unit_verified': False, 'unit_modified': False,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
