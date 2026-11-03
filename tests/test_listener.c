/* Exercise the real generated receiver's socket factory and SETUP response.
 * Only thread creation is held back; sockets and the IPv6 client are real. */
#define _GNU_SOURCE
#include <pthread.h>
#include <assert.h>
#include <errno.h>
static void *pending_listener;
static int thread_failure;
static int hold_thread(pthread_t *thread, const pthread_attr_t *attr,
                       void *(*entry)(void *), void *arg) {
    assert(thread && !attr && entry && arg);
    if (thread_failure)
        return EAGAIN;
    *thread = (pthread_t)1;
    pending_listener = arg;
    return 0;
}
static int hold_detach(pthread_t thread) { assert(thread == (pthread_t)1); return 0; }
#define pthread_create hold_thread
#define pthread_detach hold_detach
#define main unused_display_fixture_main
#include "../build/native/test_capture_display.c"
#undef main
#undef pthread_create
#undef pthread_detach

int main(void) {
    uint16_t port = 0;
    uint8_t zero[16] = {0};
    Obj *session = new_obj(DICT), *response, *streams;
    PassiveListener *listener;
    struct sockaddr_in6 address;
    socklen_t size = sizeof(address);
    int client, accepted, only_v6 = 0;
    socklen_t option_size = sizeof(only_v6);
    setenv("CARPLAY_ALTSCREEN_LOG", "/dev/null", 1);
    memset(&cw_advertised_geometry, 0, sizeof(cw_advertised_geometry));
    cw_advertised_geometry.width = 800;
    cw_advertised_geometry.height = 480;
    assert(!start_passive_listener(&port, zero, zero, 0, session));
    listener = pending_listener;
    /* MU1417 /etc/pf.conf permits TCP 7000:7001 and then drops carplay0.
     * The old ephemeral 65xxx ports can therefore never deliver video. */
    assert(port == 7001 && listener && listener->port == 7001);
    assert(!getsockname(listener->server_fd, (struct sockaddr *)&address, &size));
    assert(address.sin6_family == AF_INET6 && ntohs(address.sin6_port) == 7001);
    assert(!getsockopt(listener->server_fd, IPPROTO_IPV6, IPV6_V6ONLY, &only_v6, &option_size));
    assert(only_v6 == 1);
    client = socket(AF_INET6, SOCK_STREAM, 0);
    assert(client >= 0);
    address.sin6_addr = in6addr_loopback;
    assert(!connect(client, (struct sockaddr *)&address, sizeof(address)));
    accepted = accept(listener->server_fd, NULL, NULL);
    assert(accepted >= 0);
    response = create_alt_stream_response(port);
    assert(response);
    streams = lookup(response, "streams");
    assert(streams && streams->count == 1);
    assert(number(streams->items[0], "type") == 111);
    assert(number(streams->items[0], "dataPort") == 7001);
    drop(response);
    close(accepted);
    close(client);
    cw_close_owner(listener->epoch, listener->server_fd);
    release_cf(listener->session);
    free(listener);
    pending_listener = NULL;
    /* A second session must fail cleanly if its worker cannot be created. */
    thread_failure = 1;
    assert(start_passive_listener(&port, zero, zero, 0, session) != 0);
    assert(session->refs == 1);
    drop(session);
    assert(!live);
    puts("PORSCHE_LISTENER_PASS actual IPv6 TCP connection, fixed firewall-permitted port, matching SETUP dataPort, failure cleanup");
    return 0;
}
