"""Offline source arbitration: deliberately no production adapters or install."""
import os,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_priority_transitions(tmp_path):
 jdk=Path(os.environ.get('JAVA_HOME',''))/'bin'
 def tool(n):
  for p in [jdk/n,jdk/(n+'.exe')]:
   if p.is_file():return str(p)
  value=shutil.which(n)
  if value:return value
  import pytest
  pytest.skip('JDK required')
 fixture=tmp_path/'PriorityFixture.java'
 fixture.write_text(r'''import org.connectwow.carplay.PorscheNavigationPriority;
import org.connectwow.carplay.PorscheNavigationPriority.Decision;
public final class PriorityFixture {
 static void check(boolean b){if(!b)throw new AssertionError();}
 static void ack(PorscheNavigationPriority p,Decision d){if(d.pending)check(p.acknowledge(d));}
 public static void main(String[] args){
  PorscheNavigationPriority cold=new PorscheNavigationPriority();
  Decision initial=cold.request(-1,false,false,0L);check(initial.pending&&!cold.mayShowCarPlay());
  ack(cold,initial);check(!cold.request(-1,false,false,0L).pending);
  int cases=0;
  for(int first=-1;first<=2;first++)for(int fv=0;fv<2;fv++)for(int fg=0;fg<2;fg++)for(int fs=0;fs<3;fs++)
   for(int next=-1;next<=2;next++)for(int nv=0;nv<2;nv++)for(int ng=0;ng<2;ng++)for(int ns=0;ns<3;ns++){
    PorscheNavigationPriority p=new PorscheNavigationPriority();
    Decision a=p.request(first,fv==1,fg==1,fs);ack(p,a);
    Decision b=p.request(next,nv==1,ng==1,ns);
    check(b.mapSource==(next==0&&nv==1&&ns>0?2:1));
    if(next!=0||nv==0||ns==0)check(!p.mayShowCarPlay()&&!p.mayForwardCarPlayGuidance()&&!p.mayUseCarPlayZoom());
    boolean wasCarPlay=first==0&&fv==1&&fs>0;
    boolean wantsCarPlay=next==0&&nv==1&&ns>0;
    check(p.mayShowCarPlay()==(wasCarPlay&&wantsCarPlay&&fs==ns));
    int wantsGuidance=wantsCarPlay?(ng==1?2:0):1;
    check(b.guidanceSource==wantsGuidance);
    check(b.clearCarPlayGuidance==(wasCarPlay&&fg==1&&(wantsGuidance!=2||fs!=ns)));
    if(b.pending && b.releaseOemPresentation)check(!p.mayShowCarPlay());
    check(p.request(next,nv==1,ng==1,ns).generation==b.generation);
    if(a.generation!=b.generation)check(!p.acknowledge(a));
    ack(p,b);check(p.mayShowCarPlay()==(next==0&&nv==1&&ns>0));
    check(p.mayForwardCarPlayGuidance()==(next==0&&nv==1&&ns>0&&ng==1));
    check(p.shouldSuppressSatelliteLogo()==p.mayShowCarPlay());
    cases++;
   }
  PorscheNavigationPriority p=new PorscheNavigationPriority();
  Decision a=p.request(0,true,true,1L);check(a.replayCarPlayGuidance&&a.releaseOemPresentation);ack(p,a);
  Decision o=p.request(1,true,true,1L);check(o.clearCarPlayGuidance&&!p.mayForwardCarPlayGuidance());ack(p,o);
  Decision arrival=p.request(2,true,true,1L);ack(p,arrival);check(!p.mayShowCarPlay());
  Decision back=p.request(0,true,true,1L);check(back.replayCarPlayGuidance);ack(p,back);
  Decision reconnect=p.request(0,false,false,1L);check(reconnect.clearCarPlayGuidance);ack(p,reconnect);
  Decision mapOnly=p.request(0,true,false,1L);ack(p,mapOnly);check(p.mayShowCarPlay()&&!p.mayForwardCarPlayGuidance());
  Decision stale=p.request(0,true,true,1L);Decision stop=p.request(1,true,true,1L);check(!p.acknowledge(stale));ack(p,stop);
  Decision resume=p.request(0,true,true,1L);ack(p,resume);
  Decision changed=p.request(0,true,true,2L);check(changed.clearCarPlayGuidance&&changed.replayCarPlayGuidance&&!p.mayShowCarPlay());ack(p,changed);
  Decision unidentified=p.request(0,true,true,0L);check(unidentified.mapSource==1);ack(p,unidentified);
  p.request(-1,true,true,1L);check(!p.mayShowCarPlay());
  // Guidance ending/restarting must preserve the already-active map/zoom/logo.
  Decision map=p.request(0,true,true,3L);ack(p,map);
  Decision noRoute=p.request(0,true,false,3L);check(noRoute.clearCarPlayGuidance&&p.mayShowCarPlay()&&p.mayUseCarPlayZoom()&&p.shouldSuppressSatelliteLogo());
  check(!p.mayForwardCarPlayGuidance());ack(p,noRoute);
  Decision newRoute=p.request(0,true,true,3L);check(newRoute.replayCarPlayGuidance&&p.mayShowCarPlay());ack(p,newRoute);
  // A token from another instance can have the same generation, but cannot commit.
  PorscheNavigationPriority other=new PorscheNavigationPriority();
  PorscheNavigationPriority victim=new PorscheNavigationPriority();
  Decision foreign=other.request(0,true,true,5L);Decision own=victim.request(0,true,true,5L);
  check(foreign.generation==own.generation&&!victim.isCurrentTransition(foreign)&&!victim.acknowledge(foreign));ack(victim,own);
  // Unrelated CarPlay refreshes cannot starve pending OEM cleanup.
  Decision takeover=p.request(1,true,true,3L);
  Decision refreshed=p.request(1,false,false,4L);check(refreshed==takeover&&p.isCurrentTransition(takeover));ack(p,takeover);
  // Invalid state/session values fail closed even after successful CarPlay ownership.
  Decision cp=p.request(0,true,true,6L);ack(p,cp);
  Decision invalid=p.request(99,true,true,6L);check(invalid.mapSource==1&&invalid.clearCarPlayGuidance&&!p.mayShowCarPlay());ack(p,invalid);
  ack(p,p.request(0,true,true,6L));p.request(0,true,true,-1L);check(!p.mayShowCarPlay());
  System.out.println("NAVIGATION_PRIORITY_POLICY_PASS "+cases+" transitions; OEM preemption; arrival hold; stale completion; map-only; replay; zoom/logo gate");
 }
}''')
 source=ROOT/'optional/navigation-priority/org/connectwow/carplay/PorscheNavigationPriority.java'
 subprocess.run([tool('javac'),'--release','8','-d',str(tmp_path),str(source),str(fixture)],check=True)
 r=subprocess.run([tool('java'),'-Xverify:all','-cp',str(tmp_path),'PriorityFixture'],capture_output=True,text=True,check=True)
 assert 'NAVIGATION_PRIORITY_POLICY_PASS 2304 transitions' in r.stdout


def test_baseline_sources_do_not_reference_priority_candidate():
 # Optional candidates do not modify baseline runtime sources or enter baseline artifacts
 # through the current Java-source glob or split-JAR allowlists.
 for directory in ['java','native','unit']:
  for p in (ROOT/directory).rglob('*'):
   if p.is_file() and p.suffix in {'.java','.c','.h','.inc','.py','.sh'}:
    text=p.read_text(encoding='utf-8')
    assert 'PorscheNavigationPriority' not in text,str(p)
    assert 'optional/navigation-priority' not in text,str(p)
