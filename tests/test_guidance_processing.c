#include "porsche_rgi.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void u16(unsigned char *p,unsigned v){p[0]=(unsigned char)(v>>8);p[1]=(unsigned char)v;}
static size_t field(unsigned char *b,unsigned id,const void *v,size_t n){u16(b,(unsigned)n+4);u16(b+2,id);if(n)memcpy(b+4,v,n);return n+4;}
static int feed(cw_rgi_state *s,unsigned id,unsigned char *body,size_t n){unsigned char packet[512];packet[0]=packet[1]=0x40;u16(packet+2,(unsigned)n+6);u16(packet+4,id);memcpy(packet+6,body,n);return cw_rgi_consume(s,packet,n+6);}
int main(int argc,char **argv){
 cw_rgi_state s;unsigned char b[256],v[8];size_t n=0;memset(&s,0,sizeof(s));s.epoch=1;assert(argc==2);
 v[0]=1;n+=field(b+n,1,v,1);u16(v,77);n+=field(b+n,13,v,2);u16(v,3);n+=field(b+n,14,v,2);
 n+=field(b+n,3,"Pandelaar",9);n+=field(b+n,4,"Uden",4);
 v[0]=0;v[1]=0;v[2]=0;v[3]=20;n+=field(b+n,10,v,4);
 assert(feed(&s,0x5201,b,n));
 n=0;u16(v,77);n+=field(b+n,1,v,2);v[0]=1;n+=field(b+n,3,v,1);
 u16(v,90);u16(v+2,0);u16(v+4,65446);n+=field(b+n,10,v,6);u16(v,65446);n+=field(b+n,11,v,2);
 n+=field(b+n,4,"Vondellaan",10);n+=field(b+n,13,"Centrum",7);
 assert(feed(&s,0x5202,b,n));
 assert(s.maneuvers[0].junction_angle_count==3&&s.maneuvers[0].junction_angles[2]==-90);
 /* Odd angle vectors fail before mutating an already valid cached maneuver. */
 n=0;u16(v,77);n+=field(b+n,1,v,2);v[0]=99;n+=field(b+n,10,v,1);
 assert(!feed(&s,0x5202,b,n)&&s.maneuvers[0].junction_angle_count==3);
 /* Count-only clear withdraws the arrow, preserving a reusable payload. */
 {
  cw_rgi_state counts=s;
  n=0;u16(v,0);n+=field(b+n,14,v,2);assert(feed(&counts,0x5201,b,n));
  assert(!counts.maneuver_selected&&counts.main_element==1&&counts.maneuvers[0].valid);
  n=0;u16(v,77);n+=field(b+n,13,v,2);u16(v,3);n+=field(b+n,14,v,2);
  assert(feed(&counts,0x5201,b,n)&&counts.maneuver_selected&&counts.main_element==13);
 }
 /* Lane prefetch capacity follows the reference's 32-event bound. */
 {
  unsigned event;cw_rgi_state lanes;memset(&lanes,0,sizeof(lanes));
  lanes.lane_selected=1;lanes.lane_index=100;
  for(event=100;event<140;event++){
   unsigned char lane[32];size_t q=0;u16(v,0);q+=field(lane+q,0,v,2);u16(v,0);q+=field(lane+q,3,v,2);
   n=0;u16(v,event);n+=field(b+n,1,v,2);n+=field(b+n,2,lane,q);
   assert(feed(&lanes,0x5204,b,n));
  }
  assert(lanes.lane_count==1); /* active event survives 39 newer events */
  {unsigned occupied=0;for(event=0;event<32;event++)occupied+=lanes.lane_events[event].occupied!=0;assert(occupied==32);}
 }
 assert(cw_rgi_publish(&s,argv[1])==0);
 puts("PORSCHE_GUIDANCE_PROCESSING_PASS actual TLV cursor/junction/text to CWRG5; malformed delta preserves cache");return 0;
}
