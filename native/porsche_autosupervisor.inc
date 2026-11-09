/* MU1417: smartphone_integrator recreates DIO on USB reconnect. Bind the
 * supervisor to each receiver instance, rather than a former shell PID. */
#include <spawn.h>
#include <sys/stat.h>
#include <sys/wait.h>
static int cw_auto_copy(const char *source,const char *target) {
    char bytes[4096];ssize_t n;int in=open(source,O_RDONLY),out;
    if(in<0)return -1;
    out=open(target,O_WRONLY|O_CREAT|O_TRUNC,0700);
    if(out<0){close(in);return -1;}
    while((n=read(in,bytes,sizeof(bytes)))>0){
        if(write(out,bytes,(size_t)n)!=n){close(in);close(out);return -1;}
    }
    close(in);close(out);return n<0?-1:0;
}
static void *cw_auto_supervisor(void *unused) {
    const char *root="/ramdisk/cw-link-probe-20261102";
    const char *base="/mnt/app/eso/hmi/connectwow-carplay/controls-v15";
    char owner[32],tool[256],query[256],target[256],marker[256];
    char *args[5],*env[4];pid_t child;int fd,status;
    posix_spawn_file_actions_t actions;
    (void)unused;
    sleep(1);
    if(mkdir(root,0700)!=0&&errno!=EEXIST)return NULL;
    snprintf(tool,sizeof(tool),"%s/cw-window-candidate",base);
    snprintf(query,sizeof(query),"%s/libcw-query-stdio.so",base);
    snprintf(target,sizeof(target),"%s/libcw-query-stdio.so",root);
    if(cw_auto_copy(query,target)!=0)return NULL;
    snprintf(marker,sizeof(marker),"%s/enabled",root);
    fd=open(marker,O_WRONLY|O_CREAT|O_TRUNC,0600);
    if(fd<0)return NULL;
    write(fd,"enabled\n",8);close(fd);
    snprintf(owner,sizeof(owner),"%ld",(long)getpid());
    args[0]=tool;args[1]="--run";args[2]=(char *)root;args[3]=owner;args[4]=NULL;
    env[0]="PATH=/bin:/usr/bin:/armle/bin:/armle/usr/bin";
    env[1]="LD_LIBRARY_PATH=/mnt/app/armle/lib:/mnt/app/armle/usr/lib:/mnt/app/root/lib-target:/eso/lib:/armle/lib:/armle/lib/dll:/armle/usr/lib";
    env[2]="IPL_CONFIG_DIR=/etc/eso/production";env[3]=NULL;
    if(posix_spawn_file_actions_init(&actions)!=0)return NULL;
    status=posix_spawn_file_actions_addopen(&actions,0,"/dev/null",O_RDONLY,0);
    if(!status)status=posix_spawn_file_actions_addopen(&actions,1,
        "/ramdisk/cw-link-probe-20261102/cw-carplay-live-v14.log",O_WRONLY|O_CREAT|O_APPEND,0600);
    if(!status)status=posix_spawn_file_actions_adddup2(&actions,1,2);
    if(!status)status=posix_spawn(&child,tool,&actions,NULL,args,env);
    posix_spawn_file_actions_destroy(&actions);
    log_status("porsche-owner-supervisor-spawn",NULL,status);
    if(!status)while(waitpid(child,&status,0)<0&&errno==EINTR){}
    return NULL;
}
__attribute__((constructor)) static void cw_auto_supervisor_loaded(void) {
    pthread_t thread;const char *value=getenv("CW_PROCESS_SUPERVISOR");
    if(!value||strcmp(value,"1"))return;
    if(pthread_create(&thread,NULL,cw_auto_supervisor,NULL)==0)pthread_detach(thread);
}
