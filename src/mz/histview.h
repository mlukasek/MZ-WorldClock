/* The historic look on the text screen (MZ-700 mode): data from data/historic.txt (build/gen/historic.c). */
#ifndef WC_HISTVIEW_H
#define WC_HISTVIEW_H

#include <stdint.h>
#include "wctime.h"

void hist_draw(void);                              /* the static screen and the title of this machine */
void hist_update(wc_time_t utc, uint8_t colon_on); /* once per frame: clocks, colons, seconds bar */

#endif
