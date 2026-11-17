/* Opt-in only: production is unchanged unless the one-boot RAM marker exists. */
#ifndef CW_NAV_PRIORITY_GATE_H
#define CW_NAV_PRIORITY_GATE_H
#ifndef CW_NAV_PRIORITY_ROOT
#define CW_NAV_PRIORITY_ROOT "/ramdisk"
#endif
static int cw_nav_allowed_at(uint32_t producer, uint32_t now) {
    uint32_t state[4];
    if (access(CW_NAV_PRIORITY_ROOT "/cw-nav-priority.enabled", F_OK) != 0) return 1;
    return cw_wire_read(CW_NAV_PRIORITY_ROOT "/cw-nav-priority.v1", "CWNP1", state, 4) &&
        state[0] > 0 && state[1] <= now && now - state[1] <= 3 &&
        state[2] == 1 && producer > 1 && state[3] == producer;
}
#endif
