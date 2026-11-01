/* The real-time clock of the Unicard (and compatible cards: MZPico): ports 50h (command, status) and
 * 51h (data). The card keeps local time of the home zone, without zone or DST (docs/rozhodnuti.md). */
#ifndef WC_RTC_UNICARD_H
#define WC_RTC_UNICARD_H

#include <stdint.h>
#include "wctime.h"

uint8_t rtc_detect(void);                     /* 1 when a card answers REVD */
uint8_t rtc_read(struct wc_tm *tm);           /* 1 when the card has a valid date and time (2020-2099) */
uint8_t rtc_write(const struct wc_tm *tm);    /* 1 when the card took the date and time */

#endif
