#include "porsche_sha256.h"
#include "porsche_wire.h"
#include "porsche_dm.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void sha(const char *path, const char *content, const char *expected)
{
    char actual[65];
    FILE *file = fopen(path, "wb"); assert(file);
    assert(fwrite(content, 1, strlen(content), file) == strlen(content));
    assert(fclose(file) == 0);
    assert(cw_sha256_file(path, actual) && !strcmp(actual, expected));
}
int main(int argc, char **argv)
{
    char path[512], digest[65]; uint32_t before[]={7,1234567890,960,640}, after[4];
    cw_display display; FILE *file; unsigned i;
    assert(argc==3); snprintf(path,sizeof(path),"%s/support.record",argv[1]);
    sha(path,"","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    sha(path,"abc","ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    sha(path,"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");
    file=fopen(path,"wb"); assert(file);
    for(i=0;i<1000000;++i)assert(fputc('a',file)!=EOF);
    assert(!fclose(file)); assert(cw_sha256_file(path,digest));
    assert(!strcmp(digest,"cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"));
    assert(cw_crc32("123456789",9)==0xcbf43926U);
    assert(cw_wire_write(path,"CWRD1",before,4));
    assert(cw_wire_read(path,"CWRD1",after,4)&&!memcmp(before,after,sizeof(before)));
    assert(!cw_wire_read(path,"CWCT1",after,4));
    file=fopen(path,"ab"); assert(file); fputs("x",file); fclose(file);
    assert(!cw_wire_read(path,"CWRD1",after,4));
    assert(cw_dm_display("displaymanager reports the following system information:\n"
        "display 0:\n terminal: main\n size: 1440 x 540\n context id: 78\n"
        "display 1:\n terminal: 2nd_lvds\n size: 960 x 640\n context id: 151\n",&display));
    assert(display.width==960&&display.height==640&&display.context==151&&display.id==1);
    assert(!cw_dm_display("display 1:\n terminal: 2nd_lvds\n size: 960 x 640\n context id: 151\n",&display));
    assert(!cw_dm_display("displaymanager reports the following system information:\n"
        "display 1:\n terminal: 2nd_lvds\n size: 960 x 640\n context id: 151\ndisplay 1:\n terminal: 2nd_lvds\n",&display));
    assert(cw_dm_layer("displaymanager knows 2 displayables:\n 78 window 960 x 640\n",78,960,640,1));
    assert(!cw_dm_layer("displaymanager knows 2 displayables:\n 78 window 800 x 298\n",78,960,640,1));
    assert(!cw_dm_layer("displaymanager knows 2 displayables:\n 78 window 960 x 640\n",78,960,640,0));
    assert(cw_dm_layer("displaymanager knows 2 displayables:\n 33 window 960 x 640\n",78,960,640,0));
    assert(!cw_dm_layer("displaymanager knows 7 displayables:\n 78 stream 0 x 0\n",78,800,480,1));
    assert(!cw_dm_layer("displaymanager knows 7 displayables:\n 78 stream 0 x 0\n",78,800,480,0));
    assert(!cw_dm_layer("displaymanager knows 7 displayables:\n 78 stream 1 x 0\n",78,800,480,1));
    assert(cw_map_context(72)&&cw_map_context(151)&&!cw_map_context(78)&&!cw_map_context(70));
    assert(!cw_dm_query("/tmp","sc",path,sizeof(path)));
    assert(cw_dm_context_state("displaymanager knows 2 contexts:\n -8 | 1 | NONE\n -123 (--)\n 72 | 1 | NONE\n 33 (MAP)\n",70,78)==0);
    assert(cw_dm_context_state("displaymanager knows 1 contexts:\n 70 | 1 | NONE\n 78 (OWN)\n",70,78)==1);
    assert(cw_dm_context_state("displaymanager knows 1 contexts:\n 70 | 1 | NONE\n 33 (MAP)\n",70,78)==2);
    assert(cw_dm_context_state("displaymanager knows 2 contexts:\n 70 | 1 | NONE\n 78 (OWN)\n",70,78)==-1);
    {
        const unsigned overlay[]={33,78};
        assert(cw_dm_context_layers("displaymanager knows 1 contexts:\n 70 | 2 | NONE\n 33 (MAP)\n 78 (OWN)\n",70,overlay,2)==1);
        assert(cw_dm_context_layers("displaymanager knows 1 contexts:\n 70 | 2 | NONE\n 78 (OWN)\n 33 (MAP)\n",70,overlay,2)==2);
        assert(cw_dm_context_layers("displaymanager knows 1 contexts:\n 70 | 2 | NONE\n 33 (MAP)\n",70,overlay,2)==-1);
    }
    {
        char report[65536]; size_t size;
        file=fopen(argv[2], "rb"); assert(file);
        size=fread(report, 1, sizeof(report)-1, file);
        assert(!ferror(file) && feof(file)); fclose(file); report[size]=0;
        assert(cw_dm_context_state(report,70,78)==0);
        assert(cw_dm_context_state(report,149,78)==0);
        assert(cw_dm_context_state(report,72,78)==2);
    }
    puts("PORSCHE_SUPPORT_PASS SHA256 standard vectors, CRC records, physical display selection, layer conflict");
    return 0;
}
