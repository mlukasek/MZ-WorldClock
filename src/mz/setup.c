/* The dialog that sets the date, the time and the home time zone (see setup.h).
 *
 *   DATE   2026-11-01        digits typed over a cursor, <- -> move it
 *   TIME   14:35             seconds start at 0 when CR is pressed
 *   ZONE   PRAGUE  UTC+1:00 EU DST     SPACE / up / down: the next / previous zone
 * A valid date and time is converted when the zone changes, so that it stays the same instant. With a
 * Unicard the time is also written to the card (rtcsync.c). */
#include "setup.h"
#include "kbd.h"
#include "text700.h"
#include "timebase.h"
#include "zones.h"
#include "wctime.h"
#include "rtcsync.h"

#define ROW_DATE 7
#define ROW_TIME 9
#define ROW_ZONE 11
#define ROW_MSG 13
#define COL_VAL 15
#define N_DIGITS 12

#define A_TEXT ATTR(C_WHITE, C_BLACK)
#define A_VALUE ATTR(C_YELLOW, C_BLACK)
#define A_CURSOR ATTR(C_BLACK, C_YELLOW)
#define A_HINT ATTR(C_CYAN, C_BLACK)

/* screen position of each digit: YYYY-MM-DD, HH:MM */
static const uint8_t dig_row[N_DIGITS] = {ROW_DATE, ROW_DATE, ROW_DATE, ROW_DATE, ROW_DATE, ROW_DATE,
                                          ROW_DATE, ROW_DATE, ROW_TIME, ROW_TIME, ROW_TIME, ROW_TIME};
static const uint8_t dig_col[N_DIGITS] = {0, 1, 2, 3, 5, 6, 8, 9, 0, 1, 3, 4};
static const char *const rule_name[] = {"", " EU DST", " US DST", " AU DST"};

static uint8_t digit[N_DIGITS];

static void put_digit(uint8_t i, uint8_t attr)
{
    txt_putc(dig_row[i], COL_VAL + dig_col[i], 0x20 + digit[i], attr);
}

static uint16_t number(uint8_t first, uint8_t n)
{
    uint16_t v = 0;

    while (n--)
        v = v * 10 + digit[first++];
    return v;
}

static void set_number(uint8_t first, uint8_t n, uint16_t v)
{
    while (n--) {
        digit[first + n] = (uint8_t)(v % 10);
        v /= 10;
    }
}

/* The digits as a date and time: 0 = invalid date, 1 = invalid time, 2 = valid */
static uint8_t digits_tm(struct wc_tm *tm)
{
    tm->year = number(0, 4);
    tm->month = (uint8_t)number(4, 2);
    tm->day = (uint8_t)number(6, 2);
    tm->hour = (uint8_t)number(8, 2);
    tm->min = (uint8_t)number(10, 2);
    tm->sec = 0;
    if (tm->year < WC_YEAR_MIN || tm->year > WC_YEAR_MAX || tm->month < 1 || tm->month > 12 || tm->day < 1
        || tm->day > wc_days_in_month(tm->year, tm->month))
        return 0;
    return (tm->hour > 23 || tm->min > 59) ? 1 : 2;
}

static void tm_digits(const struct wc_tm *tm)
{
    uint8_t i;

    set_number(0, 4, tm->year);
    set_number(4, 2, tm->month);
    set_number(6, 2, tm->day);
    set_number(8, 2, tm->hour);
    set_number(10, 2, tm->min);
    for (i = 0; i < N_DIGITS; ++i)
        put_digit(i, A_VALUE);
}

static void show_zone(uint8_t z)
{
    const struct wc_zone *w = &wc_zones[z];
    int16_t off = w->std_minutes;
    uint8_t col = COL_VAL + 10;          /* names have at most 9 characters; the line ends in column 39 */

    txt_puts(ROW_ZONE, COL_VAL, "                         ", A_VALUE);
    txt_puts(ROW_ZONE, COL_VAL, w->name, A_VALUE);
    txt_puts(ROW_ZONE, col, "UTC", A_TEXT);
    txt_putc(ROW_ZONE, col + 3, txt_code(off < 0 ? '-' : '+'), A_TEXT);
    if (off < 0)
        off = -off;
    txt_putc(ROW_ZONE, col + 4, 0x20 + off / 60, A_TEXT);
    txt_putc(ROW_ZONE, col + 5, txt_code(':'), A_TEXT);
    txt_dec2(ROW_ZONE, col + 6, (uint8_t)(off % 60), A_TEXT);
    txt_puts(ROW_ZONE, col + 8, rule_name[w->dst], A_TEXT);
}

uint8_t setup_run(uint8_t *zone, uint8_t have_time)
{
    struct wc_tm tm;
    uint8_t cur = 0, i, key;
    uint16_t frac;
    wc_time_t now;
    const struct wc_zone *w;

    if (have_time) {
        w = &wc_zones[*zone];
        wc_split(wc_to_local(clock_now(&frac), w->std_minutes, w->dst), &tm);
    } else {
        tm.year = 2026;
        tm.month = 1;
        tm.day = 1;
        tm.hour = tm.min = 0;
    }
    txt_fill(0x00, A_TEXT);
    txt_puts(1, 10, "*** WORLD CLOCK ***", ATTR(C_CYAN, C_BLACK));
    txt_puts(4, 2, "SET THE DATE, TIME AND HOME ZONE", A_TEXT);
    txt_puts(ROW_DATE, 6, "DATE", A_TEXT);
    txt_puts(ROW_TIME, 6, "TIME", A_TEXT);
    txt_puts(ROW_ZONE, 6, "ZONE", A_TEXT);
    txt_putc(ROW_DATE, COL_VAL + 4, txt_code('-'), A_VALUE);
    txt_putc(ROW_DATE, COL_VAL + 7, txt_code('-'), A_VALUE);
    txt_putc(ROW_TIME, COL_VAL + 2, txt_code(':'), A_VALUE);
    txt_puts(16, 6, "0-9      DIGITS", A_HINT);
    txt_puts(17, 6, "<- ->    MOVE", A_HINT);
    txt_puts(18, 6, "SPACE    NEXT ZONE", A_HINT);
    txt_puts(19, 6, "CR       START THE CLOCK", A_HINT);
    txt_puts(20, 6, have_time ? "BREAK    BACK" : "BREAK    EXIT", A_HINT);
    if (rtc_present)
        txt_puts(22, 6, "UNICARD CLOCK: SET WITH CR TOO", ATTR(C_GREEN, C_BLACK));
    tm_digits(&tm);
    show_zone(*zone);

    for (;;) {
        put_digit(cur, A_CURSOR);
        tb_wait_frame();
        key = kbd_get();
        if (key == K_NONE)
            continue;
        put_digit(cur, A_VALUE);
        txt_puts(ROW_MSG, 6, "                  ", A_TEXT);
        if (key >= '0' && key <= '9') {
            digit[cur] = key - '0';
            put_digit(cur, A_VALUE);
            if (cur < N_DIGITS - 1)
                ++cur;
        } else if (key == K_LEFT || key == K_DEL) {
            if (cur)
                --cur;
        } else if (key == K_RIGHT) {
            if (cur < N_DIGITS - 1)
                ++cur;
        } else if (key == ' ' || key == K_DOWN || key == K_UP) {
            i = key == K_UP ? (*zone + wc_zone_count - 1) % wc_zone_count : (*zone + 1) % wc_zone_count;
            if (digits_tm(&tm) == 2) {       /* the same instant in the new zone */
                w = &wc_zones[*zone];
                now = wc_to_utc(wc_make(&tm), w->std_minutes, w->dst);
                wc_split(wc_to_local(now, wc_zones[i].std_minutes, wc_zones[i].dst), &tm);
                tm_digits(&tm);
            }
            *zone = i;
            show_zone(*zone);
        } else if (key == K_BREAK) {
            return 0;
        } else if (key == K_CR) {
            i = digits_tm(&tm);
            if (i == 0) {
                txt_puts(ROW_MSG, 6, "INVALID DATE", ATTR(C_RED, C_BLACK));
                cur = 0;
            } else if (i == 1) {
                txt_puts(ROW_MSG, 6, "INVALID TIME", ATTR(C_RED, C_BLACK));
                cur = 8;
            } else {
                w = &wc_zones[*zone];
                clock_set(wc_to_utc(wc_make(&tm), w->std_minutes, w->dst));
                rtc_manual_set(*zone);
                return 1;
            }
        }
    }
}
