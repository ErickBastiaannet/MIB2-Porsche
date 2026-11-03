"""Run the actual coordinator, ring reader and decoder adapter with fake hardware.

The subprocess really forks the worker, loads its decoder API dynamically,
consumes binary ring slots and executes a substitute displaymanager CLI.
This proves wiring and fallback, not hardware output or iPhone compatibility.
"""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import threading
import time
import unittest
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'build/host-test'


@unittest.skipUnless((HOST/'porsche-carplay').exists(), 'Build host runtime fixtures first')
class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.root=Path('/tmp/cw-runtime')
        self.root.mkdir()  # refuse any pre-existing directory
        for name in ['libnvss_video.so','libcw-query-stdio.so']:
            shutil.copyfile(HOST/name,self.root/name)
        (self.root/'context').write_text('72')
        (self.root/'dm-profile').write_bytes(b'fixture-profile\n')
        (self.root/'enabled').touch()
        self.process=None
        self.owner=subprocess.Popen(['sleep','60'])
        self.log=open(self.root/'runtime.log','wb')
        dmdt=self.root/'dmdt'
        dmdt.write_text('''#!/usr/local/bin/python
import sys
from pathlib import Path
root=Path('/tmp/cw-runtime')
cmd=sys.argv[1]
if cmd=='gs': print('displaymanager reports the following system information:\\ndisplay 1:\\n terminal: 2nd_lvds\\n size: 960 x 640\\n context id: '+(root/'context').read_text())
elif cmd=='gd':
    print('displaymanager knows 1 displayables:')
    if (root/'window').exists(): print(' 78 stream 0 x 0' if (root/'stream-kind').exists() else ' 78 window 960 x 640')
elif cmd=='gc':
    ids=([78,33] if (root/'overlay-order').read_text()=='78,33' else [33,78]) if (root/'overlay').exists() else ([78] if (root/'declared').exists() else [])
    print('displaymanager knows 1 contexts:\\n 70 | '+str(len(ids))+' | NONE')
    for item in ids: print(' '+str(item)+' (DISPLAYABLE)')
elif cmd=='dc' and sys.argv[2:] == ['70','78']: (root/'declared').touch()
elif cmd=='dc' and sys.argv[2:] in [['70','33','78'],['70','78','33']]:
    (root/'declared').touch(); (root/'overlay').touch(); (root/'overlay-order').write_text(','.join(sys.argv[3:]))
elif cmd=='sc' and sys.argv[2]=='4' and 0<=int(sys.argv[3])<=157: (root/'context').write_text(sys.argv[3])
else: sys.exit(1)
''')
        dmdt.chmod(0o755)

    def tearDown(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
        self.owner.terminate(); self.owner.wait(timeout=3)
        self.log.close()
        shutil.rmtree(self.root)

    def publish(self, generation=1, idr=True):
        config=bytes([1,66,0,30,255,225,0,2,103,1,1,0,2,104,1])
        video=bytes([0,0,0,2,101 if idr else 65,1])
        slot_size=28+256*1024
        ring=bytearray(16+64*slot_size)
        struct.pack_into('<IIII',ring,0,0x43505247,1,generation,2)
        for index,(kind,data) in enumerate([(1,config),(2,video)]):
            offset=16+index*slot_size
            struct.pack_into('<IIIIIII',ring,offset,index+1,kind,len(data),1,index+1,0,0)
            ring[offset+28:offset+28+len(data)]=data
        path=self.root/'cw-porsche-alt-ring.bin'
        # Update the existing inode, as the real producer does on reconnect.
        with path.open('r+b' if path.exists() else 'wb') as stream: stream.write(ring)
        (self.root/'cw-porsche-altstream.ready').write_text(f'{self.owner.pid} {int(time.time())}\n')

    def start(self):
        env=dict(os.environ,LD_LIBRARY_PATH=str(self.root))
        self.process=subprocess.Popen([str(HOST/'porsche-carplay'),'--run',str(self.root),str(self.owner.pid)],
                                      stdout=self.log,stderr=self.log,env=env)

    def wait_context(self, wanted, seconds=8):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            if (self.root/'context').read_text()==str(wanted): return
            if self.process.poll() is not None: break
            time.sleep(.05)
        self.log.flush()
        self.fail('Context not reached: '+str(wanted)+'\n'+(self.root/'runtime.log').read_text())

    def test_video_handover_and_disconnect_restore(self):
        self.publish(); self.start(); self.wait_context(70)
        self.assertTrue((self.root/'cw-carplay-ready.v1').exists())
        (self.root/'cw-porsche-altstream.ready').unlink(); self.wait_context(72)
        self.assertFalse((self.root/'cw-carplay-ready.v1').exists())

    def test_disabled_map_preserves_original(self):
        (self.root/'enabled').unlink(); self.publish(); self.start()
        time.sleep(1)
        self.assertEqual((self.root/'context').read_text(),'72')
        self.assertFalse((self.root/'window').exists())

    def test_non_idr_does_not_replace_original(self):
        self.publish(idr=False); self.start(); time.sleep(1)
        self.assertEqual((self.root/'context').read_text(),'72')
        self.assertFalse((self.root/'cw-carplay-ready.v1').exists())

    def test_direct_stream_layer_does_not_replace_original_map(self):
        (self.root/'stream-kind').touch()
        self.publish(); self.start(); time.sleep(1.5)
        self.assertEqual((self.root/'context').read_text(),'72')
        self.assertFalse((self.root/'cw-carplay-ready.v1').exists())

    def test_unknown_display_configuration_does_not_switch(self):
        (self.root/'dm-profile').write_bytes(b'unknown configuration\n')
        self.publish(); self.start(); time.sleep(1.5)
        self.assertEqual((self.root/'context').read_text(),'72')

    def test_driver_other_page_not_overridden_on_disconnect(self):
        self.publish(); self.start(); self.wait_context(70)
        (self.root/'context').write_text('75')
        (self.root/'cw-porsche-altstream.ready').unlink()
        time.sleep(1)
        self.assertEqual((self.root/'context').read_text(),'75')

    def test_stale_producer_lease_cannot_replay_old_video(self):
        self.publish(); self.start(); self.wait_context(70)
        self.wait_context(72)
        time.sleep(2.5)
        self.assertEqual((self.root/'context').read_text(),'72')
        self.assertFalse((self.root/'cw-carplay-ready.v1').exists())

    def test_reconnect_after_disconnect(self):
        self.publish(); self.start(); self.wait_context(70)
        (self.root/'cw-porsche-altstream.ready').unlink(); self.wait_context(72)
        time.sleep(2.1)
        self.publish(generation=2); self.wait_context(70)

    def test_worker_restores_map_if_supervisor_dies(self):
        self.publish(); self.start(); self.wait_context(70)
        self.process.kill(); self.process.wait(timeout=3)
        until=time.monotonic()+5
        while time.monotonic()<until:
            if (self.root/'context').read_text()=='72': break
            time.sleep(.1)
        self.assertEqual((self.root/'context').read_text(),'72')

    def start_visible_probe(self):
        config=bytes([1,66,0,30,255,225,0,2,103,1,1,0,2,104,1])
        frame=bytes([0,0,0,2,101,1])
        vector=self.root/'test-vector'
        vector.write_bytes(b'CWNV'+struct.pack('>4I',960,640,len(config),len(frame))+config+frame)
        self.process=subprocess.Popen([str(HOST/'cw-visible-decode'),str(self.root),str(vector),'--visible-test-5s'],
            env=dict(os.environ,LD_LIBRARY_PATH=str(self.root)),stdout=self.log,stderr=self.log)

    def test_visible_probe_returns_to_original_map(self):
        self.start_visible_probe(); self.wait_context(70); self.wait_context(72)
        self.assertEqual(self.process.wait(timeout=8),0)
        self.assertIn('VISIBLE_TEST_MAP_RESTORED',(self.root/'runtime.log').read_text())
        self.assertFalse((self.root/'window').exists())

    def test_visible_probe_guardian_restores_map_after_parent_is_killed(self):
        self.start_visible_probe(); self.wait_context(70)
        self.process.kill(); self.process.wait(timeout=3)
        until=time.monotonic()+8
        while time.monotonic()<until:
            if (self.root/'context').read_text()=='72': break
            time.sleep(.05)
        self.assertEqual((self.root/'context').read_text(),'72')

    def start_visible_window(self,overlay=False,top=False):
        mode='--visible-window-overlay-top-5s' if top else ('--visible-window-overlay-5s' if overlay else '--visible-window-5s')
        self.process=subprocess.Popen([str(HOST/'cw-visible-window'),str(self.root),mode],
            stdout=self.log,stderr=self.log)

    def test_visible_window_restores_map_and_removes_window(self):
        self.start_visible_window();self.wait_context(70);self.wait_context(72)
        self.assertEqual(self.process.wait(timeout=8),0)
        self.assertFalse((self.root/'window').exists())

    def test_visible_window_guardian_recovers_after_parent_is_killed(self):
        self.start_visible_window();self.wait_context(70)
        self.process.kill();self.process.wait(timeout=3)
        until=time.monotonic()+8
        while time.monotonic()<until:
            if (self.root/'context').read_text()=='72':break
            time.sleep(.05)
        self.assertEqual((self.root/'context').read_text(),'72')

    def test_overlay_retains_map_displayable_and_restores_original_context(self):
        self.start_visible_window(overlay=True);self.wait_context(70)
        self.assertTrue((self.root/'overlay').exists())
        self.wait_context(72);self.assertEqual(self.process.wait(timeout=8),0)
        self.assertFalse((self.root/'window').exists())
        self.assertIn('keep_map=1',(self.root/'runtime.log').read_text())

    def test_overlay_alternate_order_retains_map_and_restores_context(self):
        self.start_visible_window(top=True);self.wait_context(70)
        self.assertEqual((self.root/'overlay-order').read_text(),'78,33')
        self.wait_context(72);self.assertEqual(self.process.wait(timeout=8),0)
        self.assertFalse((self.root/'window').exists())

    def test_overlay_order_can_change_only_after_previous_owner_exits(self):
        self.start_visible_window(overlay=True);self.wait_context(70);self.wait_context(72)
        self.assertEqual(self.process.wait(timeout=8),0)
        self.start_visible_window(top=True);self.wait_context(70)
        self.assertEqual((self.root/'overlay-order').read_text(),'78,33')
        self.wait_context(72);self.assertEqual(self.process.wait(timeout=8),0)

    def test_overlay_does_not_take_context_from_a_live_owner(self):
        (self.root/'declared').touch();(self.root/'overlay').touch()
        (self.root/'overlay-order').write_text('33,78')
        prefix=f'CWCO1 {self.owner.pid} {int(time.time())} 70 78 '
        (self.root/'cw-porsche-context-owner.v1').write_text(prefix+f'{zlib.crc32(prefix.encode())&0xffffffff:08x}\n')
        self.start_visible_window(top=True)
        self.assertEqual(self.process.wait(timeout=5),1)
        self.assertEqual((self.root/'context').read_text(),'72')
        self.assertEqual((self.root/'overlay-order').read_text(),'33,78')
        self.assertFalse((self.root/'window').exists())
        self.assertIsNone(self.owner.poll())

    def test_actual_native_archive_conflict_scanner(self):
        good=self.root/'good.jar'; bad=self.root/'bad.jar'; invalid=self.root/'invalid.jar'
        with zipfile.ZipFile(good,'w',zipfile.ZIP_DEFLATED) as archive: archive.writestr('some/Other.class',b'anything')
        with zipfile.ZipFile(bad,'w') as archive: archive.writestr('de/audi/tghu/fwhmi/DisplayManagerMIB2High.class',b'conflict')
        invalid.write_bytes(b'PK invalid')
        for path,expected in [(good,0),(bad,1),(invalid,1)]:
            result=subprocess.run([str(HOST/'porsche-carplay'),'--check-jar',str(path)],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,expected)
        output=subprocess.check_output([str(HOST/'porsche-carplay'),'--hash',str(good)],text=True)
        self.assertEqual(output.strip(),hashlib.sha256(good.read_bytes()).hexdigest())
