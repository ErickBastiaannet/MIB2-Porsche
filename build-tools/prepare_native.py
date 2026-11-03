"""Generate Porsche negotiation/receiver sources from the pinned upstream."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'c645c379f26ed5db7e252f80297d6f7cb4468a34'
SOURCE_HASH = '587883e03897be26582a553c61575eb554ad5207b7b156d1cfa94f42d8735305'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('--capture-profile', type=Path, help='Verified native-security JSON; builds an experimental capture receiver, not a renderer')
    args = parser.parse_args()
    upstream = args.upstream.resolve()
    commit = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != COMMIT:
        raise SystemExit('Unsupported upstream revision')
    source = upstream / 'src/card-core/source'
    original = (source / 'altscreen_handshake_probe.c').read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_HASH:
        raise SystemExit('Upstream handshake source changed')
    target = ROOT / 'build/native'
    target.mkdir(parents=True, exist_ok=True)
    for header in source.glob('*.h'):
        shutil.copyfile(header, target / header.name)
    for native in ROOT.joinpath('native').glob('*'):
        shutil.copyfile(native, target / native.name)
    text = original.decode('utf-8')
    text = text.replace('    int stream_type = -1;', '#ifdef ALTSCREEN_PASSIVE_CAPTURE\n    int stream_type = -1;\n#endif', 1)
    start = text.index('static void *create_alt_display(void)')
    end = text.index('static OSStatus append_alt_display', start)
    text = text[:start] + '#include "porsche_display.inc"\n\n' + text[end:]
    # Recent CarKit consumes the physical-panel contract from displayPanels,
    # while AirPlaySender selects stream 110/111 from displays. Publish the
    # exact same two-display array under both keys atomically.
    text = text.replace(
        'status = set_object(server_info, "displays", new_displays);',
        'status = set_object(server_info, "displays", new_displays);\n'
        '        if (!status) status = set_object(server_info, "displayPanels", new_displays);',
        1,
    )
    name = 'porsche_handshake_probe.c'
    if args.capture_profile:
        profile = json.loads(args.capture_profile.read_text(encoding='utf-8'))
        profile = profile.get('airplay', profile)
        if (profile['library_sha256'] != '816f1fa8b333ca091676cea65d405f36adb82ceee5119eb6f8f99538678b527a'
                or profile['session_key_offset'] != 456 or profile['function_bytes'] != 108
                or profile['function_fnv1a'] != 2480334254):
            raise SystemExit('Unsupported capture security profile')
        prefix = '\n'.join('#define ' + flag + ' 1' for flag in [
            'CW_PORSCHE_CAPTURE', 'ALTSCREEN_PASSIVE_CAPTURE', 'ALTSCREEN_STOCK_FIRST_SETUP',
            'ALTSCREEN_STOCK_RESPONSE_MERGE', 'ALTSCREEN_ADVERTISE_SOURCE_950',
            'ALTSCREEN_ADVERTISE_CARPLAY_CONTROL', 'ALTSCREEN_ACTIVATE_DISPLAY',
            'ALTSCREEN_ACTIVATE_ON_SCREEN_READY', 'ALTSCREEN_AES_CTR_DECRYPT', 'ALTSCREEN_FORWARD_SHM_RING',
            'ALTSCREEN_LISTEN_IPV6', 'ALTSCREEN_RUNTIME_MAP_CONTROL'])
        prefix += '\n#define VW790_CARD_SIDE 0\n#define ALTSCREEN_FORCE_KEYFRAME_INTERVAL 25ULL\n'
        # MU1417 pf.conf permits TCP 7000:7001 on carplay0 and drops other
        # inbound ports. An ephemeral listener accepts SETUP but never video.
        prefix += '#include "porsche_network.h"\n#define ALTSCREEN_FIXED_PORT CW_CARPLAY_DATA_PORT\n'
        prefix += '#define ALT_FRAME_RING_PATH "/ramdisk/cw-porsche-alt-ring.bin"\n'
        prefix += '#define ALT_FRAME_FORCE_IDR_PATH "/ramdisk/cw-porsche-alt-force-idr.request"\n'
        guard = '''static int cw_check_airplay(void) {
    const unsigned char *code = (const unsigned char *)dlsym(RTLD_NEXT, "AirPlayReceiverSessionSetSecurityInfo");
    uint32_t hash = 2166136261U; unsigned i;
    if (!code) return 0;
    for (i = 0; i < CW_FUNCTION_BYTES; ++i) hash = (hash ^ code[i]) * 16777619U;
    return hash == CW_FUNCTION_FNV;
}
'''.replace('CW_FUNCTION_BYTES', str(profile['function_bytes']) + 'U').replace('CW_FUNCTION_FNV', str(profile['function_fnv1a']) + 'U')
        needle = 'static int enabled(void)'
        text = text.replace(needle, guard + '\n' + needle, 1)
        text = text.replace('return value && value[0] && strcmp(value, "0") != 0;',
                            'return value && value[0] && strcmp(value, "0") != 0 && cw_check_airplay();', 1)
        text = text.replace('if (count >= 2) {', 'if (count != 1) {', 1)
        text = text.replace('        return 0;\n    }\n    alt_display = create_alt_display();',
                            '        return -1;\n    }\n    alt_display = create_alt_display();', 1)
        text = text.replace('        append_alt_display(result);',
                            '        if (append_alt_display(result) == 0) cw_add_extended_features(result);', 1)
        needle = '        memset(alt_aes_key, 0, sizeof(alt_aes_key));'
        text = text.replace(needle, '''        {
            uint32_t security_ready = 0;
            if (!session) return -1;
            memcpy(&security_ready, (const uint8_t *)session + 452U, sizeof(security_ready));
            if (!security_ready) return -1;
        }
''' + needle, 1)
        text = text.replace('typedef struct PassiveListener {', 'typedef struct PassiveListener {\n    cw_geometry geometry;', 1)
        text = text.replace('    listener->server_fd = fd;', '''    if (!cw_copy_advertised_geometry(&listener->geometry)) {
        close(fd); free(listener); return -1;
    }
    listener->server_fd = fd;''', 1)
        text = text.replace('if ((int)width == ALTSCREEN_DISPLAY_WIDTH &&\n                (int)height == ALTSCREEN_DISPLAY_HEIGHT && body_size > 0)',
                            'if (width == (float)listener->geometry.width &&\n                height == (float)listener->geometry.height && body_size > 0)', 1)
        # Validate floating header dimensions before integer logging/caching.
        needle = '            write_capture_file("alt-video-config.bin", body, body_size);'
        text = text.replace(needle, '''            if (!(width >= 64 && width <= 8192 && height >= 64 && height <= 8192)
                    || width != (float)listener->geometry.width || height != (float)listener->geometry.height) break;
''' + needle, 1)
        # The capture receiver never changes a display context. Distinct names
        # keep its volatile artifacts separate from the original VW deployment.
        text = text.replace('"/ramdisk/carplay-altstream.ready"', '"/ramdisk/cw-porsche-altstream.ready"')
        text = text.replace('"/ramdisk/carplay-bridge.ready"', '"/ramdisk/cw-porsche-bridge.ready"')
        # Bound a disconnected peer's read without introducing a receiver restart.
        text = text.replace('        count = recv(fd, buffer + offset, size - offset, 0);',
                            '        if (wait_readable(fd, 5) <= 0) return -1;\n        count = recv(fd, buffer + offset, size - offset, 0);', 1)
        text = text.replace('    cw_geometry geometry;', '    cw_geometry geometry;\n    uint32_t epoch;', 1)
        marker_start = text.index('static int create_marker(const char *path)')
        marker_end = text.index('static int consume_marker', marker_start)
        text = text[:marker_start] + '''static int create_marker(const char *path)
{
    char temporary[512], record[64]; int fd, length;
    if (snprintf(temporary, sizeof(temporary), "%s.%ld.tmp", path, (long)getpid()) >= (int)sizeof(temporary)) return -1;
    length = snprintf(record, sizeof(record), "%ld %lu\\n", (long)getpid(), (unsigned long)time(NULL));
    fd = open(temporary, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) return -1;
    if (write(fd, record, (size_t)length) != length) { close(fd); unlink(temporary); return -1; }
    if (close(fd) || rename(temporary, path)) { unlink(temporary); return -1; }
    return 0;
}

''' + text[marker_end:]
        start = text.index('static void *passive_listener_thread')
        end = text.index('static OSStatus start_passive_listener', start)
        thread = text[start:end]
        thread = thread.replace('int stream_ready_signaled = 0;', 'time_t stream_ready_signaled = 0;')
        thread = thread.replace('!stream_ready_signaled)', 'stream_ready_signaled != time(NULL))')
        thread = thread.replace('stream_ready_signaled = 1;', 'stream_ready_signaled = time(NULL);')
        thread = thread.replace('unlink(ALTSCREEN_READY_PATH)', 'cw_marker(listener->epoch, ALTSCREEN_READY_PATH, 0)')
        thread = thread.replace('unlink(ALTSCREEN_BRIDGE_READY_PATH)', 'cw_marker(listener->epoch, ALTSCREEN_BRIDGE_READY_PATH, 0)')
        thread = thread.replace('create_marker(ALTSCREEN_READY_PATH)', 'cw_marker(listener->epoch, ALTSCREEN_READY_PATH, 1)')
        thread = thread.replace('consume_marker(ALTSCREEN_BRIDGE_READY_PATH)', 'cw_marker(listener->epoch, ALTSCREEN_BRIDGE_READY_PATH, 2) == 1')
        thread = thread.replace('consume_marker(ALT_FRAME_FORCE_IDR_PATH)', 'cw_marker(listener->epoch, ALT_FRAME_FORCE_IDR_PATH, 2) == 1')
        thread = thread.replace('close(listener->server_fd);', 'cw_close_owner(listener->epoch, listener->server_fd);')
        thread = thread.replace('    if (client_fd < 0) {', '''    if (client_fd >= 0 && !cw_accept_owner(listener->epoch, client_fd)) {
        close(client_fd); client_fd = -1;
    }
    if (client_fd < 0) {''', 1)
        thread = thread.replace('create_forward_ring()', 'cw_ring(listener->epoch)')
        thread = thread.replace('forward_ring_message(', 'cw_forward(listener->epoch, ')
        thread = thread.replace('if (client_fd >= 0) close(client_fd);', 'cw_close_owner(listener->epoch, client_fd);')
        thread = thread.replace('        if (read_exact(client_fd, header, sizeof(header)) != 0) break;',
                                '        if (!cw_current(listener->epoch) || read_exact(client_fd, header, sizeof(header)) != 0) break;')
        thread = thread.replace('        ++messages;', '        if (!cw_current(listener->epoch)) break;\n        ++messages;', 1)
        text = text[:start] + '#include "porsche_capture_owner.inc"\n\n' + thread + text[end:]
        text = text.replace('    status = pthread_create(&thread, NULL, passive_listener_thread, listener);',
                            '    listener->epoch = cw_claim(fd);\n    status = pthread_create(&thread, NULL, passive_listener_thread, listener);', 1)
        # Thread creation failure must unregister before another claim can reuse fd.
        text = text.replace('    if (status != 0) {\n        close(fd);',
                            '    if (status != 0) {\n        cw_close_owner(listener->epoch, fd);', 1)
        # The thread can finish before pthread_create returns. Save the port first.
        text = text.replace('    listener->epoch = cw_claim(fd);', '    *out_port = listener->port;\n    listener->epoch = cw_claim(fd);', 1)
        text = text.replace('    *out_port = listener->port;\n    return 0;', '    return 0;', 1)
        # V14.5 keeps the proven native-only display path, but mirrors the
        # stock Porsche day/night state to the UUID-addressed cluster screen.
        # It also permits one guarded initial zoom-out after showUI; no HMI
        # class is needed for either operation.
        text = text.replace(
            '} else if (!status && strcmp(type, "requestUI") == 0) {',
            '} else if (!status && strcmp(type, "setNightMode") == 0) {\n'
            '        status = set_cstring(params, "uuid", ALT_UUID);\n'
            '        if (!status) status = set_int(params, "nightMode", zoom_direction ? 1 : 0);\n'
            '    } else if (!status && strcmp(type, "requestUI") == 0) {',
            1,
        )
        map_end = text.index('#endif /* ALTSCREEN_RUNTIME_MAP_CONTROL */')
        night_hook = r'''
typedef OSStatus (*CwSetNightModeFn)(void *, int, void *, void *);
OSStatus AirPlayReceiverSessionSetNightMode(void *session, int night,
                                            void *completion, void *context)
{
    static CwSetNightModeFn real_function;
    void *map_session = NULL;
    OSStatus stock_status;
    if (!real_function)
        real_function = (CwSetNightModeFn)resolve("AirPlayReceiverSessionSetNightMode");
    if (!real_function) return -1;
    stock_status = real_function(session, night, completion, context);
    pthread_mutex_lock(&g_map_control_lock);
    map_session = (void *)retain_cf(g_map_control_session);
    pthread_mutex_unlock(&g_map_control_lock);
    if (map_session) {
        send_map_semantic_command(map_session, "setNightMode", NULL, night ? 1 : 0);
        release_cf(map_session);
    }
    log_capture("cluster-night-mode", night ? 1 : 0, stock_status, 0);
    return stock_status;
}

'''
        text = text[:map_end] + night_hook + text[map_end:]
        text = text.replace(
            '    send_alt_command(task->session, "showUI", ALT_MAP_URL);\n#endif',
            '    send_alt_command(task->session, "showUI", ALT_MAP_URL);\n'
            '#ifdef ALTSCREEN_RUNTIME_MAP_CONTROL\n'
            '    {\n'
            '        const char *initial_zoom = getenv("CW_INITIAL_ZOOM_OUT");\n'
            '        if (initial_zoom && initial_zoom[0] && strcmp(initial_zoom, "0") != 0) {\n'
            '            usleep(600000U);\n'
            '            send_map_semantic_command(task->session, "changeMapZoomLevel", NULL, 1);\n'
            '            log_capture("cluster-initial-zoom-out", 1, 0, 0);\n'
            '        }\n'
            '    }\n'
            '#endif\n#endif',
            1,
        )
        # The READY callback belongs to the already-running type-110 screen.
        # Remembering the session only after type 111 has been requested is a
        # circular dependency: a route start or USB reconnect then becomes the
        # accidental trigger. Arm activation when the stock main stream setup
        # succeeds, so its first READY frame requests the cluster display.
        text = text.replace(
            '#if defined(ALTSCREEN_ACTIVATE_DISPLAY) && \\\n'
            '    defined(ALTSCREEN_ACTIVATE_ON_SCREEN_READY)\n'
            '        remember_alt_session(session);\n'
            '#endif\n'
            '        log_capture("alt-passive-port-created", port, 111, 0);',
            '#if defined(ALTSCREEN_ACTIVATE_DISPLAY) && \\\n'
            '    defined(ALTSCREEN_ACTIVATE_ON_SCREEN_READY)\n'
            '        {\n'
            '            const char *auto_wake = getenv("CW_AUTO_ALT_WAKE");\n'
            '            if (!auto_wake || !auto_wake[0] || strcmp(auto_wake, "0") == 0)\n'
            '                remember_alt_session(session);\n'
            '        }\n'
            '#endif\n'
            '        log_capture("alt-passive-port-created", port, 111, 0);',
            1,
        )
        text = text.replace(
            '#ifndef ALTSCREEN_ACTIVATE_ON_SCREEN_READY\n'
            '        OSStatus schedule_status = schedule_alt_activation(session,\n'
            '                                                            1000U * 1000U);\n'
            '        log_status("alt-activation-schedule-result", session, schedule_status);\n'
            '#endif',
            '#ifdef ALTSCREEN_ACTIVATE_ON_SCREEN_READY\n'
            '        {\n'
            '            const char *auto_wake = getenv("CW_AUTO_ALT_WAKE");\n'
            '            if (auto_wake && auto_wake[0] && strcmp(auto_wake, "0") != 0) {\n'
            '                remember_alt_session(session);\n'
            '                log_status("alt-main-ready-armed", session, 0);\n'
            '            }\n'
            '        }\n'
            '#else\n'
            '        OSStatus schedule_status = schedule_alt_activation(session,\n'
            '                                                            1000U * 1000U);\n'
            '        log_status("alt-activation-schedule-result", session, schedule_status);\n'
            '#endif',
            1,
        )
        text = prefix + '\n' + text
        name = 'porsche_capture_receiver.c'
    (target / name).write_text(text, encoding='utf-8', newline='\n')
    fixture = (upstream / 'src/card-core/tests/test_scene_contract.original.c').read_text(encoding='utf-8')
    fixture = fixture[:fixture.index('#define dlsym symbol')]
    fixture = fixture.replace('static void *symbol(void *scope,const char *name)', '''static long cf_count(const void *p) { const Obj *o=p; assert(o->kind==ARRAY); return o->count; }
static const void *cf_value(const void *p,long index) { const Obj *o=p; assert(index>=0 && index<o->count); return o->items[index]; }
static void *symbol(void *scope,const char *name)''', 1)
    fixture = fixture.replace('    SYM("CFArrayAppendValue",cf_append);', '''    SYM("CFArrayAppendValue",cf_append);
    SYM("CFArrayGetCount",cf_count); SYM("CFArrayGetValueAtIndex",cf_value);''', 1)
    fixture += '#define dlsym symbol\n#include "' + name + '"\n#undef dlsym\n'
    fixture += (ROOT / 'tests/display_fixture.inc').read_text(encoding='utf-8')
    (target / ('test_capture_display.c' if args.capture_profile else 'test_display.c')).write_text(fixture, encoding='utf-8', newline='\n')
    print('Porsche ' + ('capture receiver' if args.capture_profile else 'negotiation probe') + ' source prepared')


if __name__ == '__main__':
    main()
