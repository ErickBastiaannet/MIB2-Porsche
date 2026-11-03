/* WITHDRAWN direct-stream experiment. The physical cluster did not display
 * this stream; context switches caused a temporary map-unavailable warning.
 * Keep for research only. Use window_selftest for the new compositor route. */
#define _POSIX_C_SOURCE 200809L
#include "porsche_nvss.h"
#include "porsche_dm.h"
#include "porsche_wire.h"
#include "porsche_sha256.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <dlfcn.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <time.h>
#include <errno.h>
#ifndef CW_RUNTIME
#define CW_RUNTIME "/ramdisk"
#endif
#ifndef CW_DMDT
#define CW_DMDT "/eso/bin/apps/dmdt"
#endif
#ifndef CW_DISPLAY_CONFIG
#define CW_DISPLAY_CONFIG "/etc/eso/production/displaymanager.json"
#endif
#ifndef CW_DISPLAY_CONFIG_SHA
#define CW_DISPLAY_CONFIG_SHA "115df2ffd860a6adccd4dd10c643a13b575a439922b272942025df8c7c246202"
#endif

/* Diagnostic profile only: the verified 2_lvds configuration binds native
 * display ID 4 to terminal 2nd_lvds. gs prints vector indices, not IDs.
 * Decoder output indices are a separate namespace (secondary output 1). */
static int verified_profile(void) {
    char digest[65];
    return cw_sha256_file(CW_DISPLAY_CONFIG,digest)&&!strcmp(digest,CW_DISPLAY_CONFIG_SHA);
}
static int switch_cluster(const char *root,unsigned index,unsigned context) {
    char text[8192],helper[512],target[16];cw_display display;pid_t child;int status;
    if(index!=1||context>157||!verified_profile()||
       !cw_dm_query(root,"gs",text,sizeof(text))||!cw_dm_display(text,&display)||display.id!=index)return 0;
    if(snprintf(helper,sizeof(helper),"%s/libcw-query-stdio.so",root)>=(int)sizeof(helper))return 0;
    snprintf(target,sizeof(target),"%u",context);
    child=fork();if(child==0){
        setenv("LD_PRELOAD",helper,1);setenv("IPL_CONFIG_DIR","/etc/eso/production",1);
        execl(CW_DMDT,"dmdt","sc","4",target,(char *)NULL);_exit(127);
    }
    if(child<0)return 0;
    return waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0;
}

static volatile sig_atomic_t stop;
static void stopping(int n) { (void)n; stop=1; }
static unsigned be32(const unsigned char *p) {
    return ((unsigned)p[0]<<24)|((unsigned)p[1]<<16)|((unsigned)p[2]<<8)|p[3];
}
static int restore(const char *root, const cw_display *before) {
    char report[8192]; cw_display now;
    if(!cw_dm_query(root,"gs",report,sizeof(report))||!cw_dm_display(report,&now))return 0;
    if(now.id!=before->id)return 0;
    /* Never take over a different page selected by the driver. */
    if(now.context!=70)return 1;
    if(!switch_cluster(root,before->id,(unsigned)before->context))return 0;
    return cw_dm_query(root,"gs",report,sizeof(report))&&cw_dm_display(report,&now)&&now.context==before->context;
}
static void guardian(const char *root, const cw_display *before,int fd,pid_t parent) {
    fd_set fds;struct timeval timeout={12,0};int event;
    signal(SIGTERM,SIG_IGN);signal(SIGINT,SIG_IGN);signal(SIGHUP,SIG_IGN);
    FD_ZERO(&fds);FD_SET(fd,&fds);event=select(fd+1,&fds,NULL,NULL,&timeout);
    (void)restore(root,before);
    if(event==0&&getppid()==parent)kill(parent,SIGTERM);
    close(fd);_exit(0);
}
int main(int argc,char **argv) {
    cw_nvss sink;cw_nvss_api api;cw_display before,now;
    char report[65536];unsigned char header[20],*config=NULL,*frame=NULL;
    unsigned w,h,cs,fs;uint32_t lease[4];void *library=NULL;FILE *file=NULL;
    int result=1,guardfd[2]={-1,-1},changed=0,context_state;pid_t guard=-1;unsigned i;
    memset(&sink,0,sizeof(sink));
    signal(SIGTERM,stopping);signal(SIGINT,stopping);signal(SIGHUP,stopping);
    if(argc!=4||strcmp(argv[3],"--visible-test-5s"))return 2;
    if(!verified_profile()){puts("TEST_DISPLAY_PROFILE_MISMATCH");goto done;}
    if(!cw_dm_query(argv[1],"gs",report,sizeof(report))||!cw_dm_display(report,&before)||
       !cw_map_context((unsigned)before.context)){puts("TEST_REQUIRES_ORIGINAL_CLUSTER_MAP");goto done;}
    if(before.id!=1){puts("TEST_REQUIRES_SECONDARY_OUTPUT");goto done;}
    if(!cw_dm_query(argv[1],"gc",report,sizeof(report)))goto done;
    context_state=cw_dm_context_state(report,70,78);
    if(context_state==1){
        if(!cw_wire_read(CW_RUNTIME "/cw-porsche-context-owner.v1","CWCO1",lease,4)||
           lease[0]<=1||lease[2]!=70||lease[3]!=78||kill((pid_t)lease[0],0)==0||errno!=ESRCH){
            puts("TEST_CONTEXT_NOT_OWNED");goto done;}
    }else if(context_state!=0){puts("TEST_CONTEXT_NOT_FREE");goto done;}
    if(!cw_dm_query(argv[1],"gd",report,sizeof(report))||!cw_dm_layer(report,78,before.width,before.height,0))goto done;
    file=fopen(argv[2],"rb");if(!file||fread(header,1,20,file)!=20||memcmp(header,"CWNV",4))goto done;
    w=be32(header+4);h=be32(header+8);cs=be32(header+12);fs=be32(header+16);
    if(w!=before.width||h!=before.height||!cs||cs>4096||!fs||fs>1024*1024)goto done;
    config=malloc(cs);frame=malloc(fs);if(!config||!frame)goto done;
    if(fread(config,1,cs,file)!=cs||fread(frame,1,fs,file)!=fs||fgetc(file)!=EOF)goto done;
    library=dlopen("libnvss_video.so",RTLD_NOW|RTLD_LOCAL);
    if(!library){printf("NVSS_LIBRARY_UNAVAILABLE: %s\n",dlerror());goto done;}
    api.open=(int32_t (*)(void **,const cw_nvss_open *))dlsym(library,"NvSSVideoOpen");
    api.configure=(int32_t (*)(void *,const cw_nvss_stream *))dlsym(library,"NvSSVideoStreamConfigure");
    api.decode=(int32_t (*)(void *,const cw_nvss_unit *,uint32_t))dlsym(library,"NvSSVideoDecode");
    api.close=(int32_t (*)(void *))dlsym(library,"NvSSVideoClose");
    if(!cw_nvss_start(&sink,&api,w,h,78,before.id,config,cs)||cw_nvss_frame(&sink,frame,fs,0)!=1){
        puts("TEST_VIDEO_REJECTED");goto done;}
    if(!cw_dm_query(argv[1],"gd",report,sizeof(report))||!cw_dm_layer(report,78,w,h,1)){
        puts("TEST_LAYER_NOT_REGISTERED");puts(report);goto done;}
    if(context_state==0&&!cw_dm_declare(argv[1],70,78)){puts("TEST_CONTEXT_DECLARATION_FAILED");goto done;}
    lease[0]=(uint32_t)getpid();lease[1]=(uint32_t)time(NULL);lease[2]=70;lease[3]=78;
    if(!cw_wire_write(CW_RUNTIME "/cw-porsche-context-owner.v1","CWCO1",lease,4)||pipe(guardfd))goto done;
    guard=fork();if(guard<0)goto done;
    if(guard==0){close(guardfd[1]);guardian(argv[1],&before,guardfd[0],getppid());}
    close(guardfd[0]);guardfd[0]=-1;
    /* Re-check immediately before switching: respect a newly selected page. */
    if(!cw_dm_query(argv[1],"gs",report,sizeof(report))||!cw_dm_display(report,&now)||
       now.context!=before.context||now.id!=before.id||stop)goto done;
    changed=1;
    if(!switch_cluster(argv[1],before.id,70)){puts("TEST_SWITCH_REJECTED");goto done;}
    if(!cw_dm_query(argv[1],"gs",report,sizeof(report))||!cw_dm_display(report,&now)||now.context!=70){
        puts("TEST_CONTEXT_NOT_SELECTED");goto done;}
    puts("VISIBLE_TEST_ACTIVE_5_SECONDS");fflush(stdout);
    {
      uint64_t until=cw_monotonic_ms()+5000;
      for(i=0;cw_monotonic_ms()<until&&!stop;++i){
        struct timespec pause={0,40000000};
        if(cw_nvss_frame(&sink,frame,fs,0)!=1)break;
        nanosleep(&pause,NULL);
      }
    }
    if(restore(argv[1],&before)){changed=0;puts("VISIBLE_TEST_MAP_RESTORED");result=0;}
done:
    if(changed)(void)restore(argv[1],&before);
    /* Closing the pipe wakes the guardian for an independent restore check. */
    if(guardfd[1]>=0)close(guardfd[1]);
    if(guard>0)(void)waitpid(guard,NULL,0);
    if(guardfd[0]>=0)close(guardfd[0]);
    cw_nvss_stop(&sink);if(library)dlclose(library);if(file)fclose(file);
    free(config);free(frame);return result;
}
