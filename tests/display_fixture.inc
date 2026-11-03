static void write_geometry(const char *path, unsigned stamp, int width, int active) {
    char body[256]; unsigned crc = 0xffffffffU, bit; size_t i; FILE *file;
    int n = snprintf(body, sizeof(body), "CWCP3 1 %u %d 1 1 2 %d 640 40 20 880 600 ", stamp, active, width);
    for (i = 0; i < (size_t)n; ++i) {
        crc ^= (unsigned char)body[i];
        for (bit = 0; bit < 8; ++bit) crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320U : 0);
    }
    file = fopen(path, "wb"); assert(file);
    fprintf(file, "%s%08x\n", body, crc ^ 0xffffffffU); assert(!fclose(file));
}

#ifdef CW_PORSCHE_CAPTURE
static void test_producer_ownership(void) {
    int first[2], second[2], fd; uint32_t old, current; char byte, marker[]="/tmp/cw-marker-XXXXXX";
    AltFrameRing *ring=calloc(1,sizeof(*ring)); uint8_t payload[]={1,2,3}; FILE *file; long pid=0;
    assert(ring && socketpair(AF_UNIX,SOCK_STREAM,0,first)==0);
    assert(socketpair(AF_UNIX,SOCK_STREAM,0,second)==0);
    old=cw_claim(first[0]); assert(cw_current(old));
    current=cw_claim(second[0]); assert(current!=old&&!cw_current(old));
    assert(recv(first[1],&byte,1,0)==0); /* old connection really interrupted */
    assert(!cw_accept_owner(old,first[1]));
    assert(cw_forward(old,ring,ALT_FRAME_TYPE_VIDEO,1,0,0,payload,3)==-1);
    assert(ring->write_sequence==0);
    assert(cw_forward(current,ring,ALT_FRAME_TYPE_VIDEO,1,0,0,payload,3)==1);
    fd=mkstemp(marker); assert(fd>=0); close(fd);
    assert(cw_marker(current,marker,1)==0);
    file=fopen(marker,"rb"); assert(file); assert(fscanf(file,"%ld",&pid)==1); fclose(file);
    assert(pid==(long)getpid());
    assert(cw_marker(old,marker,0)==-1 && access(marker,F_OK)==0);
    assert(cw_marker(current,marker,2)==1);
    cw_close_owner(old,first[0]); close(first[1]);
    cw_close_owner(current,second[0]); close(second[1]); free(ring);
    puts("PORSCHE_CAPTURE_OWNER_PASS reconnect shutdown, stale producer excluded, PID lease, marker isolation");
}
static void test_extensions_preserved(void) {
    Obj *result=new_obj(DICT), *existing=new_obj(ARRAY), *feature=cf_string(NULL,"stockFeature",0x08000100U);
    cf_append(existing,feature); put(result,"extendedFeatures",existing);
    drop(feature); drop(existing);
    cw_add_extended_features(result);
    existing=lookup(result,"extendedFeatures");
    assert(existing->count==3&&!strcmp(existing->items[0]->text,"stockFeature"));
    assert(!strcmp(existing->items[1]->text,"altScreen")&&!strcmp(existing->items[2]->text,"viewAreas"));
    drop(result); assert(!live);
}
#endif
int main(void) {
    char path[] = "/tmp/cw-geometry-XXXXXX";
    int fd = mkstemp(path); Obj *display, *views, *safe;
    assert(fd >= 0); close(fd);
    assert(!setenv("CONNECTWOW_PORSCHE_GEOMETRY", path, 1));
    assert(!setenv("CARPLAY_ALTSCREEN_LOG", "/dev/null", 1));
    assert(!create_alt_display()); assert(!live); /* empty file */
    write_geometry(path, (unsigned)time(NULL), 960, 1);
    display = create_alt_display(); assert(display);
    assert(number(display, "type") == 111);
    assert(number(display, "widthPixels") == 960 && number(display, "heightPixels") == 640);
    assert(number(display, "widthPhysical") == 162 && number(display, "heightPhysical") == 97);
    assert(!strcmp(string(display, "name"), "Instrument Cluster"));
    assert(!strcmp(string(display, "uid"), string(display, "uuid")));
    assert(lookup(display, "initialVideoStreams")->count == 1);
    assert(!strcmp(string(display, "initialURL"), "maps:/car/instrumentcluster/map"));
    views = lookup(display, "viewAreas"); assert(views->count == 1);
    safe = lookup(views->items[0], "safeArea");
    assert(number(safe, "originXPixels") == 40 && number(safe, "widthPixels") == 880);
    drop(display); assert(!live);
    fail_number = 1; assert(!create_alt_display()); assert(!live); fail_number = 0;
    write_geometry(path, (unsigned)time(NULL), 800, 1); /* area exceeds width */
    assert(!create_alt_display()); assert(!live);
    write_geometry(path, (unsigned)time(NULL) - 20, 960, 1);
    assert(!create_alt_display()); assert(!live);
    write_geometry(path, (unsigned)time(NULL), 960, 0);
    assert(!create_alt_display()); assert(!live);
    assert(!unlink(path));
#ifdef CW_PORSCHE_CAPTURE
    test_producer_ownership();
    test_extensions_preserved();
#endif
    puts("PORSCHE_DISPLAY_PASS actual builder: dynamic geometry, missing/stale/invalid/hidden, allocation failure, no fixed resolution");
    return 0;
}
