#ifndef CW_PORSCHE_RGI_H
#define CW_PORSCHE_RGI_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint16_t position;
    uint16_t direction;
    uint8_t type, marking_left, marking_right, description, guidance;
} cw_rgi_lane;

typedef struct {
    uint8_t valid, main_element, direction;
    int8_t z_level;
    char description[97];
    char after_road[97];
    char exit_info[97];
} cw_rgi_maneuver;

typedef struct {
    uint64_t epoch;
    int active;
    uint32_t distance;
    uint8_t bargraph, main_element, direction;
    int8_t z_level;
    cw_rgi_lane lanes[12];
    uint8_t lane_count;
    uint16_t maneuver_index;
    cw_rgi_maneuver maneuvers[64];
    char current_road[97];
    char turn_to[97];
} cw_rgi_state;

int cw_rgi_consume(cw_rgi_state *state, const uint8_t *message, size_t length);
size_t cw_rgi_component(uint8_t *output, size_t capacity, uint16_t component_id);
size_t cw_rgi_patch_identify(uint8_t *output, size_t capacity,
                             const uint8_t *message, size_t length,
                             uint16_t component_id);
size_t cw_rgi_start(uint8_t *output, size_t capacity, uint16_t component_id);
int cw_rgi_publish(const cw_rgi_state *state, const char *path);

#endif
