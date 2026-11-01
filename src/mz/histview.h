/* The historic look on the text screen (MZ-700 mode): data from data/historic.txt (build/gen/historic.c). */
#ifndef WC_HISTVIEW_H
#define WC_HISTVIEW_H

#include <stdint.h>
#include "wctime.h"

#define VIEW_PACIFIC 0                             /* the period screen */
#define VIEW_ATLANTIC 1                            /* the continents swapped (key M) */
extern uint8_t hist_view;
extern uint8_t hist_hiragana;                      /* the hiragana title from own glyphs (MZ-800) */
/* The seconds bar in 1 s steps: draws / removes the half glyph over a bar cell (NULL: 2 s steps) */
extern void (*hist_half)(uint8_t cell, uint8_t on);
void hist_half_cgram(uint8_t cell, uint8_t on);    /* MZ-800: from the CG-RAM */

void hist_draw(void);                              /* the static screen of hist_view and the title */
void hist_update(wc_time_t utc, uint8_t colon_on); /* once per frame: clocks, colons, seconds bar */

#endif
