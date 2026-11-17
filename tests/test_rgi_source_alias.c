#include "porsche_rgi.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void u16(unsigned char *p,unsigned n){p[0]=(unsigned char)(n>>8);p[1]=(unsigned char)n;}
static size_t field(unsigned char *p,unsigned id,const void *value,size_t n){u16(p,(unsigned)n+4);u16(p+2,id);memcpy(p+4,value,n);return n+4;}
static void feed(cw_rgi_state *s,unsigned id,unsigned char *body,size_t n){
    unsigned char packet[256];packet[0]=packet[1]=0x40;u16(packet+2,(unsigned)n+6);u16(packet+4,id);memcpy(packet+6,body,n);
    assert(cw_rgi_consume_at(s,packet,n+6,1000));
}
int main(void){
    const char *aliases[]={"Apple Kaarten","Apple\240Kaarten","Apple\302\240Kaarten","Apple Maps","Apple\302\240Maps"};
    unsigned i;unsigned char b[128],v[4];size_t n;cw_rgi_state s;
    memset(&s,0,sizeof(s));s.epoch=1;
    n=0;v[0]=1;n+=field(b+n,1,v,1);u16(v,77);n+=field(b+n,13,v,2);
    n+=field(b+n,0x13,aliases[0],strlen(aliases[0]));feed(&s,0x5201,b,n);
    n=0;u16(v,77);n+=field(b+n,1,v,2);v[0]=1;n+=field(b+n,3,v,1);feed(&s,0x5202,b,n);
    for(i=1;i<sizeof(aliases)/sizeof(aliases[0]);i++){
        n=field(b,0x13,aliases[i],strlen(aliases[i]));feed(&s,0x5201,b,n);
        assert(s.active&&s.maneuver_selected&&s.maneuver_index==77&&s.main_element==13&&s.direction==64);
        assert(!strcmp(s.source_name,aliases[i]));
    }
    /* Google remains a genuinely different provider; returning Apple cannot
     * resurrect Google's or the previous Apple session's cached instruction. */
    n=field(b,0x13,"Google Maps",11);feed(&s,0x5201,b,n);
    assert(!s.maneuver_selected&&!s.maneuvers[0].occupied);
    n=field(b,0x13,"Apple Maps",10);feed(&s,0x5201,b,n);
    assert(!s.maneuver_selected&&!s.maneuvers[0].occupied);
    puts("PORSCHE_SOURCE_ALIAS_PASS localized Apple labels preserve arrows; real provider switches clear");return 0;
}
