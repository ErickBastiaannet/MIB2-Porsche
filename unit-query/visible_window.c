/* Bounded compositor-window diagnostic. No persistent installation. */
#define _POSIX_C_SOURCE 200809L
#include "porsche_window.h"
#include "porsche_window_loader.h"
#include "porsche_dm.h"
#include "porsche_wire.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <time.h>
#include <spawn.h>
#ifndef CW_DMDT
#define CW_DMDT "/eso/bin/apps/dmdt"
#endif
extern char **environ;
static const unsigned overlay_layers[]={33,78};
static const unsigned overlay_top_layers[]={78,33};
static int declare_overlay(const char *root,int top){
    char *args[]={"dmdt","dc","70","33","78",NULL};
    char report[65536];pid_t child;int status;
    if(top){args[3]="78";args[4]="33";}
    if(posix_spawn(&child,CW_DMDT,NULL,NULL,args,environ))return 0;
    if(waitpid(child,&status,0)!=child||!WIFEXITED(status)||WEXITSTATUS(status))return 0;
    return cw_dm_query(root,"gc",report,sizeof(report))&&
        cw_dm_context_layers(report,70,top?overlay_top_layers:overlay_layers,2)==1;
}

#ifndef CW_RUNTIME
#define CW_RUNTIME "/ramdisk"
#endif
static volatile sig_atomic_t stopped;
static void stop(int n){(void)n;stopped=1;}
static int restore(const char *root,const cw_display *original){
    char text[16384];cw_display now;
    if(!cw_dm_query(root,"gs",text,sizeof(text))||!cw_dm_display(text,&now)||now.id!=original->id)return 0;
    if(now.context!=70)return 1; /* preserve another page selected by the driver */
    return cw_dm_switch(root,original->id,(unsigned)original->context)&&
        cw_dm_query(root,"gs",text,sizeof(text))&&cw_dm_display(text,&now)&&now.context==original->context;
}
static void watch(const char *root,const cw_display *before,int fd,pid_t owner){
    fd_set descriptors;struct timeval timeout={18,0};int event;
    alarm(0);signal(SIGTERM,SIG_IGN);signal(SIGINT,SIG_IGN);signal(SIGHUP,SIG_IGN);
    FD_ZERO(&descriptors);FD_SET(fd,&descriptors);
    event=select(fd+1,&descriptors,NULL,NULL,&timeout);
    if(!restore(root,before))fputs("WINDOW_GUARD_RESTORE_FAILED\n",stderr);
    if(event==0&&getppid()==owner){
        struct timespec pause={0,500000000};kill(owner,SIGTERM);nanosleep(&pause,NULL);
        if(getppid()==owner)kill(owner,SIGKILL);
    }
    close(fd);_exit(0);
}
int main(int argc,char **argv){
    cw_window window;cw_window_libraries libraries;cw_display before,now;
    char report[65536];uint32_t lease[4];unsigned backend;int state,result=1,changed=0;
    int pipefd[2]={-1,-1},overlay=0,top=0;pid_t guard=-1;
    memset(&window,0,sizeof(window));memset(&libraries,0,sizeof(libraries));
    if(argc!=3)return 2;
    top=!strcmp(argv[2],"--visible-window-overlay-top-5s");
    overlay=top||!strcmp(argv[2],"--visible-window-overlay-5s");
    if(!overlay&&strcmp(argv[2],"--visible-window-5s"))return 2;
    signal(SIGTERM,stop);signal(SIGINT,stop);signal(SIGHUP,stop);alarm(20);
    if(!cw_dm_query(argv[1],"gs",report,sizeof(report))||!cw_dm_display(report,&before)||
       !cw_map_context((unsigned)before.context)||!cw_dm_backend_id(before.id,&backend)){
        puts("WINDOW_TEST_DISPLAY_REJECTED");goto done;
    }
    if(!cw_dm_query(argv[1],"gd",report,sizeof(report))||!cw_dm_layer(report,78,before.width,before.height,0)){
        puts("WINDOW_TEST_LAYER_NOT_FREE");goto done;
    }
    if(!cw_dm_query(argv[1],"gc",report,sizeof(report)))goto done;
    state=cw_dm_context_state(report,70,78);
    if(overlay&&state==2&&cw_dm_context_layers(report,70,overlay_layers,2)==1)state=3;
    if(overlay&&state==2&&cw_dm_context_layers(report,70,overlay_top_layers,2)==1)state=4;
    if(state==1||state==3||state==4){
        if(!cw_wire_read(CW_RUNTIME "/cw-porsche-context-owner.v1","CWCO1",lease,4)||
           lease[0]<=1||lease[2]!=70||lease[3]!=78||kill((pid_t)lease[0],0)==0||errno!=ESRCH){
            puts("WINDOW_TEST_CONTEXT_NOT_OWNED");goto done;
        }
    }else if(state!=0){puts("WINDOW_TEST_CONTEXT_OCCUPIED");goto done;}
    if(pipe(pipefd))goto done;
    /* Fork the guardian BEFORE loading EGL and starting vendor GPU threads. */
    guard=fork();if(guard<0)goto done;
    if(guard==0){close(pipefd[1]);watch(argv[1],&before,pipefd[0],getppid());}
    close(pipefd[0]);pipefd[0]=-1;
    if(!cw_window_load(&libraries)||!cw_window_start(&window,&libraries.api,before.width,before.height,78)){
        puts("WINDOW_TEST_CREATE_FAILED");goto done;
    }
    if(!cw_dm_query(argv[1],"gd",report,sizeof(report))||!cw_dm_layer(report,78,before.width,before.height,1)){
        puts("WINDOW_TEST_REGISTRATION_FAILED");goto done;
    }
    if(overlay){
        if(state!=(top?4:3)&&!declare_overlay(argv[1],top))goto done;
    }else if(state==0&&!cw_dm_declare(argv[1],70,78))goto done;
    lease[0]=(uint32_t)getpid();lease[1]=(uint32_t)time(NULL);lease[2]=70;lease[3]=78;
    if(!cw_wire_write(CW_RUNTIME "/cw-porsche-context-owner.v1","CWCO1",lease,4))goto done;
    if(!cw_dm_query(argv[1],"gs",report,sizeof(report))||!cw_dm_display(report,&now)||
       now.id!=before.id||now.context!=before.context||stopped)goto done;
    changed=1;
    if(!cw_dm_switch(argv[1],before.id,70)||!cw_dm_query(argv[1],"gs",report,sizeof(report))||
       !cw_dm_display(report,&now)||now.context!=70){puts("WINDOW_TEST_SWITCH_FAILED");goto done;}
    printf("WINDOW_TEST_ACTIVE_5_SECONDS backend=%u size=%ux%u keep_map=%d top_first=%d\n",backend,before.width,before.height,overlay,top);fflush(stdout);
    {
        uint64_t until=cw_monotonic_ms()+5000;
        while(!stopped&&cw_monotonic_ms()<until){
            struct timespec pause={0,40000000};
            if(!cw_window_bars(&window))goto done;
            nanosleep(&pause,NULL);
        }
    }
    if(restore(argv[1],&before)){changed=0;puts("WINDOW_TEST_MAP_RESTORED");result=0;}
done:
    if(changed)(void)restore(argv[1],&before);
    if(pipefd[1]>=0)close(pipefd[1]);
    if(guard>0)(void)waitpid(guard,NULL,0);
    if(pipefd[0]>=0)close(pipefd[0]);
    cw_window_stop(&window);cw_window_unload(&libraries);
    return result;
}
