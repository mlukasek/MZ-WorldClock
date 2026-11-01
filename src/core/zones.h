/* Time zones the user can choose as home (the zone of the entered time and of the RTC). */
#ifndef WC_ZONES_H
#define WC_ZONES_H

#include <stdint.h>

struct wc_zone {
    const char *name;        /* upper case, at most 10 characters */
    int16_t std_minutes;     /* standard time offset from UTC */
    uint8_t dst;             /* DST_... (wctime.h) */
};

extern const struct wc_zone wc_zones[];
extern const uint8_t wc_zone_count;

#define ZONE_PRAGUE 2        /* default home on a European machine */
#define ZONE_TOKYO 9         /* default home on a Japanese machine */

#endif
