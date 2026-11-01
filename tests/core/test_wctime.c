/* Test of src/core/wctime.c on the z88dk +test target (run in z88dk-ticks by tests/core/run_core.py).
 * For each vector (UTC time, zone) it prints: offset (hex), the local time split (YYYYMMDDhhmmssW) and the
 * local -> UTC round trip (hex); the Python side computes the same with zoneinfo. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/wctime.h"
#include "vectors.h"            /* generated: ZONES[], VECTORS[] */

static void hex(uint32_t v, uint8_t digits)
{
    while (digits--)
        putchar("0123456789ABCDEF"[(uint8_t)(v >> (digits * 4)) & 15]);
}

static void dec(uint16_t v, uint8_t digits)
{
    char buf[5];
    uint8_t i = digits;

    while (i--) {
        buf[i] = '0' + v % 10;
        v /= 10;
    }
    for (i = 0; i < digits; ++i)
        putchar(buf[i]);
}

int main(void)
{
    uint16_t i;
    struct wc_tm tm;
    const struct test_zone *z;
    wc_time_t local;
    int16_t off;

    for (i = 0; i < N_VECTORS; ++i) {
        z = &ZONES[VECTORS[i].zone];
        off = wc_offset(VECTORS[i].utc, z->std, z->rule);
        local = wc_to_local(VECTORS[i].utc, z->std, z->rule);
        wc_split(local, &tm);
        hex((uint16_t)off, 4);
        putchar(' ');
        dec(tm.year, 4);
        dec(tm.month, 2);
        dec(tm.day, 2);
        dec(tm.hour, 2);
        dec(tm.min, 2);
        dec(tm.sec, 2);
        dec(tm.wday, 1);
        putchar(' ');
        hex(wc_make(&tm) == local ? wc_to_utc(local, z->std, z->rule) : 0xFFFFFFFFUL, 8);
        putchar('\n');
    }
    return 0;
}
