#ifndef CW_PORSCHE_DM_H
#define CW_PORSCHE_DM_H
#include <stddef.h>
#include <stdint.h>
typedef struct {
    unsigned width, height;
    unsigned id; /* dmdt report index; NOT a backend display ID. */
    int context;
} cw_display;
uint64_t cw_monotonic_ms(void);
int cw_dm_query(const char *root, const char *command, char *text, size_t capacity);
int cw_dm_display(const char *text, cw_display *display);
int cw_dm_layer(const char *text, unsigned id, unsigned width, unsigned height, int present);
/* MU1417 binding: verified production configuration maps index 1 to backend 4. */
int cw_dm_backend_id(unsigned report_index, unsigned *backend_id);
int cw_dm_switch(const char *root, unsigned display_id, unsigned context);
/* -1 invalid report; 0 absent/empty; 1 exactly the requested layer; 2 occupied. */
int cw_dm_context_state(const char *text, unsigned context, unsigned layer);
/* Same states, matching an exact ordered list of displayables. */
int cw_dm_context_layers(const char *text,unsigned context,const unsigned *layers,size_t count);
int cw_dm_declare(const char *root, unsigned context, unsigned layer);
/* Only the physically tested Porsche composition [78,33]. Requires an empty
 * or already owned context; ownership must be checked by the caller. */
int cw_dm_declare_overlay(const char *root);
int cw_map_context(unsigned context);
#endif
