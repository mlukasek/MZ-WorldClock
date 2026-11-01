/* The dialog that sets the date, the time and the home time zone (text screen, MZ-700 mode). */
#ifndef WC_SETUP_H
#define WC_SETUP_H

#include <stdint.h>

/* Returns 1 when a time was set (clock_set called), 0 when cancelled. `have_time`: the clock runs, the
 * dialog starts with its time. */
uint8_t setup_run(uint8_t *zone, uint8_t have_time);

#endif
