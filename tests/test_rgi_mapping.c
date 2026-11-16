/* Expected values exported from luka-dev/mib2q-carplay-rgi
 * 21f501611b0b28dbdeb2849e8443ce90ec9517ff ManeuverMapper.java.
 * Compile this translation unit alone: the static mapper is exercised against
 * an independent reference oracle, not against a duplicate implementation. */
#include "../native/porsche_rgi.c"
#include <assert.h>
int main(int argc,char **argv) {
    FILE *f;unsigned type,junction,side,main,direction,count=0,failures=0;int angle;
    assert(argc==2);f=fopen(argv[1],"r");assert(f);
    while(fscanf(f,"%u %d %u %u %u %u",&type,&angle,&junction,&side,&main,&direction)==6){
        uint8_t actual_main,actual_direction;
        map_maneuver(type,angle,junction,side,&actual_main,&actual_direction);
        if(actual_main!=main||actual_direction!=direction){
            if(failures<12)fprintf(stderr,"mapping type=%u angle=%d junction=%u side=%u expected=%u/%u actual=%u/%u\n",type,angle,junction,side,main,direction,actual_main,actual_direction);
            failures++;
        }
        count++;
    }
    fclose(f);assert(count==4536);
    if(failures){fprintf(stderr,"%u mapping mismatches\n",failures);return 1;}
    printf("PORSCHE_REFERENCE_MAPPING_PASS %u cases\n",count);return 0;
}
