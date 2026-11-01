/* The clock from the Unicard RTC: set at the start, kept in step every 10 minutes, written when the user sets
 * the time. The card keeps local time of the home zone. */
#ifndef WC_RTCSYNC_H
#define WC_RTCSYNC_H

#include <stdint.h>
#include "wctime.h"

extern uint8_t rtc_present;                    /* a card answered at the start (set by main) */

uint8_t rtc_start(uint8_t zone);               /* 1 when the clock was set from the card (up to 2 s) */
void rtc_poll(wc_time_t now, uint8_t zone);    /* once per frame */
void rtc_manual_set(uint8_t zone);             /* after the dialog set the clock: write the card */

#endif
