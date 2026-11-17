"""Generate the isolated MU1417 startup candidate; never edit the live baseline."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]

def generate():
    source = ROOT / 'native/porsche_unit.c'
    text = source.read_text()
    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('Unexpected startup baseline: ' + old[:90])
        text = text.replace(old, new, 1)

    # Purely observational diagnostics: distinguish query, layout and ownership.
    replace('static int prepare_context(const char *root) {', '''static int context_wait(const char *reason,int state,uint64_t since) {
    fprintf(stderr,"CARPLAY_CONTEXT_WAIT reason=%s state=%d t_ms=%llu elapsed_ms=%llu\\n",
        reason,state,(unsigned long long)cw_monotonic_ms(),
        (unsigned long long)(cw_monotonic_ms()-since));
    return 0;
}
static int startup_owner_conflict(void) {
    uint32_t owner[4];
    if(access(CONTEXT_OWNER,F_OK)!=0)return errno!=ENOENT;
    if(!cw_wire_read(CONTEXT_OWNER,"CWCO1",owner,4)||owner[0]<=1||owner[2]!=70||owner[3]!=LAYER)return 1;
    return owner[0]!=(uint32_t)getpid() && (kill((pid_t)owner[0],0)==0 || errno!=ESRCH);
}
static int prepare_context(const char *root) {''')
    replace('''    int state;
    if (!cw_dm_query(root, "gc", report, sizeof(report)))
        return 0;
    state = cw_dm_context_state''', '''    int state;
    uint64_t since=cw_monotonic_ms();
    if (!cw_dm_query(root, "gc", report, sizeof(report)))
        return context_wait("query",-1,since);
    state = cw_dm_context_state''')
    replace('''            owner[3] != LAYER)
            return 0;''', '''            owner[3] != LAYER)
            return context_wait("owner-record",state,since);''')
    replace('''        if (owner[0] != (uint32_t)getpid() && (kill((pid_t)owner[0], 0) == 0 || errno != ESRCH))
            return 0;
    } else
        return 0;''', '''        if (owner[0] != (uint32_t)getpid() && (kill((pid_t)owner[0], 0) == 0 || errno != ESRCH))
            return context_wait("live-owner",state,since);
    } else
        return context_wait(state<0?"report":"layout",state,since);''')
    replace('''    return cw_wire_write(CONTEXT_OWNER, "CWCO1", owner, 4);
}''', '''    if(!cw_wire_write(CONTEXT_OWNER,"CWCO1",owner,4))return context_wait("owner-write",state,since);
    fprintf(stderr,"CARPLAY_CONTEXT_PREPARED t_ms=%llu\\n",(unsigned long long)cw_monotonic_ms());
    return 1;
}''')
    replace('''                if (!prepare_context(root)) {
                    fputs("CARPLAY_CONTEXT_NOT_AVAILABLE\\n", stderr);''', '''                /* Match the reference ordering: create a renderer on a verified
                 * free displayable before requiring its presentation context.
                 * Existing windows still require the original strict owner gate. */
                int window_free=cw_dm_layer(text,LAYER,geometry.width,geometry.height,0);
                if ((window_free && startup_owner_conflict()) ||
                    (!window_free && !prepare_context(root))) {
                    fprintf(stderr,"CARPLAY_CONTEXT_NOT_AVAILABLE stage=pre-render t_ms=%llu\\n",
                        (unsigned long long)cw_monotonic_ms());''')
    replace('''                {
                    uint32_t snapshot[3] = {now_seconds(), original, original};''', '''                if(window_free)fprintf(stderr,"CARPLAY_CONTEXT_DEFERRED free-window=78 t_ms=%llu\\n",
                    (unsigned long long)cw_monotonic_ms());
                {
                    uint32_t snapshot[3] = {now_seconds(), original, original};''')
    replace('''                if (output_ok)
                    output_ok = cw_dm_declare_overlay(root);''', '''                /* No switch/ready lease until the unchanged context ownership
                 * and composition checks pass, after useful pixels exist. */
                if (output_ok)
                    output_ok = prepare_context(root) && cw_dm_declare_overlay(root);''')
    replace('''fprintf(stderr, "CARPLAY_ACTIVE display=%u context=%u size=%ux%u\\n", target.id,
                            own, ready[2], ready[3]);''', '''fprintf(stderr, "CARPLAY_ACTIVE display=%u context=%u size=%ux%u t_ms=%llu\\n", target.id,
                            own, ready[2], ready[3],(unsigned long long)cw_monotonic_ms());''')
    target = ROOT / 'build/context-startup'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'porsche_unit.c').write_text(text, encoding='utf-8', newline='\n')
    (target / 'input.json').write_text(json.dumps({
        'baseline_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'scope': 'native startup only; strict context ownership before publication',
        'physically_verified': False,
    }, indent=2) + '\n')
    print('CONTEXT_STARTUP_SOURCE_READY baseline unchanged')

if __name__ == '__main__':
    generate()
