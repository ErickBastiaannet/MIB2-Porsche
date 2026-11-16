#ifndef CW_PORSCHE_RGI_H
#define CW_PORSCHE_RGI_H
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint16_t position;
    uint16_t direction;
    uint8_t type, marking_left, marking_right, description, guidance;
    uint8_t angle_count;
    uint16_t angles[16];
} cw_rgi_lane;

typedef struct {
    uint8_t valid, main_element, direction;
    uint8_t occupied, type, junction, driving, linked_lane_known;
    uint16_t wire_id, linked_lane;
    uint8_t junction_angle_count;
    int16_t junction_angles[16];
    int16_t angle;
    uint32_t step_distance;
    uint64_t touched;
    int8_t z_level;
    char description[97];
    char after_road[97];
    char exit_info[97];
} cw_rgi_maneuver;

typedef struct {
    uint8_t occupied, valid, count;
    uint16_t wire_id;
    uint64_t touched;
    cw_rgi_lane lanes[12];
} cw_rgi_lane_event;

typedef struct {
    uint64_t epoch;
    int active;
    uint32_t distance;
    uint32_t distance_remaining;
    uint64_t time_remaining, eta, time_remaining_at;
    uint8_t eta_valid, maneuver_state, maneuver_count_known;
    uint16_t maneuver_count;
    uint8_t bargraph, main_element, direction;
    uint8_t lane_visibility;
    int8_t z_level;
    cw_rgi_lane lanes[12];
    uint8_t lane_count;
    uint16_t maneuver_index;
    uint8_t maneuver_selected;
    uint8_t distance_valid, lane_selected;
    uint16_t lane_index;
    uint64_t cache_clock;
    cw_rgi_maneuver maneuvers[64];
    cw_rgi_lane_event lane_events[32];
    char current_road[97];
    char turn_to[97];
    char destination[97];
    char source_name[97];
    uint8_t source_support_known, source_supports_rg, visible_in_app;
    uint8_t route_state, end_reason, zero_pending;
    uint64_t zero_deadline_ms, arrival_deadline_ms;
} cw_rgi_state;

enum { CW_RGI_END_NONE=0, CW_RGI_END_STOP=1, CW_RGI_END_ARRIVAL=2, CW_RGI_END_DISCONNECT=3 };
uint64_t cw_rgi_now_ms(void);
int cw_rgi_tick(cw_rgi_state *state,uint64_t now_ms);
void cw_rgi_end(cw_rgi_state *state,int reason);
int cw_rgi_consume_at(cw_rgi_state *state,const uint8_t *message,size_t length,uint64_t now_ms);

int cw_rgi_consume(cw_rgi_state *state, const uint8_t *message, size_t length);
size_t cw_rgi_component(uint8_t *output, size_t capacity, uint16_t component_id);
size_t cw_rgi_patch_identify(uint8_t *output, size_t capacity,
                             const uint8_t *message, size_t length,
                             uint16_t component_id);
size_t cw_rgi_start(uint8_t *output, size_t capacity, uint16_t component_id);
int cw_rgi_publish(const cw_rgi_state *state, const char *path);

#endif
