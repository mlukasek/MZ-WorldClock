/* Portable time library of MZ-WorldClock: calendar, UTC seconds since 2000-01-01, time zones with today's
 * daylight saving time rules. No hardware access; tested by tests/core against Python's zoneinfo. */
#ifndef WC_WCTIME_H
#define WC_WCTIME_H

#include <stdint.h>

typedef uint32_t wc_time_t;          /* seconds since 2000-01-01 00:00:00 (UTC or local) */

#define WC_YEAR_MIN 2000
#define WC_YEAR_MAX 2099

/* Daylight saving time rules (the current rules, applied to every year) */
#define DST_NONE 0
#define DST_EU 1      /* last Sunday of March 01:00 UTC - last Sunday of October 01:00 UTC */
#define DST_US 2      /* second Sunday of March 02:00 local - first Sunday of November 02:00 local */
#define DST_AU 3      /* first Sunday of October 02:00 local - first Sunday of April 03:00 local (south) */

struct wc_tm {
    uint16_t year;
    uint8_t month;                   /* 1-12 */
    uint8_t day;                     /* 1-31 */
    uint8_t wday;                    /* 0 = Sunday */
    uint8_t hour, min, sec;
};

uint8_t wc_days_in_month(uint16_t year, uint8_t month);
uint16_t wc_days_from_date(uint16_t year, uint8_t month, uint8_t day);   /* days since 2000-01-01 */
wc_time_t wc_make(const struct wc_tm *tm);                                 /* tm->wday is ignored */
void wc_split(wc_time_t t, struct wc_tm *tm);

/* Offset of local time from UTC in minutes at the UTC time `utc` */
int16_t wc_offset(wc_time_t utc, int16_t std_minutes, uint8_t rule);
wc_time_t wc_to_local(wc_time_t utc, int16_t std_minutes, uint8_t rule);
/* Local time -> UTC. The repeated hour at the end of DST is taken as DST (the earlier instant); a time in
 * the skipped hour at its start is taken as standard time. */
wc_time_t wc_to_utc(wc_time_t local, int16_t std_minutes, uint8_t rule);

#endif
