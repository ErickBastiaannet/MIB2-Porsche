#ifndef CW_PORSCHE_JAR_H
#define CW_PORSCHE_JAR_H
/* 1: no overlapping override; 0: conflict, invalid, or unreadable archive. */
int cw_jar_compatible(const char *path);
#endif
