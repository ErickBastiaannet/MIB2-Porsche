#include "porsche_rgi.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static uint16_t be16(const uint8_t *p) { return (uint16_t)((p[0] << 8) | p[1]); }
static uint32_t be32(const uint8_t *p) { return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3]; }
static uint64_t be64(const uint8_t *p) { return ((uint64_t)be32(p) << 32) | be32(p + 4); }
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)(v>>8); p[1]=(uint8_t)v; }

static int text_copy(char *out,size_t cap,const uint8_t *in,size_t n) {
    size_t i,used=0;
    if(!out||cap<2)return 0;
    for(i=0;i<n&&used+1<cap;i++) if(in[i]>=0x20 && in[i]!=0x7f) out[used++]=(char)in[i];
    while(used&&out[used-1]==' ')--used;
    out[used]=0;
    return 1;
}

/* Bounded slots carry the full uint16 iAP2 identity, as in the reference.
 * A long route does not stop working at maneuver ID 64. */
static cw_rgi_maneuver *maneuver_slot(cw_rgi_state *s,unsigned index,int create) {
    unsigned i,slot=64;uint64_t oldest=~(uint64_t)0;
    for(i=0;i<64;i++)if(s->maneuvers[i].occupied&&s->maneuvers[i].wire_id==index)return &s->maneuvers[i];
    if(!create)return NULL;
    if(index<64&&!s->maneuvers[index].occupied)slot=index;
    else for(i=0;i<64;i++) {
        cw_rgi_maneuver *m=&s->maneuvers[i];
        if(!m->occupied){slot=i;break;}
        if(s->maneuver_selected&&m->wire_id==s->maneuver_index)continue;
        if(m->touched<oldest){oldest=m->touched;slot=i;}
    }
    if(slot==64)return NULL;
    memset(&s->maneuvers[slot],0,sizeof(s->maneuvers[slot]));
    s->maneuvers[slot].occupied=1;s->maneuvers[slot].wire_id=(uint16_t)index;
    s->maneuvers[slot].angle=1000;
    return &s->maneuvers[slot];
}

static void select_maneuver(cw_rgi_state *s,unsigned index) {
    cw_rgi_maneuver *m;
    /* Do not keep an obsolete arrow or promote a cached future maneuver
     * when the authoritative first entry has not arrived yet. */
    s->maneuver_index=(uint16_t)index;
    s->maneuver_selected=1;
    s->main_element=1;s->direction=0;s->z_level=0;s->turn_to[0]=0;
    m=maneuver_slot(s,index,1);
    if(!m||!m->valid)return;
    s->main_element=m->main_element;s->direction=m->direction;s->z_level=m->z_level;
    if(m->exit_info[0]) { strncpy(s->turn_to,m->exit_info,sizeof(s->turn_to)-1);s->turn_to[sizeof(s->turn_to)-1]=0; }
    else if(m->after_road[0]) { strncpy(s->turn_to,m->after_road,sizeof(s->turn_to)-1);s->turn_to[sizeof(s->turn_to)-1]=0; }
    else { strncpy(s->turn_to,m->description,sizeof(s->turn_to)-1);s->turn_to[sizeof(s->turn_to)-1]=0; }
}

static void select_lanes(cw_rgi_state *s) {
    unsigned i;uint16_t index=s->lane_index;int selected=s->lane_selected;
    cw_rgi_maneuver *m=s->maneuver_selected?maneuver_slot(s,s->maneuver_index,0):NULL;
    if(!selected&&m&&m->linked_lane_known){index=m->linked_lane;selected=1;}
    s->lane_count=0;
    if(!selected)return;
    for(i=0;i<32;i++)if(s->lane_events[i].occupied&&s->lane_events[i].wire_id==index&&s->lane_events[i].valid){
        s->lane_count=s->lane_events[i].count;
        memcpy(s->lanes,s->lane_events[i].lanes,sizeof(s->lanes));return;
    }
}

static uint32_t crc32_bytes(const uint8_t *p, size_t n) {
    uint32_t c=0xffffffffU; size_t i; int b;
    for (i=0;i<n;i++) { c^=p[i]; for (b=0;b<8;b++) c=(c>>1)^((0U-(c&1U))&0xedb88320U); }
    return c^0xffffffffU;
}

static int valid(const uint8_t *m,size_t n,uint16_t id) {
    size_t o=6;
    if (!m || n<6 || m[0]!=0x40 || m[1]!=0x40 || be16(m+2)!=n || be16(m+4)!=id) return 0;
    while (o<n) { uint16_t z; if (n-o<4) return 0; z=be16(m+o); if (z<4 || z>n-o) return 0; o+=z; }
    return o==n;
}

static int tlv_next(const uint8_t *m,size_t n,size_t *o,uint16_t *id,const uint8_t **v,size_t *vn) {
    uint16_t z; if (*o+4>n) return 0; z=be16(m+*o); if (z<4 || *o+z>n) return 0;
    *id=be16(m+*o+2); *v=m+*o+4; *vn=z-4; *o+=z; return 1;
}

static void map_maneuver(unsigned type,int angle,unsigned junction,unsigned driving,uint8_t *main,uint8_t *dir) {
    int directional=angle!=0&&angle!=1000&&angle!=-1000;
    *main=1; *dir=0;
    if (type==0 || type==5 || type==15 || type==17) { *main=11; return; }
    if (type==10 || type==12 || type==27) { *main=3;return; }
    if (type==52 || type==53) { *main=12; *dir=(type==52)?64:192; return; }
    if (type==11 || type==16 || type==51) {
        int a=angle<0?-angle:angle;
        *main=13;
        if(!directional||a<=22)*dir=0;
        else if(a>180)*dir=angle<0?64:192;
        else if(a<=67)*dir=angle<0?32:224;
        else if(a<=112)*dir=angle<0?64:192;
        else *dir=angle<0?96:160;
        return;
    }
    if (type==19) { *main=driving?22:21; *dir=128; return; }
    if (type==6) { *main=13; *dir=driving?64:192; return; }
    if (junction==1 && (type==7 || (type>=28 && type<=46))) {
        *main=(type==7)?(driving?27:26):(driving?22:21);
        if (type>=28 && type<=46) {
            /* Reference ManeuverMapper.directionFromAngle16: geometry, not
             * exit ordinal (exit 3 does not imply 67.5 degrees). */
            static const uint8_t bins[17]={128,112,96,80,64,48,32,16,0,240,224,208,192,176,160,144,128};
            int a=angle<-180?-180:(angle>180?180:angle);
            unsigned bin=(unsigned)((a+180)*2+22)/45;
            *dir=(angle==1000||angle==-1000)?0:bins[bin];
        } else *dir=driving?64:192;
        return;
    }
    if (junction!=0) return;
    switch(type) {
    case 4: case 18: case 26: *main=25; *dir=directional?(angle<0?64:192):(driving?192:64);break;
    case 1: *main=13; *dir=64; break; case 2: *main=13; *dir=192; break;
    case 3: *main=13; *dir=0; break;
    case 13: case 49: *main=13; *dir=32; break; case 14: case 50: *main=13; *dir=224; break;
    case 47: *main=13; *dir=96; break; case 48: *main=13; *dir=160; break;
    case 8: case 9: *main=13; *dir=(directional?angle<0:driving!=0)?32:224; break;
    case 20: *main=13; *dir=directional&&angle>=-180&&angle<0?(angle<-112?96:(angle>=-67?32:64)):64; break;
    case 21: *main=13; *dir=directional&&angle<=180&&angle>0?(angle>112?160:(angle<=67?224:192)):192; break;
    case 22: *main=13; *dir=32; break; case 23: *main=13; *dir=224; break;
    case 24: *main=3;*dir=64;break;case 25: *main=3;*dir=192;break;
    default: break;
    }
}

/* The same Apple app publishes localized and English labels in one session.
 * A display label is not an app switch. Keep this alias list deliberately
 * narrow: unrelated providers must still invalidate the previous route. */
static int apple_maps_source(const char *name) {
    return !strcmp(name,"Apple Maps") || !strcmp(name,"Apple Kaarten")
        || !strcmp(name,"Apple\240Kaarten") || !strcmp(name,"Apple\302\240Kaarten")
        || !strcmp(name,"Apple\240Maps") || !strcmp(name,"Apple\302\240Maps");
}

static int same_guidance_source(const char *a,const char *b) {
    return !strcmp(a,b) || (apple_maps_source(a)&&apple_maps_source(b));
}

static int parse_update(cw_rgi_state *s,const uint8_t *m,size_t n) {
    size_t o=6,vn; uint16_t id; const uint8_t *v; int changed=0;
    /* The list is a sequence of uint16 IDs, not a count followed by IDs.
     * Reject malformed lists before changing any part of the snapshot. */
    while (tlv_next(m,n,&o,&id,&v,&vn)) if(id==13 && (vn&1U))return 0;
    o=6;
    /* iOS supplies one selected guidance source. Source name can follow the
     * distance TLV, so invalidate the previous source before applying deltas. */
    while (tlv_next(m,n,&o,&id,&v,&vn)) if(id==0x13) {
        char source[97]={0};text_copy(source,sizeof(source),v,vn);
        if(strcmp(source,s->source_name)) {
            uint64_t epoch=s->epoch;
            /* First source label may follow the route's prefetched payloads.
             * Only an actual source switch invalidates those payloads. */
            if(s->source_name[0]&&!same_guidance_source(source,s->source_name)){
                memset(s,0,sizeof(*s));s->epoch=epoch;
            }
            memcpy(s->source_name,source,sizeof(source));changed=1;
        }
    }
    o=6;
    /* Reference RouteGuidance.parse processes count before list regardless
     * of wire order. Count zero withdraws selection, not cached payloads. */
    while(tlv_next(m,n,&o,&id,&v,&vn))if(id==14&&vn>=2&&be16(v)==0&&(!s->maneuver_count_known||s->maneuver_count!=0)){
        s->maneuver_selected=0;s->main_element=1;s->direction=0;s->z_level=0;s->turn_to[0]=0;
        s->distance=0;s->distance_valid=0;
    }
    o=6;
    /* Distance belongs to the primary instruction, not to its successor.
     * Invalidate before parsing so TLV ordering cannot erase a new distance. */
    while (tlv_next(m,n,&o,&id,&v,&vn)) if(id==13) {
        if(!vn||!s->maneuver_selected||be16(v)!=s->maneuver_index){s->distance_valid=0;s->distance=0;}
    }
    o=6;
    while (tlv_next(m,n,&o,&id,&v,&vn)) {
        if (id==1 && vn>=1) {
            s->route_state=v[0];s->active=v[0]!=0;
            changed=1;
        }
        else if (id==3) { text_copy(s->current_road,sizeof(s->current_road),v,vn); changed=1; }
        else if (id==4) { text_copy(s->destination,sizeof(s->destination),v,vn); changed=1; }
        else if (id==2 && vn>=1) { s->maneuver_state=v[0]; changed=1; }
        else if (id==5 && vn>=8) { s->eta=be64(v);s->eta_valid=1; changed=1; }
        else if (id==14 && vn>=2) { s->maneuver_count=be16(v);s->maneuver_count_known=1; changed=1; }
        else if (id==6 && vn>=8) { s->time_remaining=be64(v);s->time_remaining_at=(uint64_t)time(NULL); changed=1; }
        else if (id==7 && vn>=4) { s->distance_remaining=be32(v); changed=1; }
        else if (id==10 && vn>=4) { s->distance=be32(v);s->distance_valid=1; changed=1; }
        else if (id==13) {
            /* Reference rgd_tlv.c + rgd_hook.c: entry zero is authoritative;
             * later entries are prefetched instructions, never a clock. */
            if(vn)select_maneuver(s,be16(v));
            else {
                s->maneuver_selected=0;s->main_element=1;
                s->direction=0;s->z_level=0;s->turn_to[0]=0;
            }
            changed=1;
        }
        else if (id==0x12 && vn>=1) { s->lane_visibility=v[0]?2:1; changed=1; }
        else if (id==0x10 && vn>=2) { s->lane_index=be16(v);s->lane_selected=1;changed=1; }
        else if (id==0x0f && vn>=1) { s->visible_in_app=v[0]; changed=1; }
        else if (id==0x14 && vn>=1) { s->source_support_known=1;s->source_supports_rg=v[0]!=0;changed=1; }
    }
    if(s->source_support_known&&!s->source_supports_rg){s->active=0;s->lane_visibility=1;}
    select_lanes(s);
    return changed;
}

static int parse_maneuver(cw_rgi_state *s,const uint8_t *m,size_t n) {
    size_t o=6,vn;uint16_t id;const uint8_t *v;unsigned index=0;int has_index=0;
    cw_rgi_maneuver *item;
    while(tlv_next(m,n,&o,&id,&v,&vn))if(id==1&&vn>=2){index=be16(v);has_index=1;}
    if(!has_index)return 0;
    o=6;
    while(tlv_next(m,n,&o,&id,&v,&vn))if(id==10&&((vn&1U)||vn>32))return 0;
    item=maneuver_slot(s,index,1);if(!item)return 0;
    item->touched=++s->cache_clock;o=6;
    /* 0x5202 is a delta: omitted fields retain their existing value. */
    while(tlv_next(m,n,&o,&id,&v,&vn)){
        if(id==2)text_copy(item->description,sizeof(item->description),v,vn);
        else if(id==3&&vn>=1){item->type=v[0];item->valid=v[0]<=53;}
        else if(id==4)text_copy(item->after_road,sizeof(item->after_road),v,vn);
        else if(id==5&&vn>=4)item->step_distance=be32(v);
        else if(id==8&&vn>=1)item->driving=v[0];
        else if(id==9&&vn>=1)item->junction=v[0];
        else if(id==10){size_t a;item->junction_angle_count=(uint8_t)(vn/2);for(a=0;a<vn/2;a++)item->junction_angles[a]=(int16_t)be16(v+2*a);}
        else if(id==11&&vn>=2)item->angle=(int16_t)be16(v);
        else if(id==12&&vn>=2){item->linked_lane=be16(v);item->linked_lane_known=1;}
        else if(id==13)text_copy(item->exit_info,sizeof(item->exit_info),v,vn);
    }
    if(item->valid)map_maneuver(item->type,item->angle,item->junction,item->driving,
                               &item->main_element,&item->direction);
    if(s->maneuver_selected&&index==s->maneuver_index)select_maneuver(s,index);
    select_lanes(s);
    return 1;
}

static int parse_lanes(cw_rgi_state *s,const uint8_t *m,size_t n) {
    size_t o=6,vn;uint16_t id,index=0;const uint8_t *v;
    unsigned count=0,i,slot=32;int has_index=0,has_lanes=0;uint64_t oldest=~(uint64_t)0;
    cw_rgi_lane lanes[12];
    while(tlv_next(m,n,&o,&id,&v,&vn))if(id==1&&vn>=2){index=be16(v);has_index=1;}
    if(!has_index)return 0;
    memset(lanes,0,sizeof(lanes));o=6;
    while(tlv_next(m,n,&o,&id,&v,&vn))if(id==2){
        size_t p=0;cw_rgi_lane lane;memset(&lane,0,sizeof(lane));lane.direction=1000;has_lanes=1;
        while(p+4<=vn){
            uint16_t z=be16(v+p),sid=be16(v+p+2);const uint8_t *sv=v+p+4;size_t sn;
            if(z<4||p+z>vn)return 0;
            sn=z-4;
            if(sid==0&&sn>=2)lane.position=be16(sv);
            else if(sid==1&&sn>=1)lane.guidance=sv[0];
            else if(sid==2){
                size_t a;if((sn&1U)||sn/2+lane.angle_count>16)return 0;
                for(a=0;a<sn;a+=2)lane.angles[lane.angle_count++]=be16(sv+a);
            }
            else if(sid==3&&sn>=2)lane.direction=be16(sv);
            p+=z;
        }
        if(p!=vn)return 0;
        if(count>=12)return 0;
        lanes[count++]=lane;
    }
    if(!has_lanes)return 0;
    for(i=0;i<32;i++)if(s->lane_events[i].occupied&&s->lane_events[i].wire_id==index){slot=i;break;}
    if(slot==32)for(i=0;i<32;i++){
        cw_rgi_lane_event *event=&s->lane_events[i];
        if(!event->occupied){slot=i;break;}
        if(s->lane_selected&&event->wire_id==s->lane_index)continue;
        if(event->touched<oldest){oldest=event->touched;slot=i;}
    }
    if(slot==32)return 0;
    s->lane_events[slot].occupied=s->lane_events[slot].valid=1;
    s->lane_events[slot].wire_id=index;s->lane_events[slot].touched=++s->cache_clock;
    s->lane_events[slot].count=(uint8_t)count;
    memcpy(s->lane_events[slot].lanes,lanes,sizeof(lanes));
    select_lanes(s);return 1;
}

uint64_t cw_rgi_now_ms(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)!=0)return 0;
    return (uint64_t)t.tv_sec*1000U+(uint64_t)t.tv_nsec/1000000U;
}

void cw_rgi_end(cw_rgi_state *s,int reason) {
    uint64_t epoch=s->epoch+1;
    memset(s,0,sizeof(*s));s->epoch=epoch;s->end_reason=(uint8_t)reason;
}

int cw_rgi_tick(cw_rgi_state *s,uint64_t now) {
    if(s->arrival_deadline_ms&&now>=s->arrival_deadline_ms){cw_rgi_end(s,CW_RGI_END_ARRIVAL);return 1;}
    if(s->zero_pending&&s->zero_deadline_ms&&now>=s->zero_deadline_ms){cw_rgi_end(s,CW_RGI_END_STOP);return 1;}
    return 0;
}

int cw_rgi_consume_at(cw_rgi_state *s,const uint8_t *m,size_t n,uint64_t now) {
    uint16_t id; int changed=0; if (!s || !m || n<6) return 0; id=be16(m+4);
    if (!valid(m,n,id)) return 0;
    if(id==0x5201){
        size_t o=6,vn;uint16_t field;const uint8_t *v;int rs=-1,hard=0,evidence=0;
        while(tlv_next(m,n,&o,&field,&v,&vn)){
            if(field==13&&(vn&1U))return 0;
            if(field==1&&vn){if(v[0]>6)return 0;rs=v[0];if(rs>0)evidence=1;}
            if(field==0x14&&vn&&!v[0])hard=1;
            if((field==13&&vn>=2)||(field==14&&vn>=2&&be16(v)>0)
                ||((field==7||field==10)&&vn>=4&&be32(v)>0)
                ||((field==3||field==4)&&vn&&v[0]))evidence=1;
        }
        if(hard){cw_rgi_end(s,CW_RGI_END_STOP);return 1;}
        if(rs==2&&s->end_reason==CW_RGI_END_ARRIVAL)return 0;
        if(rs>0&&rs!=2&&s->route_state==2){
            uint64_t epoch=s->epoch;char source[97];memcpy(source,s->source_name,sizeof(source));
            memset(s,0,sizeof(*s));s->epoch=epoch;memcpy(s->source_name,source,sizeof(source));
        }
        if(rs>0&&!s->active&&s->end_reason){
            uint64_t epoch=s->epoch;char source[97];memcpy(source,s->source_name,sizeof(source));
            memset(s,0,sizeof(*s));s->epoch=epoch;memcpy(s->source_name,source,sizeof(source));
        }
        if(rs==0&&s->active){
            /* LuKa rgd_hook.c: 800ms normal zero grace; no timeout for
             * a reset following REROUTING. Repeated zeros never extend it. */
            if(!s->zero_pending){s->zero_pending=1;s->zero_deadline_ms=(s->route_state==5||s->route_state==2)?0:now+800;++s->epoch;return 1;}
            return 0;
        }
        if(s->zero_pending&&evidence){
            /* New route generation; do not reuse the old route's ID zero. */
            char source[97];uint64_t epoch=s->epoch;
            memcpy(source,s->source_name,sizeof(source));
            memset(s,0,sizeof(*s));s->epoch=epoch;s->active=1;s->route_state=1;
            memcpy(s->source_name,source,sizeof(source));
        } else if(s->zero_pending)return 0;
        if(rs==0){cw_rgi_end(s,CW_RGI_END_STOP);return 1;}
    } else if((id==0x5202||id==0x5204)&&s->zero_pending){
        /* Reference: valid maneuver/lane evidence cancels a transient zero.
         * Validate/consume first below; malformed packets cannot cancel it. */
        cw_rgi_state *next=(cw_rgi_state *)calloc(1,sizeof(*next));
        if(!next)return 0;
        changed=id==0x5202?parse_maneuver(next,m,n):parse_lanes(next,m,n);
        if(!changed){free(next);return 0;}
        next->epoch=s->epoch+1;next->route_state=1;next->active=1;
        memcpy(next->source_name,s->source_name,sizeof(next->source_name));
        memcpy(s,next,sizeof(*s));free(next);return 1;
    }
    if (id==0x5201) changed=parse_update(s,m,n);
    else if (id==0x5202) changed=parse_maneuver(s,m,n);
    else if (id==0x5203) {cw_rgi_end(s,CW_RGI_END_STOP);return 1;}
    else if (id==0x5204) changed=parse_lanes(s,m,n);
    if(changed){
        if(s->active)s->end_reason=CW_RGI_END_NONE;
        if(s->route_state==2){
            /* Explicit iOS ARRIVED. Fifthbro uses a non-blocking 5s hold;
             * repeated arrival updates must not restart the deadline. */
            if(!s->arrival_deadline_ms)s->arrival_deadline_ms=now+5000;
            s->main_element=3;s->direction=0;s->lane_count=0;s->lane_visibility=1;
            s->distance=0;s->distance_valid=0;s->distance_remaining=0;s->time_remaining=0;
        }else s->arrival_deadline_ms=0;
        ++s->epoch;
    }
    return changed;
}

int cw_rgi_consume(cw_rgi_state *s,const uint8_t *m,size_t n) {
    return cw_rgi_consume_at(s,m,n,cw_rgi_now_ms());
}

static size_t add16(uint8_t *p,size_t cap,uint16_t id,uint16_t value) { if(cap<6)return 0;put16(p,6);put16(p+2,id);put16(p+4,value);return 6; }
static size_t add0(uint8_t *p,size_t cap,uint16_t id) { if(cap<4)return 0;put16(p,4);put16(p+2,id);return 4; }

size_t cw_rgi_component(uint8_t *o,size_t cap,uint16_t cid) {
    const char name[]="ConnectWow Route Guidance"; size_t p=4,nl=sizeof(name); unsigned id;
    if (!o || cap<4+6+4+nl+7*6) return 0;
    put16(o+2,0x001e);
    p+=add16(o+p,cap-p,0,cid); put16(o+p,(uint16_t)(4+nl));put16(o+p+2,1);memcpy(o+p+4,name,nl);p+=4+nl;
    for(id=2;id<=8;id++) p+=add16(o+p,cap-p,(uint16_t)id,(id==6||id==8)?6:256);
    put16(o,(uint16_t)p); return p;
}

size_t cw_rgi_patch_identify(uint8_t *o,size_t cap,const uint8_t *m,size_t n,uint16_t cid) {
    uint8_t component[128]; size_t cn,off=6,out=6; if(!valid(m,n,0x1d01)||cap<n)return 0;
    memcpy(o,m,6); cn=cw_rgi_component(component,sizeof(component),cid); if(!cn)return 0;
    while(off<n){uint16_t z=be16(m+off),id=be16(m+off+2);if(id!=0x001e){if(out+z>cap)return 0;memcpy(o+out,m+off,z);out+=z;}off+=z;}
    if(out+cn>cap)return 0;
    memcpy(o+out,component,cn);out+=cn;put16(o+2,(uint16_t)out);return out;
}

size_t cw_rgi_start(uint8_t *o,size_t cap,uint16_t cid) {
    size_t p=6;if(cap<24)return 0;o[0]=o[1]=0x40;put16(o+4,0x5200);p+=add16(o+p,cap-p,0,cid);p+=add0(o+p,cap-p,1);p+=add0(o+p,cap-p,2);p+=add0(o+p,cap-p,3);put16(o+2,(uint16_t)p);return p;
}

int cw_rgi_publish(const cw_rgi_state *s,const char *path) {
    char body[4096],tmp[256],file[256]; size_t used; unsigned i; int fd; uint32_t crc; time_t now=time(NULL);
    const cw_rgi_maneuver *current=NULL;
    if(!s||!path||strlen(path)>230)return -1;
    for(i=0;i<64;i++)if(s->maneuver_selected&&s->maneuvers[i].occupied&&s->maneuvers[i].wire_id==s->maneuver_index&&s->maneuvers[i].valid){current=&s->maneuvers[i];break;}
    used=(size_t)snprintf(body,sizeof(body),"CWRG5 %llu %llu %d %u %u %u %u %d %u %u %llu %u %d %u %u %d %u %u",
        (unsigned long long)s->epoch,(unsigned long long)now,s->active,s->distance,s->bargraph,s->main_element,s->direction,s->z_level,s->lane_count,
        s->distance_remaining,(unsigned long long)s->time_remaining,s->lane_visibility,
        current?(int)current->type:-1,current?current->step_distance:0,s->distance_valid,s->maneuver_selected?(int)s->maneuver_index:-1,s->route_state,s->end_reason);
    {
        struct timespec realtime;
        uint64_t mono=cw_rgi_now_ms(),wall=(uint64_t)now*1000U,stop=0,arrival=0;
        if(clock_gettime(CLOCK_REALTIME,&realtime)==0)wall=(uint64_t)realtime.tv_sec*1000U+(uint64_t)realtime.tv_nsec/1000000U;
        if(s->zero_deadline_ms)stop=wall+(s->zero_deadline_ms>mono?s->zero_deadline_ms-mono:0);
        if(s->arrival_deadline_ms)arrival=wall+(s->arrival_deadline_ms>mono?s->arrival_deadline_ms-mono:0);
        used+=(size_t)snprintf(body+used,sizeof(body)-used," %llu %u %u %u %u %u %llu %llu %u %u %d %llu ",
            (unsigned long long)s->eta,s->eta_valid,s->maneuver_state,s->maneuver_count_known,s->maneuver_count,s->zero_pending,
            (unsigned long long)stop,(unsigned long long)arrival,current?current->junction:0,current?current->driving:0,current?current->angle:1000,(unsigned long long)s->time_remaining_at);
        if(!current||!current->junction_angle_count)body[used++]='-';
        else {unsigned a;for(a=0;a<current->junction_angle_count;a++)used+=(size_t)snprintf(body+used,sizeof(body)-used,"%04x",(uint16_t)current->junction_angles[a]);}
    }
    for(i=0;i<s->lane_count&&used<sizeof(body);i++){
        unsigned a;const cw_rgi_lane *l=&s->lanes[i];
        used+=(size_t)snprintf(body+used,sizeof(body)-used," %u,%u,%u,%u,%u,%u,%u;",l->position,l->direction,l->type,l->marking_left,l->marking_right,l->description,l->guidance);
        for(a=0;a<l->angle_count&&used+5<sizeof(body);a++)used+=(size_t)snprintf(body+used,sizeof(body)-used,"%04x",l->angles[a]);
    }
    used+=(size_t)snprintf(body+used,sizeof(body)-used," ");
    if(!s->current_road[0]) used+=(size_t)snprintf(body+used,sizeof(body)-used,"-");
    else for(i=0;s->current_road[i]&&used+2<sizeof(body);i++) used+=(size_t)snprintf(body+used,sizeof(body)-used,"%02x",(unsigned char)s->current_road[i]);
    used+=(size_t)snprintf(body+used,sizeof(body)-used," ");
    if(!s->turn_to[0]) used+=(size_t)snprintf(body+used,sizeof(body)-used,"-");
    else for(i=0;s->turn_to[i]&&used+2<sizeof(body);i++) used+=(size_t)snprintf(body+used,sizeof(body)-used,"%02x",(unsigned char)s->turn_to[i]);
    used+=(size_t)snprintf(body+used,sizeof(body)-used," ");
    if(!s->destination[0]) used+=(size_t)snprintf(body+used,sizeof(body)-used,"-");
    else for(i=0;s->destination[i]&&used+2<sizeof(body);i++) used+=(size_t)snprintf(body+used,sizeof(body)-used,"%02x",(unsigned char)s->destination[i]);
    {
        const char *labels[2]={current?current->after_road:"",current?current->exit_info:""};
        unsigned label;
        for(label=0;label<2;label++){
            body[used++]=' ';
            if(!labels[label][0])body[used++]='-';
            else for(i=0;labels[label][i]&&used+2<sizeof(body);i++)used+=(size_t)snprintf(body+used,sizeof(body)-used,"%02x",(unsigned char)labels[label][i]);
        }
    }
    if(used+11>=sizeof(body))return -1;
    body[used++]=' ';crc=crc32_bytes((const uint8_t*)body,used);used+=(size_t)snprintf(body+used,sizeof(body)-used,"%08x\n",crc);
    snprintf(file,sizeof(file),"%s.tmp",path);fd=open(file,O_WRONLY|O_CREAT|O_TRUNC,0600);if(fd<0)return -1;
    if(write(fd,body,used)!=(ssize_t)used){close(fd);unlink(file);return -1;}close(fd);if(rename(file,path)!=0){unlink(file);return -1;} (void)tmp; return 0;
}
