/* The modern look of the MZ-800 (320x200, 4 colours): the world map with day and night, the cities, the home
 * zone, the home time and the seconds bar. Data and the reference renderer: tools/mkmodern.py, tools/modref.py. */
#ifndef WC_MODVIEW_H
#define WC_MODVIEW_H

#include <stdint.h>
#include "wctime.h"

void mod_enter(uint8_t home, uint8_t view, wc_time_t utc);   /* into MZ-800 mode and draw everything */
void mod_leave(void);                                         /* back to MZ-700 mode */
void mod_update(wc_time_t utc);                               /* once per frame */

#endif
