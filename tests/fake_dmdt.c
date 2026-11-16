#define _POSIX_C_SOURCE 200809L
#include <time.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
    if(argc!=2)return 1;
    if(!strcmp(argv[1],"gs")) {
        struct timespec delay={2,0};nanosleep(&delay,NULL);
    }
    puts("FAKE_DISPLAY_REPLY");return 0;
}
