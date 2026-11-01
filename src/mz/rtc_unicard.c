/* The real-time clock of the Unicard (see rtc_unicard.h). Protocol: E:\SAPI_GIT\SAPI_DPI-firmware\docs\unicard.md.
 *
 * A command is written to port 50h; the status is read after STSR (03h) as 4 bytes from port 50h: byte 0
 * bit 0 waits for parameters, bit 1 output ready, bit 7 error (bits 2-5 report open files); byte 1 the
 * command; byte 2 the bytes still to read or write. Every port access holds the Z80 in WAIT until the card
 * is done, so there is no busy state to poll. Without a card the ports float and the status does not match. */
#include "rtc_unicard.h"
#include "hw.h"

#define UC_CMD 0x50
#define UC_DATA 0x51
#define CMD_STSR 0x03
#define CMD_REVD 0x06
#define CMD_RTCSETD 0x60
#define CMD_RTCSETT 0x61
#define CMD_RTCGETD 0x62
#define CMD_RTCGETT 0x63

static uint8_t st[4];

static void status(void)
{
    uint8_t i;

    HW_OUT(UC_CMD, CMD_STSR);
    for (i = 0; i < 4; ++i)
        st[i] = hw_in(UC_CMD);
}

/* A command with `n` bytes of output: 1 when the card has them ready */
static uint8_t command_out(uint8_t cmd, uint8_t n)
{
    HW_OUT(UC_CMD, cmd);
    status();
    return (st[0] & 0x83) == 0x02 && st[1] == cmd && st[2] == n;
}

uint8_t rtc_detect(void)
{
    uint8_t i;

    if (!command_out(CMD_REVD, 4))
        return 0;
    for (i = 0; i < 4; ++i)       /* version, revision, subtype, machine type */
        hw_in(UC_DATA);
    return 1;
}

static uint8_t get3(uint8_t cmd, uint8_t *v)
{
    if (!command_out(cmd, 3))
        return 0;
    v[0] = hw_in(UC_DATA);
    v[1] = hw_in(UC_DATA);
    v[2] = hw_in(UC_DATA);
    return 1;
}

uint8_t rtc_read(struct wc_tm *tm)
{
    uint8_t d[3], t[3], d2[3];
    uint8_t tries;

    for (tries = 0; tries < 3; ++tries) {
        /* date, time, date again: the time belongs to the date only if the date did not change meanwhile */
        if (!get3(CMD_RTCGETD, d) || !get3(CMD_RTCGETT, t) || !get3(CMD_RTCGETD, d2))
            return 0;
        if (d[0] == d2[0] && d[1] == d2[1] && d[2] == d2[2])
            break;
    }
    tm->year = 1980 + d[2];
    tm->month = d[1];
    tm->day = d[0];
    tm->hour = t[0];
    tm->min = t[1];
    tm->sec = t[2];
    return tm->year >= 2020 && tm->year <= WC_YEAR_MAX && tm->month >= 1 && tm->month <= 12 && tm->day >= 1
           && tm->day <= wc_days_in_month(tm->year, tm->month) && tm->hour < 24 && tm->min < 60 && tm->sec < 60;
}

static uint8_t set3(uint8_t cmd, uint8_t a, uint8_t b, uint8_t c)
{
    HW_OUT(UC_CMD, cmd);
    HW_OUT(UC_DATA, a);
    HW_OUT(UC_DATA, b);
    HW_OUT(UC_DATA, c);
    status();
    return !(st[0] & 0x81) && st[1] == cmd;  /* no error, no parameters missing */
}

uint8_t rtc_write(const struct wc_tm *tm)
{
    return set3(CMD_RTCSETT, tm->hour, tm->min, tm->sec)
           && set3(CMD_RTCSETD, tm->day, tm->month, (uint8_t)(tm->year - 1980));
}
