#ifndef CW_PORSCHE_PARSER_H
#define CW_PORSCHE_PARSER_H
/* Standalone decoder process only; preserve the vendor parser's presentation
 * order, replacing its hardware-output callback with a synchronous pixel copy. */
int cw_parser_start(void (*surface)(void *));
void cw_parser_stop(void);
#endif
