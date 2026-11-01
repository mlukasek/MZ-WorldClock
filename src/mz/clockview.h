/* The clock screens of the MZ-800 (key G after the map): a big digital clock and an analog one, both with the
 * 9 cities. Layout and tables: tools/mkmodern.py; reference renderer: tools/clockref.py. */
#ifndef WC_CLOCKVIEW_H
#define WC_CLOCKVIEW_H

#include <stdint.h>
#include "wctime.h"

/* Into MZ-800 mode (16 colours with the VRAM extension, else 4) and draw everything (leave with gfx_end()) */
void clk_enter(uint8_t analog, uint8_t home, wc_time_t utc);
void clk_update(wc_time_t utc);              /* once per frame */

#endif
