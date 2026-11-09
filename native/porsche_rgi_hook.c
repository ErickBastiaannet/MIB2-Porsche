#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <dlfcn.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "porsche_rgi.h"
/* MU1417 driver SHA256 7b9a1a6b...a8cb7. Writable dispatch tables,
 * following AU37x; executable driver text is never modified. */
typedef int (*pair_fn)(void *,void *);
typedef int (*recv_fn)(void *);
typedef void *(*pop_fn)(void *);
typedef int (*raw_fn)(void *,const void *,unsigned int);
typedef int (*blob_fn)(void *,void *,unsigned int,const void *,unsigned int);
typedef void *(*open_fn)(const char *,int);
static open_fn original_dlopen;
static pair_fn original_ident,get_data,parse_header,probe_yes,probe_no,handle_probe,handle_message,push_packet;
static recv_fn original_recv,*recv_slot;
static pop_fn pop_packet;
static raw_fn send_raw;
static blob_fn add_blob;
static pair_fn *ident_slot;
static int installed,got_guidance,identified;
static time_t last_request,last_publish;
static cw_rgi_state state;
static void log_line(const char *message) {
    int fd=open("/ramdisk/cw-porsche-rgi.log",O_WRONLY|O_CREAT|O_APPEND,0600);
    char line[240];int n;if(fd<0)return;
    n=snprintf(line,sizeof(line),"%lu %s\n",(unsigned long)time(NULL),message);
    if(n>0)write(fd,line,(size_t)n);
    close(fd);
}
static int ident_hook(void *link,void *packet) {
    unsigned char component[128];size_t n;int rc=original_ident(link,packet);
    if(rc==-1)return rc;
    n=cw_rgi_component(component,sizeof(component),0x10);
    if(!n||add_blob(link,packet,0x1e,component+4,(unsigned int)n-4)!=0){
        log_line("RGI Identify component append failed; stock retained");return rc;
    }
    got_guidance=0;identified=0;last_request=0;
    memset(&state,0,sizeof(state));
    cw_rgi_publish(&state,"/ramdisk/cw-carplay-guidance.v1");
    log_line("RGI Identify component appended through OEM builder");return rc;
}
static int inspect_packet(void *packet) {
    const unsigned char *data=*(const unsigned char **)((unsigned char *)packet+24);
    size_t size=*(uint32_t *)((unsigned char *)packet+28),i;
    if(!data||size<6||size>1024U*1024U)return 0;
    for(i=0;i+6<=size&&i<64;i++){
        size_t n;unsigned id;
        if(data[i]!=0x40||data[i+1]!=0x40)continue;
        n=(size_t)((data[i+2]<<8)|data[i+3]);
        if(n<6||i+n>size)return 0;
        id=(unsigned)((data[i+4]<<8)|data[i+5]);
        if(id==0x1d00){identified=0;got_guidance=0;last_request=0;}
        if(id==0x1d02){identified=1;log_line("iOS IdentificationAccepted");}
        if(id==0x1d03){identified=0;log_line("iOS IdentificationRejected");}
        if(id==0x5201||id==0x5202||id==0x5204){
            got_guidance=1;
            if(cw_rgi_consume(&state,data+i,n)){
                cw_rgi_publish(&state,"/ramdisk/cw-carplay-guidance.v1");
                last_publish=time(NULL);
                {
                    char detail[180];
                    snprintf(detail,sizeof(detail),"route-guidance source=%s active=%d distance=%u epoch=%llu",
                        state.source_name[0]?state.source_name:"unknown",state.active,state.distance,
                        (unsigned long long)state.epoch);
                    log_line(detail);
                }
            }
        }
        return id==0x5201||id==0x5202||id==0x5204;
    }
    return 0;
}
/* Same exported call sequence and packet ownership as MU1417
 * transport_recv_pkt; only its diagnostic print calls are omitted. */
static int receive_hook(void *link) {
    void *packet=pop_packet(link);int rc;time_t now;
    if(!packet)return -1;
    if(get_data(link,packet)!=0){push_packet(link,packet);return 0;}
    if(parse_header(link,packet)!=0){
        if(probe_yes(link,packet)!=0){
            rc=handle_probe(link,packet);
            if(rc==0)push_packet(link,packet);
            return 0;
        }
        if(probe_no(link,packet)!=0){push_packet(link,packet);return 0;}
        push_packet(link,packet);exit(0);
    }
    inspect_packet(packet);
    rc=handle_message(link,packet);
    /* AU37x ownership rule: exactly 1 transfers the packet to another
     * owner. Positive drop codes (including 2) still need recycling.
     * Never recycle rc==1 based only on message ID: that corrupts a
     * pending caller's packet. */
    if(rc!=1)push_packet(link,packet);
    now=time(NULL);
    /* iOS sends route deltas, not periodic complete snapshots. Refresh the
     * cached state only on successfully received OEM link traffic. If the
     * link stops, Java's existing freshness timeout still clears guidance. */
    if(identified&&got_guidance&&state.epoch>1&&now-last_publish>=2){
        cw_rgi_publish(&state,"/ramdisk/cw-carplay-guidance.v1");
        last_publish=now;
    }
    if(identified&&!got_guidance&&now-last_request>=2){
        unsigned char request[32];size_t n=cw_rgi_start(request,sizeof(request),0x10);
        last_request=now;
        rc=send_raw(link,request,(unsigned int)n);
        log_line(rc==0?"0x5200 route-guidance request sent":"0x5200 route-guidance request failed");
    }
    return 0;
}
static void bind_driver(void *handle) {
    unsigned char *table;void *recv;uint32_t expected;
    if(installed)return;
    table=(unsigned char *)dlsym(handle,"ident_info_funcs");
    recv=dlsym(handle,"transport_recv_pkt");
    if(!table||!recv){log_line("RGI disabled: driver tables absent");return;}
    memcpy(&expected,(unsigned char *)recv+0x24c,4);
    if(expected!=0xebffc61dU){log_line("RGI disabled: MU1417 receive fingerprint mismatch");return;}
    /* iap2_drvr is local, at verified ident_info_funcs+0xc0. */
    recv_slot=(recv_fn *)(table+0xc0+0x20);
    if((void *)*recv_slot!=recv){log_line("RGI disabled: MU1417 dispatch slot mismatch");return;}
    ident_slot=(pair_fn *)(table+23*8+4);
    original_ident=*ident_slot;original_recv=*recv_slot;
#define BIND(variable,type,name) variable=(type)dlsym(handle,name);if(!variable){log_line("RGI missing " name);return;}
    BIND(pop_packet,pop_fn,"packet_recvlist_pop")
    BIND(push_packet,pair_fn,"packet_recvlist_push")
    BIND(get_data,pair_fn,"link_get_transport_data")
    BIND(parse_header,pair_fn,"packet_parse_hdr")
    BIND(probe_yes,pair_fn,"packet_detect_probe_support")
    BIND(probe_no,pair_fn,"packet_detect_probe_nosupport")
    BIND(handle_probe,pair_fn,"link_handle_probe_support")
    BIND(handle_message,pair_fn,"link_handle_iap2pkt")
    BIND(send_raw,raw_fn,"link_send_raw_message")
    BIND(add_blob,blob_fn,"packet_addparam_blob")
#undef BIND
    if(!original_ident){log_line("RGI disabled: Identify builder absent");return;}
    *ident_slot=ident_hook;*recv_slot=receive_hook;installed=1;
    log_line("MU1417 mm-ipod route-guidance dispatch tables active");
}
void *dlopen(const char *path,int flags) {
    void *handle;const char *enabled;
    if(!original_dlopen)original_dlopen=(open_fn)dlsym(RTLD_NEXT,"dlopen");
    if(!original_dlopen)return NULL;
    handle=original_dlopen(path,flags);enabled=getenv("CW_RGI_ENABLE");
    if(handle&&path&&enabled&&strcmp(enabled,"0")&&strstr(path,"ipod-drvr-iap2.so"))bind_driver(handle);
    return handle;
}
__attribute__((constructor)) static void loaded(void) {
    memset(&state,0,sizeof(state));state.epoch=1;
    unlink("/ramdisk/cw-carplay-guidance.v1");
    log_line("Porsche MU1417 mm-ipod RGI table preload active");
}
__attribute__((destructor)) static void unloaded(void) {
    if(installed){*recv_slot=original_recv;*ident_slot=original_ident;}
    state.active=0;state.lane_count=0;++state.epoch;
    cw_rgi_publish(&state,"/ramdisk/cw-carplay-guidance.v1");
}
