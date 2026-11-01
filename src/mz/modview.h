/* The modern look of the MZ-800 (320x200, 4 colours): the world map with day and night, the cities, the home
 * zone, the home time and the seconds bar. Data and the reference renderer: tools/mkmodern.py, tools/modref.py. */
#ifndef WC_MODVIEW_H
#define WC_MODVIEW_H

#include <stdint.h>
#include "wctime.h"

/* Into MZ-800 mode and draw everything (leave with gfx_end()) */
void mod_enter(uint8_t home, uint8_t view, wc_time_t utc);
void mod_update(wc_time_t utc);                               /* once per frame */
void mod_prepare(uint8_t home);                               /* precompute for the home zone (optional) */

/* Shared with the clock screens (clockview.c). The texts are in one buffer, valid until the next call. */
const char *mod_city_hm(uint8_t city, wc_time_t utc);         /* the city's local HH:MM */
const char *mod_date_text(const struct wc_tm *tm);            /* DAY DD.MM.YYYY */
uint8_t mod_offset_text(int16_t minutes);                     /* UTC+h[:mm] into mod_text, its length */
extern char mod_text[16];
void mod_bar(uint8_t sec, uint8_t colour);                    /* the seconds bar; mapped */
void mod_ruler(uint8_t colour);                               /* its ruler; mapped */
void mod_sun(wc_time_t utc);                                  /* the sun for mod_day_at */
uint8_t mod_day_at(uint16_t x, uint8_t y);                    /* 1 = day at a point of the map (Pacific view) */

#endif
