#include "porsche_parser.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static int bad_hash, missing, libraries, creates, destroys, published;
static void *saved_functions,*saved_user;
static int fixture_hash(const char *path,char digest[65]) {
 assert(path);strcpy(digest,bad_hash?"bad":strstr(path,"libnvparser")?
 "56b7f7195984ad76223f94c24b954c2bcc79a8f6125d30aa9265470d83bd2e94":
 "b57f3eb1697c6846d06a1c546ad8b06834c630ccfac88c6ea6787dd5ccc41475");return 1;
}
static void *fixture_open(const char *path,int flags){assert(path&&flags);++libraries;return (void *)1;}
static int fixture_close(void *p){assert(p==(void *)1&&libraries==1);--libraries;return 0;}
/* Separate declaration to let the included implementation define its ABI. */
static void *fixture_symbol(void *,const char *);
#define cw_sha256_file fixture_hash
#define dlopen fixture_open
#define dlclose fixture_close
#define dlsym fixture_symbol
#include "../native/porsche_parser.c"
#undef cw_sha256_file
#undef dlopen
#undef dlclose
#undef dlsym
static void *original_create(const parameters *p){
 assert(p&&p->clock_rate==1000000&&p->buffering==50&&p->codec==4&&p->extended_sequence==(void *)14);
 saved_functions=p->functions;saved_user=p->user;++creates;return (void *)20;
}
static void original_destroy(void *p){assert(p==(void *)20);++destroys;}
static void *fixture_symbol(void *p,const char *name){assert(p==(void *)1);if(missing)return NULL;
 if(!strcmp(name,"video_parser_create"))return (void *)original_create;
 if(!strcmp(name,"video_parser_destroy"))return (void *)original_destroy;
 assert(0);return NULL;
}
static void publish_surface(void *p){assert(p==(void *)30);++published;}
int main(void){
 callbacks table;parameters config;unsigned i;unsigned char picture[12+sizeof(void *)], data[8+sizeof(void *)];void *ptr;
 memset(&config,0,sizeof(config));for(i=0;i<7;++i)table.callbacks[i]=(void *)(uintptr_t)(i+1);
 config.functions=&table;config.user=(void *)10;config.clock_rate=1000000;config.buffering=50;config.codec=4;config.extended_sequence=(void *)14;
 bad_hash=1;assert(!cw_parser_start(publish_surface)&&!libraries);
 bad_hash=0;missing=1;assert(!cw_parser_start(publish_surface)&&!libraries);
 missing=0;assert(cw_parser_start(publish_surface));assert(!cw_parser_start(publish_surface));
 config.codec=3;assert(!video_parser_create(&config));config.codec=4;
 assert(video_parser_create(&config)==(void *)20&&creates==1);
 assert(!video_parser_create(&config)&&creates==1);
 assert(saved_functions!=&table&&saved_user==config.user);
 for(i=0;i<7;++i)if(i!=2)assert(((callbacks *)saved_functions)->callbacks[i]==table.callbacks[i]);
 assert(table.callbacks[2]==(void *)3);
 memset(picture,0,sizeof(picture));memset(data,0,sizeof(data));
 ptr=data;memcpy(picture+12,&ptr,sizeof(ptr));ptr=(void *)30;memcpy(data+8,&ptr,sizeof(ptr));
 assert(display_picture(config.user,picture,1234)==1&&published==1);
 ptr=NULL;memcpy(data+8,&ptr,sizeof(ptr));assert(!display_picture(config.user,picture,1234));
 assert(!display_picture(config.user,NULL,1234));
 cw_parser_stop();assert(libraries==1); /* never unload an active callback table */
 video_parser_destroy((void *)99);assert(!destroys);
 video_parser_destroy((void *)20);assert(destroys==1);
 cw_parser_stop();cw_parser_stop();assert(!libraries);
 puts("PARSER_CAPTURE_PASS firmware guards, callback ABI, preserved parameters, persistent callback table, picture access, single owner, shutdown");return 0;
}
