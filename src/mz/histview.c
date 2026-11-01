/* The historic look on the text screen (see histview.h).
 *
 * After a minute changes, the cities are recomputed one per call (a local time costs some tens of
 * thousands of T states), so the colons and the seconds bar never stop. The bar is full after 60 s: 30
 * cells of HIST_BAR_CHAR (the lower half of the cell), counted in halves of a cell. The CG-ROMs have no
 * glyph for half of it, so the MZ-700 steps by whole cells (2 s); with hist_half the own half glyph gives 1 s
 * steps: on the MZ-800 from its CG-RAM (set 1, the same code), on the MZ-1500 from its PCG. */
#include <string.h>
#include "histview.h"
#include "historic.h"
#include "machine.h"
#include "text700.h"
#include "hw.h"

#define COLON 0x4F

uint8_t hist_view;
uint8_t hist_hiragana;
void (*hist_half)(uint8_t cell, uint8_t on);

static uint32_t shown_minute;
static wc_time_t minute_utc;
static uint16_t dirty;                 /* bit i: clock i to redraw */
static uint8_t colon_shown;
static uint8_t bar_shown;

/* Screen offset of clock i in the current view */
static uint16_t clock_pos(uint8_t i)
{
    const struct hist_clock *c = &hist_clocks[i];

    return hist_view == VIEW_ATLANTIC ? c->row_atl * 40 + c->col_atl : c->row * 40 + c->col;
}

static void draw_clock(uint8_t i)
{
    const struct hist_clock *c = &hist_clocks[i];
    struct wc_tm tm;
    uint16_t p = clock_pos(i);

    wc_split(wc_to_local(minute_utc, c->utc_minutes, c->dst), &tm);
    VRAM_TEXT[p] = 0x20 + tm.hour / 10;
    VRAM_TEXT[p + 1] = 0x20 + tm.hour % 10;
    VRAM_TEXT[p + 2] = colon_shown == 1 ? COLON : 0x00;
    VRAM_TEXT[p + 3] = 0x20 + tm.min / 10;
    VRAM_TEXT[p + 4] = 0x20 + tm.min % 10;
    memset((uint8_t *)VRAM_ATTR + p, HIST_CLOCK_ATTR, 5);
}

/* The half cell from the MZ-800's CG-RAM: the bar character in set 1 is the own half glyph */
void hist_half_cgram(uint8_t cell, uint8_t on)
{
    if (on) {
        VRAM_TEXT[HIST_BAR_ROW * 40 + HIST_BAR_COL + cell] = HIST_BAR_CHAR;
        VRAM_ATTR[HIST_BAR_ROW * 40 + HIST_BAR_COL + cell] = HIST_BAR_ATTR | 0x80;
    }
}

/* The screen is built here and copied to the VRAM at once (on the MZ-700 every VRAM access during the
   picture waits for the line's blanking, so it is not the place to compute in) */
static uint8_t scr[2000];

void hist_draw(void)
{
    uint8_t r, c, cs, b, s;
    const uint8_t *top, *bot;
    uint8_t *ch, *at;
    const struct hist_item *it;

    memset(scr, 0, 2000);
    /* the map: text rows 2-21 from block rows 4-43 (two mask rows of 10 bytes per text row; text column cs
       is bits 2cs, 2cs+1 of both); the Atlantic view takes its columns from hist_atl_col */
    for (r = 2; r < 22; ++r) {
        top = hist_map + (uint16_t)(2 * r - 4) * 10;
        bot = top + 10;
        ch = scr + (uint16_t)r * 40;
        at = ch + 1000;
        for (c = 0; c < 40; ++c) {
            cs = hist_view == VIEW_ATLANTIC ? hist_atl_col[c] : c;
            if (cs >= 40)
                continue;
            s = (cs & 3) << 1;
            b = ((top[cs >> 2] >> s) & 3) | ((bot[cs >> 2] >> s) & 3) << 2;
            if (b) {
                ch[c] = 0xF0 | b;
                at[c] = 0x10;
            }
        }
    }
    /* the title line, the ruler, the names */
    for (it = hist_items; it < hist_items + HIST_ITEMS; ++it) {
        ch = scr + (hist_view == VIEW_ATLANTIC ? (uint16_t)it->row_atl * 40 + it->col_atl
                                                : (uint16_t)it->row * 40 + it->col);
        memcpy(ch, it->codes, it->len);
        memset(ch + 1000, it->attr, it->len);
    }
    if (mach.jp || hist_hiragana) {
        memcpy(scr, hist_title_jp_chars, 40);
        memcpy(scr + 1000, hist_title_jp_attrs, 40);
    } else {
        memcpy(scr, hist_title_eu_chars, 40);
        memcpy(scr + 1000, hist_title_eu_attrs, 40);
    }
    memcpy((uint8_t *)VRAM_TEXT, scr, 1000);
    memcpy((uint8_t *)VRAM_ATTR, scr + 1000, 1000);
    if (bar_shown & 1)
        hist_half(bar_shown >> 1, 0);    /* the screen copy has an empty bar */
    shown_minute = 0xFFFFFFFFUL;
    colon_shown = 2;
    bar_shown = 0;
}

void hist_update(wc_time_t utc, uint8_t colon_on)
{
    uint32_t minute = utc / 60;
    uint8_t sec = (uint8_t)(utc - minute * 60);
    uint8_t i, halves;
    volatile uint8_t *bar = VRAM_TEXT + HIST_BAR_ROW * 40 + HIST_BAR_COL;
    volatile uint8_t *bar_attr = VRAM_ATTR + HIST_BAR_ROW * 40 + HIST_BAR_COL;

    if (minute != shown_minute) {
        shown_minute = minute;
        minute_utc = minute * 60;
        dirty = (1u << HIST_CLOCKS) - 1;
    }
    if (dirty) {
        for (i = 0; !((dirty >> i) & 1); ++i)
            ;
        dirty &= ~(1u << i);
        draw_clock(i);
    }
    colon_on = colon_on ? 1 : 0;
    if (colon_on != colon_shown) {
        colon_shown = colon_on;
        for (i = 0; i < HIST_CLOCKS; ++i)
            VRAM_TEXT[clock_pos(i) + 2] = colon_on ? COLON : 0x00;
    }
    halves = hist_half ? sec + 1 : (sec + 1) & 0xFE;   /* full during the last second of the minute */
    if (halves != bar_shown) {
        if (bar_shown & 1)
            hist_half(bar_shown >> 1, 0);
        if (halves < bar_shown) {
            memset((uint8_t *)bar, 0x00, HIST_BAR_CELLS);
            memset((uint8_t *)bar_attr, HIST_BAR_ATTR, HIST_BAR_CELLS);
            bar_shown = 0;
        }
        for (i = bar_shown >> 1; i < (halves >> 1); ++i) {
            bar[i] = HIST_BAR_CHAR;
            bar_attr[i] = HIST_BAR_ATTR;
        }
        if (halves & 1)
            hist_half(halves >> 1, 1);
        bar_shown = halves;
    }
}
