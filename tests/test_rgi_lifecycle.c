#include "porsche_rgi.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void u16(unsigned char *p,unsigned v){p[0]=(unsigned char)(v>>8);p[1]=(unsigned char)v;}
static size_t field(unsigned char *p,unsigned id,const unsigned char *v,size_t n){u16(p,(unsigned)n+4);u16(p+2,id);if(n)memcpy(p+4,v,n);return n+4;}
static int feed(cw_rgi_state *s,unsigned id,const unsigned char *body,size_t n,uint64_t now){
    unsigned char packet[256];assert(n+6<=sizeof(packet));packet[0]=packet[1]=0x40;u16(packet+2,(unsigned)n+6);u16(packet+4,id);if(n)memcpy(packet+6,body,n);
    return cw_rgi_consume_at(s,packet,n+6,now);
}
static void route(cw_rgi_state *s,unsigned rs,uint64_t now){unsigned char b[8],v=(unsigned char)rs;size_t n=field(b,1,&v,1);feed(s,0x5201,b,n,now);}
static void maneuver(cw_rgi_state *s,unsigned index,uint64_t now){
    unsigned char b[32],v[2];size_t n=0;u16(v,index);n+=field(b+n,1,v,2);v[0]=2;n+=field(b+n,3,v,1);assert(feed(s,0x5202,b,n,now));
}
static void current(cw_rgi_state *s,unsigned index,uint64_t now){unsigned char b[8],v[2];u16(v,index);assert(feed(s,0x5201,b,field(b,13,v,2),now));}
static void empty(const cw_rgi_state *s,int reason){
    unsigned i;assert(!s->active&&!s->maneuver_selected&&!s->distance_valid&&!s->lane_count&&!s->distance_remaining&&!s->time_remaining);
    assert(!s->destination[0]&&!s->turn_to[0]&&s->end_reason==reason);
    for(i=0;i<64;i++)assert(!s->maneuvers[i].occupied);
    for(i=0;i<32;i++)assert(!s->lane_events[i].occupied);
}
int main(void){
    cw_rgi_state s;unsigned char b[64],v=0;size_t n;
    memset(&s,0,sizeof(s));route(&s,1,100);maneuver(&s,7,200);current(&s,7,300);
    strcpy(s.destination,"Aat");s.distance_remaining=100;s.time_remaining=50;
    route(&s,0,1000);assert(s.active&&s.zero_pending&&s.zero_deadline_ms==1800);
    route(&s,0,1500);assert(s.zero_deadline_ms==1800);assert(!cw_rgi_tick(&s,1799));
    assert(cw_rgi_tick(&s,1800));empty(&s,CW_RGI_END_STOP);
    maneuver(&s,7,1900);assert(!s.active&&s.end_reason==CW_RGI_END_STOP);
    route(&s,1,2000);assert(s.active&&!s.maneuver_selected);current(&s,7,2100);assert(s.main_element==1);
    maneuver(&s,7,2200);assert(s.main_element==13);
    route(&s,5,3000);route(&s,0,3100);assert(s.zero_pending&&!s.zero_deadline_ms);
    assert(!cw_rgi_tick(&s,1000000)&&s.active);
    assert(!feed(&s,0x5202,NULL,0,1000010)&&s.zero_pending);
    maneuver(&s,8,1000020);assert(s.active&&!s.zero_pending&&!s.maneuver_selected);
    current(&s,8,1000030);assert(s.main_element==13);
    /* Normal reset with valid follow-up must not stop or reuse the old ID. */
    route(&s,0,1001000);route(&s,1,1001100);assert(!s.zero_pending&&s.active);
    current(&s,8,1001200);assert(s.main_element==1);
    /* Explicit reached state is not inferred merely from an arrival payload. */
    route(&s,2,2000000);assert(s.active&&s.main_element==3&&s.arrival_deadline_ms==2005000);
    route(&s,2,2001000);assert(s.arrival_deadline_ms==2005000);
    route(&s,0,2001100);assert(!cw_rgi_tick(&s,2004999));
    assert(cw_rgi_tick(&s,2005000));empty(&s,CW_RGI_END_ARRIVAL);
    route(&s,2,2006000);empty(&s,CW_RGI_END_ARRIVAL);
    route(&s,1,2007000);assert(s.active&&s.end_reason==0);
    route(&s,2,2007100);cw_rgi_end(&s,CW_RGI_END_DISCONNECT);empty(&s,CW_RGI_END_DISCONNECT);
    assert(!cw_rgi_tick(&s,9000000));
    /* App switch cancels an old arrival deadline and drops its descriptors. */
    route(&s,1,9000010);
    n=field(b,0x13,(const unsigned char*)"Apple Maps",10);assert(feed(&s,0x5201,b,n,9000011));
    route(&s,2,9000012);
    n=field(b,0x13,(const unsigned char*)"Google Maps",11);v=1;n+=field(b+n,1,&v,1);
    assert(feed(&s,0x5201,b,n,9000013)&&s.active&&!s.arrival_deadline_ms&&!s.maneuver_selected);
    assert(!cw_rgi_tick(&s,9006000));
    /* Source unsupported is a hard clear, regardless of reroute grace. */
    route(&s,1,9006100);route(&s,5,9006200);route(&s,0,9006300);
    v=0;n=field(b,0x14,&v,1);assert(feed(&s,0x5201,b,n,9006400));empty(&s,CW_RGI_END_STOP);
    puts("PORSCHE_RGI_LIFECYCLE_PASS stop, reroute, arrival, hard clear, disconnect, no resurrection");return 0;
}
