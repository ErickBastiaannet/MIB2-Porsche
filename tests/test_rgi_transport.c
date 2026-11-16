/* Baseline RX ownership and passive lifecycle integration. This fixture does
 * not claim that a synchronous OEM sender cannot block on the physical unit. */
#define _GNU_SOURCE
#include <assert.h>
#define dlopen cw_test_dlopen
#include "../native/porsche_rgi_hook.c"
#undef dlopen
static unsigned char packet[40];
static int pushed, handled, data_rc, header_rc, owner_rc, sends, link_token;
static void *pop(void *link){assert(link==&link_token);return packet;}
static int push(void *link,void *p){assert(link==&link_token&&p==packet);pushed++;return 0;}
static int data(void *link,void *p){assert(link==&link_token&&p==packet);return data_rc;}
static int header(void *link,void *p){assert(link==&link_token&&p==packet);return header_rc;}
static int no_probe(void *link,void *p){(void)link;(void)p;return 0;}
static int consume(void *link,void *p){assert(link==&link_token&&p==packet);handled++;return owner_rc;}
static int send(void *link,const void *p,unsigned int n){
    const unsigned char *b=p;assert(link==&link_token&&n==24&&b[4]==0x52&&b[5]==0);sends++;return 0;
}
int main(void){
    pop_packet=pop;push_packet=push;get_data=data;parse_header=header;
    probe_yes=probe_no=no_probe;handle_message=consume;send_raw=send;
    data_rc=1;assert(receive_hook(&link_token)==0&&pushed==1&&handled==0);
    data_rc=0;owner_rc=1;assert(receive_hook(&link_token)==0&&pushed==1&&handled==1);
    owner_rc=2;assert(receive_hook(&link_token)==0&&pushed==2&&handled==2);
    owner_rc=0;assert(receive_hook(&link_token)==0&&pushed==3&&handled==3);
    identified=1;got_guidance=0;last_request=0;
    assert(receive_hook(&link_token)==0&&sends==1);
    got_guidance=1;state.active=1;state.epoch=2;state.arrival_deadline_ms=1;
    assert(receive_hook(&link_token)==0&&sends==1&&!state.active&&state.end_reason==CW_RGI_END_ARRIVAL);
    puts("PORSCHE_RGI_TRANSPORT_PASS baseline RX ownership; unchanged request shape; passive expiry");return 0;
}
