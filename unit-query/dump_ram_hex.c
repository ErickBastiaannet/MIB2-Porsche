/* Bounded read-only transfer of our own RAM diagnostics over the RCC console. */
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc,char **argv){
    static char output_buffer[4096];
    static const char hex[]="0123456789abcdef";
    unsigned char input[512];char output[1025],path[256];size_t i,n,total=0;
    struct stat metadata;FILE *file;
    if(argc!=2||strlen(argv[1])>60||strncmp(argv[1],"cw-",3)||strstr(argv[1],".."))return 2;
    for(i=0;argv[1][i];++i)if(!isalnum((unsigned char)argv[1][i])&&argv[1][i]!='-'&&argv[1][i]!='.')return 2;
    snprintf(path,sizeof(path),"/net/mmx/ramdisk/cw-link-probe-20261102/%s",argv[1]);
    file=fopen(path,"rb");if(!file)return 1;
    if(fstat(fileno(file),&metadata)||!S_ISREG(metadata.st_mode)||metadata.st_size<=0||metadata.st_size>2*1024*1024){fclose(file);return 1;}
    alarm(20);setvbuf(stdout,output_buffer,_IOFBF,sizeof(output_buffer));
    printf("HEX_BEGIN %ld\n",(long)metadata.st_size);
    while((n=fread(input,1,sizeof(input),file))!=0){
        total+=n;if(total>(size_t)metadata.st_size){fclose(file);return 1;}
        for(i=0;i<n;++i){output[i*2]=hex[input[i]>>4];output[i*2+1]=hex[input[i]&15];}
        output[n*2]='\n';if(fwrite(output,1,n*2+1,stdout)!=n*2+1){fclose(file);return 1;}
    }
    if(ferror(file)||total!=(size_t)metadata.st_size){fclose(file);return 1;}
    fclose(file);puts("HEX_END");return 0;
}
