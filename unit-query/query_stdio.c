#include <stdio.h>
#include <unistd.h>

/* dmdt exits without normal stdio flushing on this firmware. Affect only the
 * short-lived diagnostic child; never inject into HMI/DisplayManager/dio. */
__attribute__((constructor))
static void cw_query_stdio(void) {
    (void)setvbuf(stdout, NULL, _IONBF, 0);
    (void)setvbuf(stderr, NULL, _IONBF, 0);
    (void)alarm(10);
}
