/* Time base in the 8253 without interrupts: CTC1 divides HSYNC to 1 Hz, CTC2 counts the seconds (MZ-700
 * memory map). The clock is UTC seconds since 2000 plus the fraction of the current second. */
#ifndef WC_TIMEBASE_H
#define WC_TIMEBASE_H

#include <stdint.h>
#include "wctime.h"

uint16_t tb_measure_lines(void);           /* lines per frame (312 PAL, 262 NTSC) */
void tb_init(uint16_t line_hz);            /* start the 1 Hz divider and the seconds counter */
void tb_wait_frame(void);                  /* until the vertical blanking starts */

void clock_set(wc_time_t utc);             /* the time is `utc` now (start of a second) */
wc_time_t clock_now(uint16_t *frac);       /* UTC now; frac = lines since the second started */
extern uint16_t tb_line_hz;
extern wc_time_t tb_last_utc;               /* the last clock_now(), for the emulator tests */
extern uint16_t tb_last_frac;

#endif
