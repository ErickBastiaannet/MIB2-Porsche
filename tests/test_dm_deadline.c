#include "porsche_dm.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
    char text[512];uint64_t before,deadline;
    assert(argc==2);
    before=cw_monotonic_ms();
    assert(!cw_dm_query_until(argv[1],"gs",text,sizeof(text),before));
    assert(cw_monotonic_ms()-before<500);
    /* One shared live-maintenance budget, not a renewed timeout per call. */
    before=cw_monotonic_ms();deadline=before+200;
    assert(cw_dm_query_until(argv[1],"gd",text,sizeof(text),deadline));
    assert(strstr(text,"FAKE_DISPLAY_REPLY"));
    assert(!cw_dm_query_until(argv[1],"gs",text,sizeof(text),deadline));
    assert(cw_monotonic_ms()-before<1500);
    assert(!cw_dm_query_until(argv[1],"gd",text,sizeof(text),deadline));
    /* Cold-start diagnostics retain their ordinary allowance. */
    assert(cw_dm_query(argv[1],"gs",text,sizeof(text)));
    puts("PORSCHE_DM_DEADLINE_PASS shared live budget; stalled query killed; cold query retained");
    return 0;
}
