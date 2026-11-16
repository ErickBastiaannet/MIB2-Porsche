/* MU1417: smartphone_integrator recreates DIO on USB reconnect. Bind the
 * supervisor to each receiver instance, rather than a former shell PID. */
#include <spawn.h>
#include <sys/stat.h>
#include <sys/wait.h>
static int cw_auto_copy(const char *source,const char *target) {
    char bytes[4096],staged[300];ssize_t n;int in=open(source,O_RDONLY),out;
    if(in<0)return -1;
    snprintf(staged,sizeof(staged),"%s.%ld.new",target,(long)getpid());
    out=open(staged,O_WRONLY|O_CREAT|O_TRUNC,0700);
    if(out<0){close(in);return -1;}
    while((n=read(in,bytes,sizeof(bytes)))>0){
        if(write(out,bytes,(size_t)n)!=n){close(in);close(out);return -1;}
    }
    close(in);close(out);return n<0?-1:rename(staged,target);
}
static void *cw_auto_supervisor(void *unused) {
    const char *root="/ramdisk/cw-link-probe-20261102";
    const char *base="/mnt/app/eso/hmi/connectwow-carplay/controls-v15";
    char owner[32],tool[256],query[256],target[256],marker[256];
    char *args[5],*env[4];pid_t child;int fd,status,log_fd;
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
    fd=open("/ramdisk/cw-link-probe-20261102/cw-carplay-live-v14.log",O_WRONLY|O_CREAT|O_APPEND,0600);
    if(fd<0)return NULL;
    log_fd=fcntl(fd,F_DUPFD,3);close(fd);
    if(log_fd<0)return NULL;
    if(posix_spawn_file_actions_init(&actions)!=0){close(log_fd);return NULL;}
    status=posix_spawn_file_actions_addopen(&actions,0,"/dev/null",O_RDONLY,0);
    if(!status)status=posix_spawn_file_actions_adddup2(&actions,log_fd,1);
    if(!status)status=posix_spawn_file_actions_adddup2(&actions,log_fd,2);
    if(!status)status=posix_spawn_file_actions_addclose(&actions,log_fd);
    if(!status)status=posix_spawn(&child,tool,&actions,NULL,args,env);
    posix_spawn_file_actions_destroy(&actions);
    close(log_fd);
    log_status("porsche-owner-supervisor-spawn",NULL,status);
    if(!status)while(waitpid(child,&status,0)<0&&errno==EINTR){}
    return NULL;
}
static pthread_mutex_t cw_auto_lock=PTHREAD_MUTEX_INITIALIZER;
static int cw_auto_started;
static void cw_auto_supervisor_start(void) {
    pthread_t thread;const char *value=getenv("CW_PROCESS_SUPERVISOR");
    if(!value||strcmp(value,"1"))return;
    /* A genuine stream callback proves loader/SDK startup is complete.
     * Never create a thread while an ELF constructor owns ldqnx's lock. */
    pthread_mutex_lock(&cw_auto_lock);
    if(!cw_auto_started&&pthread_create(&thread,NULL,cw_auto_supervisor,NULL)==0){
        cw_auto_started=1;pthread_detach(thread);
    }
    pthread_mutex_unlock(&cw_auto_lock);
}
