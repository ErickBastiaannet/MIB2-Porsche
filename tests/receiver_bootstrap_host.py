"""Linux-host test: explicit capture env on each exec, same PID, safe fallback."""
import os,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);root=p/'controls';root.mkdir();runtime=p/'runtime';stock=p/'stock';wrapper=p/'receiver.sh'
 c=p/'stock.c';c.write_text('''#include <stdio.h>\n#include <stdlib.h>\n#include <unistd.h>\nint main(int argc,char **argv){printf("%ld|%s|%s|%s|%s\\n",(long)getpid(),getenv("CW_PROCESS_SUPERVISOR")?getenv("CW_PROCESS_SUPERVISOR"):"unset",getenv("CARPLAY_ALTSCREEN_ENABLE")?getenv("CARPLAY_ALTSCREEN_ENABLE"):"unset",getenv("LD_PRELOAD")?getenv("LD_PRELOAD"):"unset",argc>1?argv[1]:"none");return 0;}''')
 subprocess.run(['cc',str(c),'-o',str(stock)],check=True)
 so=p/'empty.c';so.write_text('void cw_fixture(void){}')
 subprocess.run(['cc','-shared','-fPIC',str(so),'-o',str(root/'cw-receiver-controls.so')],check=True)
 for n in ['enabled','installed.manifest','libcw-query-stdio.so']:(root/n).write_text('fixture')
 (root/'cw-window-candidate').write_text('fixture');(root/'cw-window-candidate').chmod(0o755)
 text=(ROOT/'unit/carplay_receiver_start.sh').read_text().replace('/mnt/app/eso/hmi/connectwow-carplay/controls-v15',str(root)).replace('/mnt/app/eso/bin/apps/dio_manager.cw-stock',str(stock)).replace('/ramdisk/cw-link-probe-20261102',str(runtime))
 wrapper.write_text(text)
 env={k:v for k,v in os.environ.items() if not k.startswith(('CW_','CARPLAY_ALTSCREEN')) and k!='LD_PRELOAD'}
 for _ in range(3):
  proc=subprocess.Popen(['/bin/sh',str(wrapper),'pass-through'],env=env,stdout=subprocess.PIPE,text=True)
  assert proc.communicate()[0]=='';assert proc.returncode==0
  output=(runtime/'cw-carplay-live-v14.log').read_text().splitlines()[-1].split('|')
  assert output==[str(proc.pid),'1','1',str(root/'cw-receiver-controls.so'),'pass-through'],output
 assert (runtime/'enabled').read_text().strip()=='enabled'
 assert len((runtime/'receiver-start.log').read_text().splitlines())==3
 # An unavailable diagnostics path must not prevent the receiver's exec.
 log=runtime/'cw-carplay-live-v14.log';log.unlink();log.mkdir()
 proc=subprocess.Popen(['/bin/sh',str(wrapper),'log-unavailable'],env=env,stdout=subprocess.PIPE,text=True)
 output=proc.communicate()[0].strip().split('|');assert proc.returncode==0
 assert output==[str(proc.pid),'1','1',str(root/'cw-receiver-controls.so'),'log-unavailable'],output
 log.rmdir()
 (root/'enabled').unlink()
 proc=subprocess.Popen(['/bin/sh',str(wrapper),'fallback'],env=env,stdout=subprocess.PIPE,text=True)
 output=proc.communicate()[0].strip().split('|');assert output==[str(proc.pid),'unset','unset','unset','fallback']
print('RECEIVER_BOOTSTRAP_PASS 3 fresh starts; explicit video env; same PID; args preserved; disabled fallback')
