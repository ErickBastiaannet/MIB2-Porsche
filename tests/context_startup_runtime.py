"""Actual supervisor + bounded CLI queries, with only the GPU worker stubbed.

Exercises ordering/ownership/fallback; does not prove hardware startup latency.
Run after prepare_context_startup.py in the existing Linux Python image.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
    base = Path(folder)
    runtime = base / 'runtime'
    profile = b'fixture-profile\n'
    worker = r'''static int decode_worker(const cw_geometry *geometry,const char *root,unsigned original,pid_t parent) {
        uint32_t frame[4]={1,0,geometry->width,geometry->height};
        char path[512];int fd;(void)original;
        snprintf(path,sizeof(path),"%s/window",root);fd=open(path,O_CREAT|O_WRONLY,0600);if(fd<0)return 1;close(fd);
        while(!stopped&&getppid()==parent){frame[1]=now_seconds();cw_wire_write(VIDEO_READY,"CWRD1",frame,4);frame[0]++;pause_ms(50);}
        unlink(path);return 0;
    }'''
    for label, source in [('baseline', ROOT/'native/porsche_unit.c'), ('candidate', ROOT/'build/context-startup/porsche_unit.c')]:
        text = source.read_text()
        start = text.index('#ifdef CW_YUV_RENDERER\nstatic int decode_worker')
        end = text.index('\n#endif\n\nstatic void restore_context', start)
        text = text[:start] + '#ifdef CW_YUV_RENDERER\n' + worker + text[end:]
        file = base / (label + '.c')
        file.write_text(text)
        subprocess.run(['cc', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                        '-DCW_YUV_RENDERER', '-DCW_RUNTIME="'+str(runtime)+'"',
                        '-DCW_DMDT="'+str(runtime/'dmdt')+'"',
                        '-DCW_DISPLAY_CONFIG="'+str(runtime/'dm-profile')+'"',
                        '-DCW_DISPLAY_CONFIG_SHA="'+hashlib.sha256(profile).hexdigest()+'"',
                        '-I'+str(ROOT/'native'), '-I'+str(ROOT/'build/native'), str(file),
                        *[str(ROOT/'native'/('porsche_'+n+'.c')) for n in
                          ['sha256','jar','wire','dm','geometry','geometry_file','session','nvss']],
                        '-ldl', '-o', str(base/label)], check=True)
    subprocess.run(['cc','-shared','-fPIC',str(ROOT/'unit-query/query_stdio.c'),'-o',str(base/'query.so')],check=True)

    def until(test, timeout=12):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if test():return
            time.sleep(.05)
        raise AssertionError('startup condition timed out: '+(runtime/'log').read_text())

    def scenario(label, blocked=False, foreign=False, occupied=False):
        runtime.mkdir()
        (runtime/'context').write_text('72')
        (runtime/'dm-profile').write_bytes(profile)
        (runtime/'enabled').touch()
        if not blocked:(runtime/'gc-ready').touch()
        if occupied:(runtime/'occupied').touch()
        shutil.copyfile(base/'query.so', runtime/'libcw-query-stdio.so')
        dmdt=runtime/'dmdt'
        dmdt.write_text('''#!/usr/local/bin/python
import sys,time
from pathlib import Path
r=Path('''+repr(str(runtime))+''');cmd=sys.argv[1]
if cmd=='gs':print('displaymanager reports the following system information:\\ndisplay 1:\\n terminal: 2nd_lvds\\n size: 800 x 480\\n context id: '+(r/'context').read_text())
elif cmd=='gd':
 print('displaymanager knows 1 displayables:')
 if (r/'window').exists() or (r/'occupied').exists():print(' 78 window 800 x 480')
elif cmd=='gc':
 while not (r/'gc-ready').exists():time.sleep(.05)
 ids=[78,33] if (r/'overlay').exists() else []
 print('displaymanager knows 1 contexts:\\n 70 | '+str(len(ids))+' | NONE')
 for item in ids:print(' '+str(item)+' (DISPLAYABLE)')
elif cmd=='dc' and sys.argv[2:]==['70','78','33']:(r/'overlay').touch()
elif cmd=='sc' and sys.argv[2]=='4':(r/'context').write_text(sys.argv[3])
else:sys.exit(1)
''')
        # Production sc argv is verified backend id followed by context.
        dmdt.chmod(0o755)
        owner=subprocess.Popen(['sleep','60'])
        if foreign:
            prefix=f'CWCO1 {owner.pid} {int(time.time())} 70 78 '
            (runtime/'cw-porsche-context-owner.v1').write_text(prefix+f'{zlib.crc32(prefix.encode())&0xffffffff:08x}\n')
        log=(runtime/'log').open('wb')
        process=subprocess.Popen([str(base/label),'--run',str(runtime),str(owner.pid)],stdout=log,stderr=log)
        try:
            def refresh():
                (runtime/'cw-porsche-altstream.ready').write_text(f'{owner.pid} {int(time.time())}\n')
            import threading
            stop=threading.Event()
            def publish():
                while not stop.is_set():refresh();stop.wait(.2)
            thread=threading.Thread(target=publish);thread.start()
            if label=='baseline':
                time.sleep(6)
                assert not (runtime/'window').exists()
                assert (runtime/'context').read_text()=='72'
            elif foreign:
                time.sleep(3)
                assert not (runtime/'window').exists()
                assert (runtime/'context').read_text()=='72'
            else:
                until(lambda:(runtime/'window').exists())
                if blocked:
                    time.sleep(4.5)
                    assert process.poll() is None and (runtime/'context').read_text()=='72'
                    assert not (runtime/'cw-carplay-ready.v1').exists()
                    assert (runtime/'log').read_text().count('CARPLAY_WORKER_STARTED')==1
                    (runtime/'gc-ready').touch()
                until(lambda:(runtime/'context').read_text()=='70')
                assert (runtime/'cw-carplay-ready.v1').exists()
                stop.set();thread.join();(runtime/'cw-porsche-altstream.ready').unlink()
                until(lambda:(runtime/'context').read_text()=='72')
                assert not (runtime/'cw-carplay-ready.v1').exists()
        finally:
            stop.set();thread.join()
            process.terminate()
            try:process.wait(timeout=12)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            owner.terminate();owner.wait();log.close()
            shutil.rmtree(runtime)

    scenario('baseline',blocked=True)
    scenario('candidate',blocked=True)
    scenario('candidate',foreign=True)
print('CONTEXT_STARTUP_RUNTIME_PASS baseline blocks worker; candidate warms once while OEM stays; context gate; live owner rejected; disconnect restores OEM')
