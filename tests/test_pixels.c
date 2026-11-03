#include "porsche_pixels.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
int main(void){
 cw_pixels channel={0};unsigned char frame[6144],out[6144];uint32_t sequence=0;unsigned i;pid_t child;int status;
 assert(!cw_pixels_open(&channel,65,64));assert(cw_pixels_open(&channel,64,64));
 assert(!cw_pixels_open(&channel,64,64));assert(!cw_pixels_read(&channel,out,sizeof(out),&sequence));
 assert(!cw_pixels_write(&channel,frame,sizeof(frame)-1));
 child=fork();assert(child>=0);
 if(!child){
  for(i=1;i<=100;++i){memset(frame,(int)i,sizeof(frame));assert(cw_pixels_write(&channel,frame,sizeof(frame)));}
  cw_pixels_close(&channel);_exit(0);
 }
 assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&!WEXITSTATUS(status));
 assert(cw_pixels_read(&channel,out,sizeof(out),&sequence));
 for(i=0;i<sizeof(out);++i)assert(out[i]==100);
 assert(!cw_pixels_read(&channel,out,sizeof(out),&sequence));
 /* A dead writer with an unfinished frame must not wait on a mutex. */
 *(volatile uint32_t *)channel.mapping=sequence+1;
 assert(!cw_pixels_read(&channel,out,sizeof(out),&sequence));
 assert(!cw_pixels_write(&channel,frame,sizeof(frame)));
 cw_pixels_close(&channel);cw_pixels_close(&channel);
 puts("PIXELS_IPC_PASS real fork, shared payload, latest frame, exact size, dead writer, cleanup");return 0;
}
