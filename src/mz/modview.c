/* The modern look of the MZ-800 (see modview.h). The same integer arithmetic as tools/mkmodern.py and
 * tools/modref.py, so tests/emu/run_modern.py can compare the VRAM planes byte for byte.
 *
 * A map row: the land (RLE) and the day (an interval from the subsolar point and the row's latitude) give
 * plane I = sea and day, plane II = land and (day or the night dither). Over it, in this order: the dotted
 * border of the home zone, the city markers, the labels (name over HH:MM, black shadow). A rectangle of the map
 * can be redrawn alone (render), which redraws whatever lies over it. The Atlantic view is the same map
 * rotated by MOD_ATL_SHIFT pixels (whole bytes).
 *
 * When a minute changes, the rows whose day interval moved are redrawn a few per frame, and the clocks one
 * city per frame, so the seconds go on. */
#include <string.h>
#include "modview.h"
#include "modern.h"
#include "gfx800.h"
#include "hw.h"
#include "text700.h"
#include "zones.h"

#define W 320
#define ROWS_PER_FRAME 4

static const char *const day_name[7] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};

/* The colours of the texts, the bar and the ruler: with the VRAM extension 16 colours in the tones of the
   period screen (IGRB; 0-3 go through the palette, i.e. the map's own colours), else the 4 of the map */
enum { M_TITLE, M_NAME, M_TIME, M_BAR, M_RULER, M_N };
static const uint8_t mcol16[M_N] = {13, 10, 14, 11, 12};
static const uint8_t mcol4[M_N] = {3, 3, 3, 3, 2};
static const uint8_t *col;

static uint8_t home, shift;            /* shift: the view's rotation in bytes */
static uint16_t yday;
static int16_t tand;
static uint16_t x16;
static uint16_t d_start[MOD_MAP_H], d_len[MOD_MAP_H];
/* The caches below are keyed in BSS (zeroed by crt0, also when the program is run again without loading):
   0 = empty. */
static uint8_t half[MOD_MAP_H];         /* half-width of the day per row, for the day half_yday - 1 */
static uint16_t half_yday;
static uint8_t dirty[MOD_MAP_H / 8];
static uint16_t dirty_clocks;
static uint32_t shown_minute;
static uint8_t shown_sec, shown_mday;
static uint8_t pl1[40], pl2[40];
static uint8_t zmask[3][MOD_ZONE_W / 8];
char mod_text[16];
/* the border cells of the home zone (cell column), cell row by cell row; computed once per home zone */
static uint8_t border_cx[MOD_BORDER_MAX];
static uint16_t border_start[MOD_ZONE_H + 1];
static uint8_t border_home;            /* the home they belong to, + 1 */

/* floor(v / 2^n), as Python's >> */
static int32_t fshr(int32_t v, uint8_t n)
{
    return v >= 0 ? v >> n : -((-v + (1L << n) - 1) >> n);
}

static void set_bits(uint8_t *b, uint16_t x, uint16_t n)
{
    uint8_t *p = b + (x >> 3);
    uint8_t s = x & 7, k;

    if (!n)
        return;
    if (s) {
        k = 8 - s;
        if (n < k) {
            *p |= (uint8_t)(((1 << n) - 1) << s);
            return;
        }
        *p++ |= (uint8_t)(0xFF << s);
        n -= k;
    }
    for (; n >= 8; n -= 8)
        *p++ = 0xFF;
    if (n)
        *p |= (uint8_t)((1 << n) - 1);
}

/* Bits [x, x + n) of a 320-pixel row, wrapping at the right edge */
static void set_cyc(uint8_t *b, uint16_t x, uint16_t n)
{
    if (x + n <= W) {
        set_bits(b, x, n);
    } else {
        set_bits(b, x, W - x);
        set_bits(b, 0, x + n - W);
    }
}

/* The land of map row y into row_land, in screen order (the view rotated by `shift` bytes) */
static void land_row(uint8_t y)
{
    land_decode(mod_land_rle + mod_land_idx[y]);
    if (shift) {                               /* rotate right by `shift` bytes; pl1 is free here */
        memcpy(pl1, row_land, 40);
        memcpy(row_land + shift, pl1, 40 - shift);
        memcpy(row_land, pl1 + 40 - shift, shift);
    }
}

/* The day of map row y into row_day, in screen order */
static void day_row(uint8_t y)
{
    uint16_t s = d_start[y] + shift * 8, n = d_len[y];

    if (n >= W) {
        memset(row_day, 0xFF, 40);
        return;
    }
    memset(row_day, 0, 40);
    if (s >= W)
        s -= W;
    set_cyc(row_day, s, n);
}

/* Bit mask (160 bits) of the cells of zone z in zone row cy */
static void zone_mask(uint8_t cy, uint8_t z, uint8_t *out)
{
    const uint8_t *p = mod_zone_rle + mod_zone_idx[cy];
    uint8_t x;

    memset(out, 0, MOD_ZONE_W / 8);
    for (x = 0; x < MOD_ZONE_W; x += p[1], p += 2)
        if (p[0] == z)
            set_bits(out, x, p[1]);
}

#define ZBIT(m, x) ((m)[(x) >> 3] & (1 << ((x) & 7)))

/* The border cells of the home zone: cells of the zone with a 4-neighbour outside it or outside the map */
static void border_build(void)
{
    uint8_t *prev = zmask[0], *cur = zmask[1], *next = zmask[2], *t;
    uint8_t cy, cx, x, len, z = mod_home_zone[home];
    const uint8_t *p;
    uint16_t n = 0;

    if (border_home == home + 1)
        return;
    border_home = home + 1;
    zone_mask(0, z, cur);
    zone_mask(1, z, next);
    for (cy = 0; cy < MOD_ZONE_H; ++cy) {
        border_start[cy] = n;
        /* only the runs of the zone in this row: their ends border on another zone (runs are maximal) */
        p = mod_zone_rle + mod_zone_idx[cy];
        for (x = 0; x < MOD_ZONE_W; x += len, p += 2) {
            len = p[1];
            if (p[0] != z)
                continue;
            for (cx = x; cx < x + len; ++cx) {
                if (cx != x && cx != x + len - 1 && cy && cy + 1 < MOD_ZONE_H && ZBIT(prev, cx) && ZBIT(next, cx))
                    continue;
                if (n < MOD_BORDER_MAX)
                    border_cx[n++] = cx;
            }
        }
        t = prev;
        prev = cur;
        cur = next;
        next = t;
        if (cy + 2 < MOD_ZONE_H)
            zone_mask(cy + 2, z, next);
    }
    border_start[MOD_ZONE_H] = n;
}

/* The subsolar point and the declination at `utc` */
static void sun(wc_time_t utc)
{
    struct wc_tm tm;
    uint8_t i, f;
    int16_t eot;
    int32_t t, q, r;

    wc_split(utc, &tm);
    yday = wc_days_from_date(tm.year, tm.month, tm.day) - wc_days_from_date(tm.year, 1, 1);
    i = yday >> 2;
    f = yday & 3;
    eot = mod_eot[i] + (int16_t)fshr((int32_t)(mod_eot[i + 1] - mod_eot[i]) * f, 2);
    tand = mod_tand[i] + (int16_t)fshr((int32_t)(mod_tand[i + 1] - mod_tand[i]) * f, 2);
    t = (int32_t)tm.hour * 3600 + (uint16_t)(tm.min * 60 + tm.sec) + eot;
    q = t >= 0 ? t * 16 / 270 : -((-t * 16 + 269) / 270);
    r = (MOD_X16_NOON - q) % (W * 16);
    if (r < 0)
        r += W * 16;
    x16 = (uint16_t)r;
    /* the half-width of the day depends only on the declination: once a day for all rows. 0 = night all
       day, W / 2 = day all day (no other row gets these values: acos(255/256) is 4 pixels) */
    if (half_yday != yday + 1) {
        half_yday = yday + 1;
        for (i = 0; i < MOD_MAP_H; ++i) {
            t = -fshr((int32_t)mod_tanlat[i] * tand, 15);
            half[i] = t >= 256 ? 0 : t <= -256 ? W / 2 : t >= 0 ? mod_acos[t] : W / 2 - mod_acos[-t];
        }
    }
}

/* The day interval of map row y; 1 when it changed */
static uint8_t interval(uint8_t y)
{
    uint8_t h = half[y];
    int16_t s;
    uint16_t start = 0, len = 0;

    if (h >= W / 2) {
        len = W;
    } else if (h) {
        s = (int16_t)(x16 >> 4) - h;
        if (s < 0)
            s += W;
        start = (uint16_t)s;
        len = 2 * h;
    }
    if (start == d_start[y] && len == d_len[y])
        return 0;
    d_start[y] = start;
    d_len[y] = len;
    return 1;
}

static char *two(char *p, uint8_t v)
{
    p[0] = '0' + v / 10;
    p[1] = '0' + v % 10;
    return p + 2;
}

const char *mod_city_hm(uint8_t i, wc_time_t utc)
{
    struct wc_tm tm;

    wc_split(wc_to_local(utc, mod_cities[i].std_minutes, mod_cities[i].dst), &tm);
    two(mod_text, tm.hour);
    mod_text[2] = ':';
    two(mod_text + 3, tm.min);
    mod_text[5] = 0;
    return mod_text;
}

const char *mod_date_text(const struct wc_tm *tm)
{
    memcpy(mod_text, day_name[tm->wday], 3);
    mod_text[3] = ' ';
    two(mod_text + 4, tm->day);
    mod_text[6] = '.';
    two(mod_text + 7, tm->month);
    mod_text[9] = '.';
    two(mod_text + 10, tm->year / 100);
    two(mod_text + 12, tm->year % 100);
    mod_text[14] = 0;
    return mod_text;
}

uint8_t mod_offset_text(int16_t off)
{
    uint8_t k = 3;

    memcpy(mod_text, "UTC", 3);
    mod_text[k++] = off < 0 ? '-' : '+';
    if (off < 0)
        off = -off;
    if (off / 60 >= 10)
        mod_text[k++] = '0' + off / 600;
    mod_text[k++] = '0' + (off / 60) % 10;
    if (off % 60) {
        mod_text[k++] = ':';
        two(mod_text + k, off % 60);
        k += 2;
    }
    mod_text[k] = 0;
    return k;
}

void mod_sun(wc_time_t utc)
{
    sun(utc);
}

uint8_t mod_day_at(uint16_t x, uint8_t sy)
{
    uint8_t h = half[sy - MOD_MAP_Y];
    int16_t s;

    if (h >= W / 2)
        return 1;
    if (!h)
        return 0;
    s = (int16_t)(x16 >> 4) - h;
    if (s < 0)
        s += W;
    s = (int16_t)x - s;
    if (s < 0)
        s += W;
    return (uint16_t)s < 2 * h;
}

static void marker(uint16_t x, uint8_t y, uint8_t big, uint8_t y0, uint8_t y1, uint8_t c0, uint8_t c1)
{
    static const int8_t dx[9] = {0, 1, -1, 0, 0, 2, -2, 0, 0};
    static const int8_t dy[9] = {0, 0, 0, 1, -1, 0, 0, 2, -2};
    uint8_t k, py;
    int16_t px;

    for (k = 0; k < (big ? 9 : 5); ++k) {
        px = (int16_t)x + dx[k];
        py = y + dy[k];
        if (px < 0 || px >= W || py < y0 || py >= y1 || (px >> 3) < c0 || (px >> 3) >= c1)
            continue;
        gfx_plot((uint16_t)px, py);
    }
}

/* The home zone border in map rows [y0, y1), pixels [xlo, xhi): a dot on the top-left pixel of each border
   cell. A function of its own and compared in pixels: inside render() zsdcc -SO3 --opt-code-size generated
   wrong code for it (docs/vyvoj.md). */
static void border_dots(uint8_t y0, uint8_t y1, uint16_t xlo, uint16_t xhi)
{
    uint8_t y = y0 + (y0 & 1);
    uint16_t k, end, x;

    for (; y < y1; y += 2) {
        k = border_start[y >> 1];
        end = border_start[(y >> 1) + 1];
        for (; k < end; ++k) {
            x = (uint16_t)border_cx[k] * 2 + shift * 8;
            if (x >= W)
                x -= W;
            if (x >= xlo && x < xhi)
                gfx_plot(x, MOD_MAP_Y + y);
        }
    }
}

/* Redraw map rows [y0, y1) (map coordinates), screen byte columns [c0, c1); VRAM mapped */
static void render(uint8_t y0, uint8_t y1, uint8_t c0, uint8_t c1)
{
    uint8_t y, c, bx, dither, i, v;
    volatile uint8_t *row;
    uint16_t x;
    uint8_t sy0 = MOD_MAP_Y + y0, sy1 = MOD_MAP_Y + y1;
    const struct mod_city *ct;

    row = GFX_VRAM + (uint16_t)(MOD_MAP_Y + y0) * 40;
    for (y = y0; y < y1; ++y, row += 40) {
        land_row(y);
        day_row(y);
        dither = ((MOD_MAP_Y + y) & 1) ? 0x55 : 0xAA;
        if (c0 == 0 && c1 == 40) {          /* a whole row: hw.asm */
            row_dither = dither;
            row_out(row);
            continue;
        }
        for (c = c0; c < c1; ++c) {
            pl1[c] = ~row_land[c] & row_day[c];
            pl2[c] = row_land[c] & (row_day[c] | dither);
        }
        gfx_wf(WF_REPLACE(1));                 /* plane I; II (written next), III, IV cleared */
        for (c = c0; c < c1; ++c)
            row[c] = pl1[c];
        gfx_wf(WF_PLANE_II);
        for (c = c0; c < c1; ++c)
            row[c] = pl2[c];
    }
    border_dots(y0, y1, (uint16_t)c0 << 3, (uint16_t)c1 << 3);
    /* markers */
    for (i = 0; i < MOD_CITIES; ++i) {
        x = mod_cities[i].x + shift * 8;
        marker(x >= W ? x - W : x, mod_cities[i].y, 0, sy0, sy1, c0, c1);
    }
    if (mod_home_y[home]) {
        x = mod_home_x[home] + shift * 8;
        marker(x >= W ? x - W : x, mod_home_y[home], 1, sy0, sy1, c0, c1);
    }
    /* labels over the rectangle */
    for (i = 0; i < MOD_CITIES; ++i) {
        ct = &mod_cities[i];
        v = shift ? 1 : 0;
        bx = ct->lx[v];
        y = ct->ly[v];
        c = (uint8_t)strlen(ct->name);
        if (c < 5)
            c = 5;
        if (y + 18 <= sy0 || y >= sy1 || bx + c + 1 <= c0 || bx >= c1)
            continue;
        gfx_text(bx, y, ct->name, GFX_SHADOW | col[M_NAME]);
        gfx_text(bx, y + 8, mod_city_hm(i, (wc_time_t)shown_minute * 60), GFX_SHADOW | col[M_TIME]);
    }
}

static void home_line(wc_time_t utc)
{
    const struct wc_zone *w = &wc_zones[home];
    struct wc_tm tm;
    uint8_t n, k;

    wc_split(wc_to_local(utc, w->std_minutes, w->dst), &tm);
    memset(mod_text, ' ', 10);
    n = (uint8_t)strlen(w->name);
    memcpy(mod_text, w->name, n);
    mod_text[10] = 0;
    gfx_text(0, MOD_HOME_Y, mod_text, col[M_NAME]);
    mod_text[0] = ' ';
    two(mod_text + 1, tm.hour);
    mod_text[3] = ':';
    two(mod_text + 4, tm.min);
    mod_text[6] = ':';
    two(mod_text + 7, tm.sec);
    mod_text[9] = 0;
    gfx_text(10, MOD_HOME_Y, mod_text, col[M_TIME]);
    /* the offset right-aligned in 8 characters at byte column 32 */
    k = mod_offset_text(wc_offset(utc, w->std_minutes, w->dst));
    memmove(mod_text + 8 - k, mod_text, k);
    memset(mod_text, ' ', 8 - k);
    mod_text[8] = 0;
    gfx_text(32, MOD_HOME_Y, mod_text, col[M_TITLE]);
    /* the date in the title row: DAY DD.MM.YYYY at byte column 26 */
    if (tm.day != shown_mday) {
        shown_mday = tm.day;
        gfx_text(26, 0, mod_date_text(&tm), col[M_TITLE]);
    }
}

/* The seconds bar: 4 pixels per second, full in the last second of the minute (colour 3, 4 rows) */
void mod_bar(uint8_t sec, uint8_t colour)
{
    uint8_t r, c;
    uint16_t end = MOD_BAR_X + 4 * (sec + 1);
    volatile uint8_t *v;

    gfx_wf(WF_REPLACE(colour));
    for (r = 0; r < 4; ++r) {
        v = GFX_VRAM + (uint16_t)(MOD_BAR_Y + r) * 40;
        for (c = MOD_BAR_X >> 3; c < ((MOD_BAR_X + 240) >> 3); ++c) {
            if (((uint16_t)c << 3) + 8 <= end)
                v[c] = 0xFF;
            else if (((uint16_t)c << 3) >= end)
                v[c] = 0x00;
            else
                v[c] = (uint8_t)((1 << (end & 7)) - 1);
        }
    }
}

void mod_ruler(uint8_t colour)
{
    uint8_t c, k, y;
    uint16_t x;
    volatile uint8_t *v;

    gfx_wf(WF_REPLACE(colour));
    memset(pl2, 0, 40);
    set_bits(pl2, MOD_BAR_X - 1, 241);         /* the line, x 31-271 */
    v = GFX_VRAM + 199 * 40;
    for (c = 0; c < 40; ++c)
        v[c] = pl2[c];
    memset(pl2, 0, 40);
    for (k = 0; k < 7; ++k) {                  /* the posts and ticks every 40 pixels (10 s) */
        x = MOD_BAR_X - 1 + 40 * k;
        pl2[x >> 3] |= 1 << (x & 7);
    }
    for (y = MOD_RULER_Y; y < 199; ++y) {
        v = GFX_VRAM + (uint16_t)y * 40;
        for (c = 0; c < 40; ++c)
            v[c] = pl2[c];
    }
}

/* The border of the home zone is the slowest part of mod_enter (about 0.3 s): main.c does it beforehand,
   while the historic look is shown */
void mod_prepare(uint8_t h)
{
    home = h;
    border_build();
}

void mod_enter(uint8_t h, uint8_t view, wc_time_t utc)
{
    uint8_t y;

    home = h;
    shift = view ? MOD_ATL_SHIFT / 8 : 0;
    col = gfx_begin(mod_palette, mod_palette) ? mcol16 : mcol4;
    gfx_map();
    gfx_text(0, 0, "*** WORLD CLOCK ***", col[M_TITLE]);
    border_build();
    shown_minute = utc / 60;
    sun(utc);
    for (y = 0; y < MOD_MAP_H; ++y)
        interval(y);
    render(0, MOD_MAP_H, 0, 40);
    mod_ruler(col[M_RULER]);
    shown_mday = 0;
    home_line(utc);
    shown_sec = (uint8_t)(utc % 60);
    mod_bar(shown_sec, col[M_BAR]);
    memset(dirty, 0, sizeof(dirty));
    dirty_clocks = 0;
    gfx_unmap();
}

void mod_update(wc_time_t utc)
{
    uint32_t minute = utc / 60;
    uint8_t sec = (uint8_t)(utc - minute * 60);
    uint8_t y, n, i;

    gfx_map();
    if (minute != shown_minute) {
        shown_minute = minute;
        sun(minute * 60);
        for (y = 0; y < MOD_MAP_H; ++y)
            if (interval(y))
                dirty[y >> 3] |= 1 << (y & 7);
        dirty_clocks = (1u << MOD_CITIES) - 1;
    }
    for (y = 0, n = 0; y < MOD_MAP_H && n < ROWS_PER_FRAME; ++y) {
        if (dirty[y >> 3] & (1 << (y & 7))) {
            dirty[y >> 3] &= ~(1 << (y & 7));
            render(y, y + 1, 0, 40);
            ++n;
        }
    }
    if (dirty_clocks && !n) {                  /* a city's clock: its label area */
        for (i = 0; !((dirty_clocks >> i) & 1); ++i)
            ;
        dirty_clocks &= ~(1u << i);
        y = mod_cities[i].ly[shift ? 1 : 0] - MOD_MAP_Y;
        render(y + 8, y + 18, mod_cities[i].lx[shift ? 1 : 0], mod_cities[i].lx[shift ? 1 : 0] + 6);
    }
    if (sec != shown_sec) {
        shown_sec = sec;
        home_line(utc);
        mod_bar(sec, col[M_BAR]);
    }
    gfx_unmap();
}
