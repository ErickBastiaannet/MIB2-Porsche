#include "porsche_rgi.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static uint16_t be16(const uint8_t *p) { return (uint16_t)((p[0] << 8) | p[1]); }
static uint32_t be32(const uint8_t *p) { return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3]; }
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)(v>>8); p[1]=(uint8_t)v; }

static int text_copy(char *out,size_t cap,const uint8_t *in,size_t n) {
    size_t i,used=0;
    if(!out||cap<2)return 0;
    for(i=0;i<n&&used+1<cap;i++) if(in[i]>=0x20 && in[i]!=0x7f) out[used++]=(char)in[i];
    while(used&&out[used-1]==' ')--used;
    out[used]=0;
    return 1;
}

static void select_maneuver(cw_rgi_state *s,unsigned index) {
    cw_rgi_maneuver *m;
    if(index>=64)return;
    s->maneuver_index=(uint16_t)index; m=&s->maneuvers[index];
    if(!m->valid)return;
    s->main_element=m->main_element;s->direction=m->direction;s->z_level=m->z_level;
    if(m->exit_info[0]) { strncpy(s->turn_to,m->exit_info,sizeof(s->turn_to)-1);s->turn_to[sizeof(s->turn_to)-1]=0; }
    else if(m->after_road[0]) { strncpy(s->turn_to,m->after_road,sizeof(s->turn_to)-1);s->turn_to[sizeof(s->turn_to)-1]=0; }
    else { strncpy(s->turn_to,m->description,sizeof(s->turn_to)-1);s->turn_to[sizeof(s->turn_to)-1]=0; }
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
    *main=1; *dir=0;
    if (type==0 || type==5 || type==15 || type==17) { *main=11; return; }
    if (type==10 || type==12 || type==27) { *main=3; return; }
    if (type==52 || type==53) { *main=12; *dir=(type==52)?64:192; return; }
    if (type==4 || type==18 || type==26) { *main=25; *dir=driving?192:64; return; }
    if (type==19) { *main=driving?22:21; *dir=128; return; }
    if (type==6) { *main=13; *dir=driving?64:192; return; }
    if (junction==1 && (type==7 || (type>=28 && type<=46))) {
        *main=(type==7)?(driving?27:26):(driving?22:21);
        if (type>=28 && type<=46) *dir=(uint8_t)(((type-27)*16)&255); else *dir=driving?64:192;
        return;
    }
    if (junction!=0) return;
    switch(type) {
    case 1: *main=13; *dir=64; break; case 2: *main=13; *dir=192; break;
    case 3: *main=13; *dir=0; break;
    case 13: case 49: *main=13; *dir=32; break; case 14: case 50: *main=13; *dir=224; break;
    case 47: *main=13; *dir=96; break; case 48: *main=13; *dir=160; break;
    case 8: *main=driving?16:15; *dir=driving?32:224; break;
    case 9: *main=13; *dir=(driving && angle>179)?32:224; break;
    case 20: *main=13; *dir=(angle<-112)?96:(angle<0?32:64); break;
    case 21: *main=13; *dir=(angle>112)?160:(angle>0?224:192); break;
    case 22: *main=16; *dir=32; break; case 23: *main=15; *dir=224; break;
    case 24: *main=3; *dir=64; break; case 25: *main=3; *dir=192; break;
    case 11: case 16: case 51: *main=13; *dir=angle<0?64:(angle>0?192:0); break;
    default: break;
    }
}

static int parse_update(cw_rgi_state *s,const uint8_t *m,size_t n) {
    size_t o=6,vn; uint16_t id; const uint8_t *v; int changed=0;
    while (tlv_next(m,n,&o,&id,&v,&vn)) {
        if (id==1 && vn>=1) { s->active=v[0]!=0; changed=1; }
        else if (id==3) { text_copy(s->current_road,sizeof(s->current_road),v,vn); changed=1; }
        else if (id==10 && vn>=4) { s->distance=be32(v); s->bargraph=s->distance>=1000?255:(uint8_t)((s->distance*255U)/1000U); changed=1; }
        else if (id==13 && vn>=2) {
            unsigned index=vn>=4?be16(v+2):be16(v);
            select_maneuver(s,index); changed=1;
        }
    }
    return changed;
}

static int parse_maneuver(cw_rgi_state *s,const uint8_t *m,size_t n) {
    size_t o=6,vn; uint16_t id; const uint8_t *v; unsigned index=0,type=0,junction=0,driving=0; int angle=0,seen=0; char description[97]={0},after[97]={0},exit_info[97]={0};
    while (tlv_next(m,n,&o,&id,&v,&vn)) {
        if (id==1 && vn>=2) index=be16(v);
        else if (id==2) text_copy(description,sizeof(description),v,vn);
        else if (id==3 && vn>=1) { type=v[0]; seen=1; }
        else if (id==4) text_copy(after,sizeof(after),v,vn);
        else if (id==8 && vn>=1) driving=v[0];
        else if (id==9 && vn>=1) junction=v[0];
        else if (id==11 && vn>=2) angle=(int16_t)be16(v);
        else if (id==13) text_copy(exit_info,sizeof(exit_info),v,vn);
    }
    if (!seen || index>=64) return 0;
    {
        cw_rgi_maneuver *item=&s->maneuvers[index];
        memset(item,0,sizeof(*item)); item->valid=1;
        map_maneuver(type,angle,junction,driving,&item->main_element,&item->direction);
        item->z_level=0;
        strncpy(item->description,description,sizeof(item->description)-1);
        strncpy(item->after_road,after,sizeof(item->after_road)-1);
        strncpy(item->exit_info,exit_info,sizeof(item->exit_info)-1);
    }
    if(index==s->maneuver_index || (s->epoch==0 && index==0)) select_maneuver(s,index);
    s->active=1; return 1;
}

static int parse_lanes(cw_rgi_state *s,const uint8_t *m,size_t n) {
    size_t o=6,vn; uint16_t id; const uint8_t *v; unsigned count=0;
    while (tlv_next(m,n,&o,&id,&v,&vn)) if (id==2) {
        size_t p=0; cw_rgi_lane lane; memset(&lane,0,sizeof(lane)); lane.direction=1000;
        while (p+4<=vn) { uint16_t z=be16(v+p),sid=be16(v+p+2); const uint8_t *sv=v+p+4; size_t sn;
            if (z<4 || p+z>vn) return 0;
            sn=z-4;
            if (sid==0 && sn>=1) lane.position=sn>=2?be16(sv):sv[0];
            else if (sid==1 && sn>=1) lane.guidance=sv[0];
            else if (sid==2 && sn>=2 && lane.direction==1000) lane.direction=be16(sv);
            else if (sid==3 && sn>=2) lane.direction=be16(sv);
            p+=z;
        }
        if (count<12) { lane.type=0; lane.marking_left=lane.marking_right=1; lane.description=0; s->lanes[count++]=lane; }
    }
    s->lane_count=(uint8_t)count; return count!=0;
}

int cw_rgi_consume(cw_rgi_state *s,const uint8_t *m,size_t n) {
    uint16_t id; int changed=0; if (!s || !m || n<6) return 0; id=be16(m+4);
    if (!valid(m,n,id)) return 0;
    if (id==0x5201) changed=parse_update(s,m,n);
    else if (id==0x5202) changed=parse_maneuver(s,m,n);
    else if (id==0x5203) {
        s->active=0; s->lane_count=0; s->maneuver_index=0;
        memset(s->maneuvers,0,sizeof(s->maneuvers));
        s->current_road[0]=0; s->turn_to[0]=0; changed=1;
    }
    else if (id==0x5204) changed=parse_lanes(s,m,n);
    if (changed) ++s->epoch;
    return changed;
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
    char body[2048],tmp[256],file[256]; size_t used; unsigned i; int fd; uint32_t crc; time_t now=time(NULL);
    if(!s||!path||strlen(path)>230)return -1;
    used=(size_t)snprintf(body,sizeof(body),"CWRG1 %llu %llu %d %u %u %u %u %d %u",
        (unsigned long long)s->epoch,(unsigned long long)now,s->active,s->distance,s->bargraph,s->main_element,s->direction,s->z_level,s->lane_count);
    for(i=0;i<s->lane_count&&used<sizeof(body);i++){const cw_rgi_lane *l=&s->lanes[i];used+=(size_t)snprintf(body+used,sizeof(body)-used," %u,%u,%u,%u,%u,%u,%u",l->position,l->direction,l->type,l->marking_left,l->marking_right,l->description,l->guidance);}
    used+=(size_t)snprintf(body+used,sizeof(body)-used," ");
    if(!s->current_road[0]) used+=(size_t)snprintf(body+used,sizeof(body)-used,"-");
    else for(i=0;s->current_road[i]&&used+2<sizeof(body);i++) used+=(size_t)snprintf(body+used,sizeof(body)-used,"%02x",(unsigned char)s->current_road[i]);
    used+=(size_t)snprintf(body+used,sizeof(body)-used," ");
    if(!s->turn_to[0]) used+=(size_t)snprintf(body+used,sizeof(body)-used,"-");
    else for(i=0;s->turn_to[i]&&used+2<sizeof(body);i++) used+=(size_t)snprintf(body+used,sizeof(body)-used,"%02x",(unsigned char)s->turn_to[i]);
    if(used+11>=sizeof(body))return -1;
    body[used++]=' ';crc=crc32_bytes((const uint8_t*)body,used);used+=(size_t)snprintf(body+used,sizeof(body)-used,"%08x\n",crc);
    snprintf(file,sizeof(file),"%s.tmp",path);fd=open(file,O_WRONLY|O_CREAT|O_TRUNC,0600);if(fd<0)return -1;
    if(write(fd,body,used)!=(ssize_t)used){close(fd);unlink(file);return -1;}close(fd);if(rename(file,path)!=0){unlink(file);return -1;} (void)tmp; return 0;
}
