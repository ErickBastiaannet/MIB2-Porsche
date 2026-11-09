#include "porsche_rgi.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void be16(unsigned char *p,unsigned v){p[0]=(unsigned char)(v>>8);p[1]=(unsigned char)v;}
static size_t tlv(unsigned char *p,unsigned id,const unsigned char *v,size_t n){be16(p,(unsigned)(n+4));be16(p+2,id);if(n)memcpy(p+4,v,n);return n+4;}
static size_t message(unsigned char *p,unsigned id,const unsigned char *body,size_t n){p[0]=p[1]=0x40;be16(p+2,(unsigned)(n+6));be16(p+4,id);if(n)memcpy(p+6,body,n);return n+6;}

int main(void){
    unsigned char body[256],m[512],out[768],v[8];size_t b=0,n,z;cw_rgi_state s;memset(&s,0,sizeof(s));s.epoch=1;
    z=cw_rgi_component(out,sizeof(out),0x10);assert(z>60&&out[2]==0&&out[3]==0x1e);
    n=message(m,0x1d01,NULL,0);z=cw_rgi_patch_identify(out,sizeof(out),m,n,0x10);assert(z>n&&out[4]==0x1d&&out[5]==1);
    z=cw_rgi_start(out,sizeof(out),0x10);assert(z==24&&out[4]==0x52&&out[5]==0);
    v[0]=1;b+=tlv(body+b,1,v,1);b+=tlv(body+b,3,(const unsigned char*)"Nieuwe Erpseweg",15);b+=tlv(body+b,4,(const unsigned char*)"Uden",4);
    v[0]=0;v[1]=0;v[2]=0x30;v[3]=0x39;b+=tlv(body+b,7,v,4);
    {unsigned char t[8]={0,0,0,0,0,0,0x0e,0x10};b+=tlv(body+b,6,t,8);}
    v[0]=1;b+=tlv(body+b,0x12,v,1);v[0]=0;v[1]=0;v[2]=1;v[3]=0xf4;b+=tlv(body+b,10,v,4);v[0]=0;v[1]=0;b+=tlv(body+b,13,v,2);n=message(m,0x5201,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&s.active&&s.distance==500&&s.bargraph==127&&s.distance_remaining==12345&&s.time_remaining==3600&&s.lane_visibility==2&&strcmp(s.current_road,"Nieuwe Erpseweg")==0&&strcmp(s.destination,"Uden")==0);
    b=0;v[0]=0;v[1]=0;b+=tlv(body+b,1,v,2);b+=tlv(body+b,2,(const unsigned char*)"Sla rechtsaf",11);v[0]=1;b+=tlv(body+b,3,v,1);b+=tlv(body+b,4,(const unsigned char*)"N279",4);v[0]=0;b+=tlv(body+b,8,v,1);b+=tlv(body+b,9,v,1);n=message(m,0x5202,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&s.main_element==13&&s.direction==64&&strcmp(s.turn_to,"N279")==0);
    b=0;v[0]=0;v[1]=1;b+=tlv(body+b,1,v,2);b+=tlv(body+b,2,(const unsigned char*)"Neem afrit",10);v[0]=2;b+=tlv(body+b,3,v,1);b+=tlv(body+b,4,(const unsigned char*)"A50",3);b+=tlv(body+b,13,(const unsigned char*)"Veghel 10",9);v[0]=0;b+=tlv(body+b,8,v,1);b+=tlv(body+b,9,v,1);n=message(m,0x5202,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&strcmp(s.turn_to,"N279")==0);
    b=0;v[0]=1;b+=tlv(body+b,1,v,1);v[0]=0;v[1]=0;v[2]=0;v[3]=1;b+=tlv(body+b,13,v,4);n=message(m,0x5201,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&s.maneuver_index==1&&s.main_element==13&&s.direction==192&&strcmp(s.turn_to,"Veghel 10")==0);
    b=0;v[0]=0;v[1]=2;b+=tlv(body+b,1,v,2);v[0]=30;b+=tlv(body+b,3,v,1);v[0]=0;b+=tlv(body+b,8,v,1);v[0]=1;b+=tlv(body+b,9,v,1);v[0]=0;v[1]=45;b+=tlv(body+b,11,v,2);n=message(m,0x5202,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&s.maneuvers[2].main_element==21&&s.maneuvers[2].direction==48);
    b=0;v[0]=0;v[1]=3;b+=tlv(body+b,1,v,2);v[0]=22;b+=tlv(body+b,3,v,1);v[0]=0;b+=tlv(body+b,8,v,1);b+=tlv(body+b,9,v,1);n=message(m,0x5202,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&s.maneuvers[3].main_element==16&&s.maneuvers[3].direction==32);
    b=0;{unsigned char lane[32];size_t q=0;v[0]=0;v[1]=1;q+=tlv(lane+q,0,v,2);v[0]=2;q+=tlv(lane+q,1,v,1);v[0]=0;v[1]=0xc0;q+=tlv(lane+q,3,v,2);b+=tlv(body+b,2,lane,q);}n=message(m,0x5204,body,b);
    assert(cw_rgi_consume(&s,m,n)==1&&s.lane_count==1&&s.lanes[0].position==1&&s.lanes[0].direction==192);
    assert(cw_rgi_publish(&s,"/tmp/cw-rgi-test") == 0);assert(access("/tmp/cw-rgi-test",R_OK)==0);unlink("/tmp/cw-rgi-test");
    b=0;b+=tlv(body+b,0x13,(const unsigned char*)"Apple Maps",10);v[0]=1;b+=tlv(body+b,1,v,1);
    n=message(m,0x5201,body,b);assert(cw_rgi_consume(&s,m,n));
    s.distance=30;s.maneuvers[1].valid=1;s.lane_count=1;
    b=0;v[0]=0;v[1]=0;v[2]=3;v[3]=0x84;b+=tlv(body+b,10,v,4);
    b+=tlv(body+b,0x13,(const unsigned char*)"Google Maps",11);v[0]=1;b+=tlv(body+b,1,v,1);
    n=message(m,0x5201,body,b);assert(cw_rgi_consume(&s,m,n));
    assert(s.active&&s.distance==900&&!s.maneuvers[1].valid&&!s.lane_count&&!s.turn_to[0]);
    assert(!strcmp(s.source_name,"Google Maps"));
    b=0;v[0]=0;v[1]=0;v[2]=3;v[3]=0x20;b+=tlv(body+b,10,v,4);
    n=message(m,0x5201,body,b);assert(cw_rgi_consume(&s,m,n)&&s.distance==800&&!strcmp(s.source_name,"Google Maps"));
    b=0;v[0]=0;b+=tlv(body+b,0x14,v,1);n=message(m,0x5201,body,b);
    assert(cw_rgi_consume(&s,m,n)&&!s.active);
    puts("PORSCHE_RGI_PASS identify, subscription, cursor, street, maneuver, lanes, source switch, atomic state");return 0;
}
