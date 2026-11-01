/* Portable time library of MZ-WorldClock (see wctime.h).
 *
 * Years 2000-2099 only: every fourth year is a leap year, so the calendar works in 4-year cycles of 1461
 * days without loops over years (a Z80 computes one local time in a few tens of thousands of T states). */
#include "wctime.h"

#define SEC_PER_DAY 86400UL
#define SEC_PER_HOUR 3600UL

static const uint16_t month_start[12] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
static const uint8_t month_days[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};

uint8_t wc_days_in_month(uint16_t year, uint8_t month)
{
    if (month == 2 && (year & 3) == 0)
        return 29;
    return month_days[month - 1];
}

uint16_t wc_days_from_date(uint16_t year, uint8_t month, uint8_t day)
{
    uint16_t yy = year - WC_YEAR_MIN;
    uint16_t days = yy * 365 + (yy + 3) / 4 + month_start[month - 1] + day - 1;

    if (month > 2 && (year & 3) == 0)
        ++days;
    return days;
}

wc_time_t wc_make(const struct wc_tm *tm)
{
    return (wc_time_t)wc_days_from_date(tm->year, tm->month, tm->day) * SEC_PER_DAY
           + (wc_time_t)tm->hour * SEC_PER_HOUR + (uint16_t)(tm->min * 60 + tm->sec);
}

void wc_split(wc_time_t t, struct wc_tm *tm)
{
    uint16_t days = (uint16_t)(t / SEC_PER_DAY);
    uint32_t rest = t - (wc_time_t)days * SEC_PER_DAY;
    uint16_t secs, doy, len;
    uint8_t yy, m;

    tm->wday = (uint8_t)((days + 6) % 7);          /* 2000-01-01 was a Saturday */
    tm->hour = (uint8_t)(rest / SEC_PER_HOUR);
    secs = (uint16_t)rest - tm->hour * (uint16_t)SEC_PER_HOUR;
    tm->min = (uint8_t)(secs / 60);
    tm->sec = (uint8_t)(secs % 60);

    yy = (uint8_t)(days / 1461) * 4;               /* 4-year cycle, its first year is a leap year */
    doy = days % 1461;
    if (doy >= 366) {
        doy -= 366;
        yy += 1 + (uint8_t)(doy / 365);
        doy %= 365;
    }
    tm->year = WC_YEAR_MIN + yy;
    for (m = 1; m < 12; ++m) {
        len = wc_days_in_month(tm->year, m);
        if (doy < len)
            break;
        doy -= len;
    }
    tm->month = m;
    tm->day = (uint8_t)(doy + 1);
}

/* Day number of the n-th (1-4) Sunday of a month, or of the last one (n = 0) */
static uint16_t sunday(uint16_t year, uint8_t month, uint8_t n)
{
    uint16_t d;

    if (n) {
        d = wc_days_from_date(year, month, 1);
        d += (uint8_t)((7 - (d + 6) % 7) % 7);     /* the first Sunday */
        return d + (uint16_t)(n - 1) * 7;
    }
    d = wc_days_from_date(year, month, wc_days_in_month(year, month));
    return d - (uint8_t)((d + 6) % 7);
}

/* Instant (UTC) of a transition: midnight of `day` + `hour` (local, in `offset` minutes from UTC) */
static wc_time_t at(uint16_t day, uint8_t hour, int16_t offset)
{
    return (wc_time_t)day * SEC_PER_DAY + (wc_time_t)hour * SEC_PER_HOUR - (int32_t)offset * 60;
}

static uint8_t is_dst(wc_time_t utc, int16_t std, uint8_t rule)
{
    uint16_t year;
    uint16_t days;

    if (rule == DST_NONE)
        return 0;
    /* the year of local standard time (no transition is near New Year) */
    days = (uint16_t)((utc + (int32_t)std * 60) / SEC_PER_DAY);
    year = WC_YEAR_MIN + (days / 1461) * 4;
    days %= 1461;
    if (days >= 366)
        year += 1 + (days - 366) / 365;
    switch (rule) {
    case DST_EU:
        return utc >= at(sunday(year, 3, 0), 1, 0) && utc < at(sunday(year, 10, 0), 1, 0);
    case DST_US:
        return utc >= at(sunday(year, 3, 2), 2, std) && utc < at(sunday(year, 11, 1), 2, std + 60);
    case DST_AU:
        return utc < at(sunday(year, 4, 1), 3, std + 60) || utc >= at(sunday(year, 10, 1), 2, std);
    }
    return 0;
}

int16_t wc_offset(wc_time_t utc, int16_t std_minutes, uint8_t rule)
{
    return is_dst(utc, std_minutes, rule) ? std_minutes + 60 : std_minutes;
}

wc_time_t wc_to_local(wc_time_t utc, int16_t std_minutes, uint8_t rule)
{
    return utc + (int32_t)wc_offset(utc, std_minutes, rule) * 60;
}

wc_time_t wc_to_utc(wc_time_t local, int16_t std_minutes, uint8_t rule)
{
    wc_time_t t = local - (int32_t)(std_minutes + 60) * 60;    /* as if DST */

    if (rule != DST_NONE && is_dst(t, std_minutes, rule))
        return t;
    return local - (int32_t)std_minutes * 60;
}
