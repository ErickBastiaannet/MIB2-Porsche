"""Exercise real C wire/CRC/freshness checks used by the native candidate."""
import ctypes,shutil,subprocess,zlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_native_gate(tmp_path):
 if os.name=='nt':
  import pytest
  pytest.skip('Linux C wire fixture; run in the QNX toolchain container')
 cc=shutil.which('cc')
 if not cc:
  import pytest
  pytest.skip('Linux C compiler required')
 marker=tmp_path/'cw-nav-priority.enabled';wire=tmp_path/'cw-nav-priority.v1'
 source=tmp_path/'gate.c';source.write_text('#include <stdint.h>\n#include <unistd.h>\n#include "porsche_wire.h"\n#define CW_NAV_PRIORITY_ROOT "'+tmp_path.as_posix()+'"\n#include "priority_gate.h"\nint gate(unsigned owner,unsigned now){return cw_nav_allowed_at(owner,now); }\n')
 lib=tmp_path/'gate.so'
 subprocess.run([cc,'-std=c99','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror','-fPIC','-shared','-I'+str(ROOT/'native'),'-I'+str(ROOT/'optional/navigation-priority/native'),str(source),str(ROOT/'native/porsche_wire.c'),'-o',str(lib)],check=True)
 f=ctypes.CDLL(str(lib)).gate;f.argtypes=[ctypes.c_uint,ctypes.c_uint];f.restype=ctypes.c_int
 def record(generation=1,at=10,allow=1,owner=1234):
  b=f'CWNP1 {generation} {at} {allow} {owner} '.encode();wire.write_bytes(b+f'{zlib.crc32(b):08x}\n'.encode())
 assert f(1234,10)==1 # opt-out leaves baseline behavior
 marker.write_text('enabled');assert f(1234,10)==0
 record();assert f(1234,10)==1 and f(1234,13)==1
 assert f(1234,14)==0 and f(9999,10)==0 and f(0,10)==0
 record(at=11);assert f(1234,10)==0
 record(allow=0);assert f(1234,10)==0
 record(allow=2);assert f(1234,10)==0
 record(generation=0);assert f(1234,10)==0
 record();wire.write_bytes(wire.read_bytes().replace(b'1234',b'1235'));assert f(1234,10)==0
 wire.write_bytes(b'CWNP1 invalid\n');assert f(1234,10)==0
 wire.write_bytes(b'x'*300);assert f(1234,10)==0
 marker.unlink();assert f(1234,10)==1

def test_priority_restore_budget(tmp_path):
 """A measured ~1s DMDT query must not exhaust the complete restore budget."""
 if os.name=='nt':
  import pytest
  pytest.skip('Linux C compiler fixture')
 import runpy
 runpy.run_path(str(ROOT/'build-tools/prepare_navigation_priority_native.py'))['generate']()
 text=(ROOT/'build/navigation-priority/porsche_unit.c').read_text()
 body=text[text.index('static int priority_restore('):text.index('static int supervisor(',text.index('static int priority_restore('))]
 source=tmp_path/'restore.c'
 source.write_text('''#include <stdint.h>
#include <stddef.h>
typedef struct {unsigned id,context;} cw_display;
static uint64_t clock_ms; static unsigned current=70, switches;
static uint64_t cw_monotonic_ms(void){return clock_ms;}
static int cw_dm_query_until(const char*r,const char*c,char*t,size_t n,uint64_t deadline){(void)r;(void)c;(void)t;(void)n;clock_ms+=1000;return clock_ms<=deadline;}
static int cw_dm_display(const char*t,cw_display*d){(void)t;d->id=1;d->context=current;return 1;}
static int cw_dm_switch_until(const char*r,unsigned d,unsigned target,uint64_t deadline){(void)r;(void)d;clock_ms+=1000;if(clock_ms>deadline)return 0;current=target;++switches;return 1;}
'''+body+'''int main(void){if(!priority_restore("fixture",72)||current!=72||switches!=1)return 1;clock_ms=0;current=70;switches=0;if(priority_restore("fixture",158)||switches)return 2;return 0;}
''')
 binary=tmp_path/'restore'
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True)
 subprocess.run([str(binary)],check=True)
