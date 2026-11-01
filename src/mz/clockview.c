/* The clock screens of the MZ-800 (see clockview.h). The same integer arithmetic and drawing order as
 * tools/clockref.py, so tests/emu/run_modern.py can compare the VRAM planes byte for byte.
 *
 * Colours as on the period photos: the title cyan, the names red, the times yellow, the bar magenta, the ruler
 * green, the face blue. With the VRAM extension in 16 colours (planes I-IV, the palette identical, so the
 * colour numbers are IGRB), without it in 4: black, blue, light red, light yellow.
 *
 * Digital: HH:MM:SS 4x6 enlarged (only the changed digits are redrawn), the home zone and its offset, the 9
 * cities (the time light by day, blue by night), the seconds bar. Analog: a face (light blue by day, dark at
 * night at home), the hands every second: the old second hand is drawn over in the face colour, the numerals
 * and all hands again (no hand reaches the ticks); beside it the home time and the cities. The minute's work
 * (the sun, the cities, the date, the offset) is done when the minute changes. */
#include <string.h>
#include "clockview.h"
#include "modview.h"
#include "modern.h"
#include "gfx800.h"
#include "zones.h"

enum { C_TITLE, C_DIGITS, C_NAME, C_DAY, C_NIGHT, C_BAR, C_RULER, C_FACE_DAY, C_FACE_NIGHT, C_RIM, C_TICK,
       C_HAND, C_SECOND, C_N };
static const uint8_t col16[C_N] = {13, 14, 10, 14, 9, 11, 12, 9, 1, 2, 15, 14, 10};
static const uint8_t col4[C_N] = {3, 3, 2, 3, 1, 2, 1, 1, 0, 2, 3, 3, 2};
static const uint8_t pal16[4] = {0x00, 0x11, 0x22, 0x33};
static const uint8_t pal4[4] = {0x00, 0x11, 0x2A, 0x3E};
static const char *const numeral[4] = {"12", "3", "6", "9"};

static const uint8_t *col;
static uint8_t analog, home, face_day, hand_s, hand_m, hand_h, shown_mday, shown_sec;
static uint32_t shown_minute;
static char shown[9], now_text[9], line[41];

static void point(uint8_t len, uint8_t pos, int16_t *x, int16_t *y)
{
    uint8_t q = pos / 15, i = pos % 15;
    uint16_t s = clk_sin60[i], c = clk_sin60[15 - i], vx, vy, dx, dy;

    vx = (q & 1) ? c : s;
    vy = (q & 1) ? s : c;
    dx = ((((uint16_t)len * vx + 128) >> 8) * CLK_ASPECT_Q8 + 128) >> 8;
    dy = ((uint16_t)len * vy + 128) >> 8;
    *x = CLK_CX + (q >= 2 ? -(int16_t)dx : (int16_t)dx);
    *y = CLK_CY + (q == 0 || q == 3 ? -(int16_t)dy : (int16_t)dy);
}

static void hand(uint8_t pos, uint8_t len, uint8_t width, uint8_t colour)
{
    int16_t x, y;

    point(len, pos, &x, &y);
    gfx_line(CLK_CX, CLK_CY, x, y, colour, width);
}

static void second_hand(uint8_t pos, uint8_t colour)
{
    int16_t x0, y0, x1, y1;

    point(CLK_HAND_TAIL, pos < 30 ? pos + 30 : pos - 30, &x0, &y0);
    point(CLK_HAND_S, pos, &x1, &y1);
    gfx_line(x0, y0, x1, y1, colour, 1);
}

static void numerals(void)
{
    uint8_t k;
    int16_t x, y;

    for (k = 0; k < 4; ++k) {
        point(CLK_NUM_R, k * 15, &x, &y);
        gfx_ptext(x - 4 * (int16_t)strlen(numeral[k]), y - 4, numeral[k], col[C_TICK]);
    }
}

static void face(void)
{
    uint8_t dy, fc = col[face_day ? C_FACE_DAY : C_FACE_NIGHT], p, k;
    int16_t x0, y0, x1, y1;

    for (dy = CLK_RO;; --dy) {
        for (k = 0; k < 2; ++k) {
            y0 = k ? CLK_CY + dy : CLK_CY - dy;
            gfx_hspan(CLK_CX - clk_face_out[dy], CLK_CX + clk_face_out[dy], y0, col[C_RIM]);
            if (dy <= CLK_R)
                gfx_hspan(CLK_CX - clk_face_in[dy], CLK_CX + clk_face_in[dy], y0, fc);
            if (!dy)
                break;
        }
        if (!dy)
            break;
    }
    for (p = 0; p < 60; ++p) {
        if (p % 5) {
            point(CLK_TICK_DOT, p, &x0, &y0);
            gfx_hspan(x0, x0, y0, col[C_TICK]);
        } else {
            point(CLK_TICK_IN, p, &x0, &y0);
            point(CLK_TICK_OUT, p, &x1, &y1);
            gfx_line(x0, y0, x1, y1, col[C_TICK], 2);
        }
    }
    numerals();
    hand_s = 0xFF;                             /* nothing to draw over */
}

static void hands(const struct wc_tm *tm)
{
    uint8_t s = tm->sec, m = tm->min, h = (tm->hour % 12) * 5 + tm->min / 12, y;
    uint8_t fc = col[face_day ? C_FACE_DAY : C_FACE_NIGHT];

    if (hand_s != 0xFF) {
        second_hand(hand_s, fc);
        if (m != hand_m)
            hand(hand_m, CLK_HAND_M, 2, fc);
        if (h != hand_h)
            hand(hand_h, CLK_HAND_H, 3, fc);
        numerals();
    }
    hand(h, CLK_HAND_H, 3, col[C_HAND]);
    hand(m, CLK_HAND_M, 2, col[C_HAND]);
    second_hand(s, col[C_SECOND]);
    for (y = CLK_CY - 1; y <= CLK_CY + 1; ++y)
        gfx_hspan(CLK_CX - 2, CLK_CX + 2, y, col[C_HAND]);
    hand_s = s;
    hand_m = m;
    hand_h = h;
}

/* Everything that changes once a minute */
static void minute(wc_time_t utc, const struct wc_tm *tm)
{
    const struct wc_zone *w = &wc_zones[home];
    uint8_t i, n, k, bx, y, day;

    mod_sun(utc - tm->sec);                    /* the sun at the start of the minute, as on the map */
    if (tm->day != shown_mday) {
        shown_mday = tm->day;
        gfx_ctext(26, 0, mod_date_text(tm), col[C_TITLE], 1, 1);
    }
    n = (uint8_t)strlen(w->name);
    k = mod_offset_text(wc_offset(utc, w->std_minutes, w->dst));
    if (analog) {
        memset(line, ' ', 10);
        memcpy(line, mod_text, k);
        line[10] = 0;
        gfx_ctext(CLK_PANEL_BX, CLK_PANEL_OFF_Y, line, col[C_TITLE], 1, 1);
        day = mod_home_y[home] ? mod_day_at(mod_home_x[home], mod_home_y[home]) : 1;
        if (day != face_day) {
            face_day = day;
            face();
        }
    } else {                                   /* "NAME  UTC+h" centred */
        memset(line, ' ', 40);
        line[40] = 0;
        bx = (40 - n - 2 - k) / 2;
        memcpy(line + bx, w->name, n);
        memcpy(line + bx + n + 2, mod_text, k);
        gfx_ctext(0, CLK_DIG_HOME_Y, line, col[C_NAME], 1, 1);
    }
    for (i = 0; i < MOD_CITIES; ++i) {
        day = mod_day_at(mod_cities[i].x, mod_cities[i].y);
        if (analog) {
            bx = CLK_LIST_TBX;
            y = CLK_LIST_Y + i * CLK_LIST_DY;
        } else {
            bx = CLK_GRID_BX0 + (i % 3) * CLK_GRID_BXD;
            y = CLK_GRID_Y + (i / 3) * CLK_GRID_DY + 8;
        }
        gfx_ctext(bx, y, mod_city_hm(i, utc), col[day ? C_DAY : C_NIGHT], 1, 1);
    }
}

static void second(wc_time_t utc)
{
    const struct wc_zone *w = &wc_zones[home];
    struct wc_tm tm;
    uint8_t i;
    char c[2];

    shown_sec = utc % 60;
    wc_split(wc_to_local(utc, w->std_minutes, w->dst), &tm);
    if (utc / 60 != shown_minute) {
        shown_minute = utc / 60;
        minute(utc, &tm);
    }
    now_text[0] = '0' + tm.hour / 10;
    now_text[1] = '0' + tm.hour % 10;
    now_text[2] = ':';
    now_text[3] = '0' + tm.min / 10;
    now_text[4] = '0' + tm.min % 10;
    now_text[5] = ':';
    now_text[6] = '0' + tm.sec / 10;
    now_text[7] = '0' + tm.sec % 10;
    c[1] = 0;
    for (i = 0; i < 8; ++i) {
        if (now_text[i] == shown[i])
            continue;
        shown[i] = c[0] = now_text[i];
        if (analog)
            gfx_ctext(CLK_PANEL_BX + 2 * i, CLK_PANEL_TIME_Y, c, col[C_DIGITS], 2, 2);
        else
            gfx_ctext(CLK_DIG_BX + 4 * i, CLK_DIG_Y, c, col[C_DIGITS], 4, 6);
    }
    if (analog)
        hands(&tm);
    else
        mod_bar(tm.sec, col[C_BAR]);
}

void clk_enter(uint8_t an, uint8_t h, wc_time_t utc)
{
    uint8_t i, y;

    analog = an;
    home = h;
    col = gfx_begin(pal4, pal16) ? col16 : col4;
    gfx_map();
    gfx_ctext(0, 0, "*** WORLD CLOCK ***", col[C_TITLE], 1, 1);
    for (i = 0; i < MOD_CITIES; ++i) {         /* the city names */
        y = analog ? CLK_LIST_Y + i * CLK_LIST_DY : CLK_GRID_Y + (i / 3) * CLK_GRID_DY;
        gfx_ctext(analog ? CLK_PANEL_BX : CLK_GRID_BX0 + (i % 3) * CLK_GRID_BXD, y, mod_cities[i].name,
                  col[C_NAME], 1, 1);
    }
    if (analog) {
        gfx_ctext(CLK_PANEL_BX, CLK_PANEL_NAME_Y, wc_zones[home].name, col[C_NAME], 1, 1);
        face_day = 0xFF;                       /* the face is drawn by the first minute() */
    } else {
        mod_ruler(col[C_RULER]);
    }
    memset(shown, 0, sizeof(shown));
    shown_minute = 0xFFFFFFFFUL;
    shown_mday = 0;
    second(utc);
    gfx_unmap();
}

void clk_update(wc_time_t utc)
{
    if (utc % 60 == shown_sec)
        return;
    gfx_map();
    second(utc);
    gfx_unmap();
}
