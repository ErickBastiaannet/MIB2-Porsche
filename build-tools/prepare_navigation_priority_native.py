"""Generate an opt-in native map-priority candidate without editing baseline sources."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def generate():
 # Priority must extend the currently installed startup fix, not resurrect the
 # older pre-context decoder gate. Regenerate that isolated input explicitly.
 import runpy
 runpy.run_path(str(ROOT/'build-tools/prepare_context_startup.py'))['generate']()
 source=ROOT/'build/context-startup/porsche_unit.c';text=source.read_text()
 replacements=[
 ('static int supervisor(const char *root, pid_t owner, int bounded_test) {', 'static int priority_restore(const char *root, unsigned original) {\n    char text[16384]; cw_display display; uint64_t deadline=cw_monotonic_ms()+4000;\n    if (original>157 || !cw_dm_query_until(root,"gs",text,sizeof(text),deadline) || !cw_dm_display(text,&display)) return 0;\n    if(display.context!=70) return 1;\n    if(!cw_dm_switch_until(root,display.id,original,deadline)) return 0;\n    return cw_dm_query_until(root,"gs",text,sizeof(text),deadline) && cw_dm_display(text,&display) && display.context!=70;\n}\nstatic int supervisor(const char *root, pid_t owner, int bounded_test) {'),
 ('    int lock = -1, active = 0;', '    int lock = -1, active = 0, priority_restore_pending = 0;'),
 ('#define LAYER 78U', '#define LAYER 78U\n#include "priority_gate.h"'),
 ('        cw_display observed;\n', '        int navigation_allowed = cw_nav_allowed_at((uint32_t)owner, now_seconds());\n        if (!navigation_allowed) {\n            unlink(READY);\n            if (active) { priority_restore_pending=1; fputs("CARPLAY_PRIORITY_RESTORE_OEM\\n", stderr); }\n            if (priority_restore_pending && priority_restore(root,original)) priority_restore_pending=0;\n            active = 0;\n            (void)cw_session_stop(&session);\n        } else priority_restore_pending=0;\n        cw_display observed;\n'),
 ('            if (publish_geometry(root, &observed, maintenance_deadline) && active &&', '            int geometry_published = publish_geometry(root, &observed, maintenance_deadline);\n            if (geometry_published && !navigation_allowed && observed.context != 70) {\n                uint32_t state[4], acknowledgement[4];\n                if (cw_wire_read("/ramdisk/cw-nav-priority.v1", "CWNP1", state, 4)) {\n                    acknowledgement[0]=state[0]; acknowledgement[1]=now_seconds();\n                    acknowledgement[2]=0; acknowledgement[3]=(uint32_t)owner;\n                    (void)cw_wire_write("/ramdisk/cw-nav-priority.applied", "CWNPA1", acknowledgement, 4);\n                }\n            }\n            if (geometry_published && active && navigation_allowed &&'),
 ('cw_monotonic_ms() + (active ? 1000 : 4000)', 'cw_monotonic_ms() + ((active || !navigation_allowed) ? 1000 : 4000)'),
 ('                if (cw_wire_read(VIDEO_READY, \"CWRD1\", lease, 4) && lease[0] > 0 &&', '                if (cw_nav_allowed_at((uint32_t)owner, now_seconds()) && cw_wire_read(VIDEO_READY, \"CWRD1\", lease, 4) && lease[0] > 0 &&'),
 ('actions = child > 0 ? cw_session_update', 'actions = child > 0 && navigation_allowed ? cw_session_update'),
 ('        if (child > 0 && cw_wire_read(VIDEO_READY, "CWRD1", ready, 4) && ready[0] > 0 &&', '        if (child > 0 && cw_nav_allowed_at((uint32_t)owner, now_seconds()) && cw_wire_read(VIDEO_READY, "CWRD1", ready, 4) && ready[0] > 0 &&'),
 ('            if (output_ok && !cw_wire_write(READY, "CWRD1", ready, 4))', '            if (!cw_nav_allowed_at((uint32_t)owner, now_seconds())) output_ok = 0;\n            if (output_ok && access("/ramdisk/cw-nav-priority.enabled", F_OK) != 0 && !cw_wire_write(READY, "CWRD1", ready, 4))'),
 ('        pause_ms(100);\n    }\n    unlink(READY);', '        if (access("/ramdisk/cw-nav-priority.enabled", F_OK) == 0 && active &&\n            cw_nav_allowed_at((uint32_t)owner, now_seconds()) &&\n            cw_wire_read(VIDEO_READY, "CWRD1", ready, 4) && ready[0] > 0 &&\n            ready[1] <= now_seconds() && now_seconds()-ready[1] <= 3)\n        {\n            uint32_t state[4], acknowledgement[4];\n            (void)cw_wire_write(READY, "CWRD1", ready, 4);\n            if (cw_wire_read("/ramdisk/cw-nav-priority.v1", "CWNP1", state, 4) && state[2] == 1 && state[3] == (uint32_t)owner) {\n                acknowledgement[0]=state[0]; acknowledgement[1]=now_seconds(); acknowledgement[2]=1; acknowledgement[3]=(uint32_t)owner;\n                (void)cw_wire_write("/ramdisk/cw-nav-priority.applied", "CWNPA1", acknowledgement, 4);\n            }\n        }\n        pause_ms(100);\n    }\n    unlink(READY);'),
 ('                    cw_dm_switch(root, target.id, own) &&', '                    cw_nav_allowed_at((uint32_t)owner, now_seconds()) &&\n                    cw_dm_switch(root, target.id, own) &&'),
 ]
 for old,new in replacements:
  if text.count(old)!=1:raise ValueError('Unexpected native anchor: '+old)
  text=text.replace(old,new)
 target=ROOT/'build/navigation-priority';target.mkdir(exist_ok=True)
 (target/'porsche_unit.c').write_text(text,encoding='utf-8',newline='\n')
 (target/'priority_gate.h').write_bytes((ROOT/'optional/navigation-priority/native/priority_gate.h').read_bytes())
 (target/'native-input.json').write_text(json.dumps({'baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'opt_in':'/ramdisk/cw-nav-priority.enabled','state':'/ramdisk/cw-nav-priority.v1','magic':'CWNP1','fields':['generation','timestamp','allow','producer']},indent=2)+'\n')
 print('PRIORITY_NATIVE_SOURCE_READY baseline untouched')
if __name__=='__main__':generate()
