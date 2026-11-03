/* Serialize producer ownership across overlapping AirPlay reconnect threads. */
static pthread_mutex_t cw_owner_mutex = PTHREAD_MUTEX_INITIALIZER;
static uint32_t cw_owner_epoch;
static int cw_owner_server = -1, cw_owner_client = -1;

static uint32_t cw_claim(int server) {
    uint32_t epoch;
    pthread_mutex_lock(&cw_owner_mutex);
    if (cw_owner_server >= 0)
        shutdown(cw_owner_server, SHUT_RDWR);
    if (cw_owner_client >= 0)
        shutdown(cw_owner_client, SHUT_RDWR);
    if (++cw_owner_epoch == 0)
        ++cw_owner_epoch;
    epoch = cw_owner_epoch;
    cw_owner_server = server;
    cw_owner_client = -1;
    unlink(ALTSCREEN_READY_PATH);
    unlink(ALTSCREEN_BRIDGE_READY_PATH);
    pthread_mutex_unlock(&cw_owner_mutex);
    return epoch;
}

static int cw_current(uint32_t epoch) {
    int current;
    pthread_mutex_lock(&cw_owner_mutex);
    current = epoch == cw_owner_epoch;
    pthread_mutex_unlock(&cw_owner_mutex);
    return current;
}

static int cw_accept_owner(uint32_t epoch, int client) {
    int current;
    pthread_mutex_lock(&cw_owner_mutex);
    current = epoch == cw_owner_epoch;
    if (current)
        cw_owner_client = client;
    pthread_mutex_unlock(&cw_owner_mutex);
    return current;
}

static void cw_close_owner(uint32_t epoch, int fd) {
    pthread_mutex_lock(&cw_owner_mutex);
    if (epoch == cw_owner_epoch) {
        if (cw_owner_client == fd)
            cw_owner_client = -1;
        if (cw_owner_server == fd)
            cw_owner_server = -1;
    }
    if (fd >= 0)
        close(fd);
    pthread_mutex_unlock(&cw_owner_mutex);
}

static int cw_marker(uint32_t epoch, const char *path, int operation) {
    int result = -1;
    pthread_mutex_lock(&cw_owner_mutex);
    if (epoch == cw_owner_epoch) {
        if (operation == 0)
            result = unlink(path);
        else if (operation == 1)
            result = create_marker(path);
        else
            result = consume_marker(path);
    }
    pthread_mutex_unlock(&cw_owner_mutex);
    return result;
}

static AltFrameRing *cw_ring(uint32_t epoch) {
    AltFrameRing *ring = NULL;
    pthread_mutex_lock(&cw_owner_mutex);
    if (epoch == cw_owner_epoch)
        ring = create_forward_ring();
    pthread_mutex_unlock(&cw_owner_mutex);
    return ring;
}

static int cw_forward(uint32_t epoch, AltFrameRing *ring, uint16_t type, uint32_t source_sequence,
                      uint32_t flags, uint64_t timestamp, const uint8_t *data, size_t size) {
    int result = -1;
    pthread_mutex_lock(&cw_owner_mutex);
    if (epoch == cw_owner_epoch)
        result = forward_ring_message(ring, type, source_sequence, flags, timestamp, data, size);
    pthread_mutex_unlock(&cw_owner_mutex);
    return result;
}
