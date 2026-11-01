/* Time base in the 8253 without interrupts (see timebase.h and docs/vyvoj.md).
 *
 * CTC1 mode 2, count = line frequency: one OUT1 pulse per second (as the monitor's TIMST).
 * CTC2 mode 0, count 0: decrements on each OUT1 pulse and keeps wrapping, a free-running seconds counter.
 * OUT2 would raise INT when it reaches 0, so PC2 stays 0 (machine.c) and interrupts stay disabled. */
#include "timebase.h"
#include "hw.h"

uint16_t tb_line_hz;
wc_time_t tb_last_utc;        /* the last clock_now() result, for the emulator tests */
uint16_t tb_last_frac;
static uint16_t base_c2;      /* CTC2 at base_utc */
static wc_time_t base_utc;

static uint16_t read_ctc1(void)
{
    uint8_t lo;

    IO_WR(R_CTC, 0x40);          /* latch counter 1 */
    lo = io_rd(R_CTC1);
    return lo | (uint16_t)io_rd(R_CTC1) << 8;
}

static uint16_t read_ctc2(void)
{
    uint8_t lo;

    IO_WR(R_CTC, 0x80);          /* latch counter 2 */
    lo = io_rd(R_CTC2);
    return lo | (uint16_t)io_rd(R_CTC2) << 8;
}

void tb_wait_frame(void)
{
    while (!(io_rd(R_PC) & 0x80))  /* until the screen is drawn (/VBLK = 1) */
        ;
    while (io_rd(R_PC) & 0x80)     /* until the blanking starts */
        ;
}

uint16_t tb_measure_lines(void)
{
    uint16_t a;

    IO_WR(R_CTC, 0x74);          /* CTC1 mode 2, count 65536: a line counter */
    IO_WR(R_CTC1, 0);
    IO_WR(R_CTC1, 0);
    tb_wait_frame();
    tb_wait_frame();
    a = read_ctc1();
    tb_wait_frame();
    return a - read_ctc1();
}

void tb_init(uint16_t line_hz)
{
    tb_line_hz = line_hz;
    IO_WR(R_CTC, 0x74);          /* CTC1 mode 2 */
    IO_WR(R_CTC, 0xB0);          /* CTC2 mode 0 */
    IO_WR(R_CTC2, 0xFE);             /* count FFFEh: a value to recognise once loaded */
    IO_WR(R_CTC2, 0xFF);
    IO_WR(R_CTC1, 10);               /* OUT1 every 10 lines, so that CTC2 loads at once (as TIMST) */
    IO_WR(R_CTC1, 0);
    while (read_ctc2() != 0xFFFE)
        ;
    clock_set(0);
}

void clock_set(wc_time_t utc)
{
    IO_WR(R_CTC, 0x74);          /* restart CTC1: the next second starts a full second from now */
    IO_WR(R_CTC1, (uint8_t)tb_line_hz);
    IO_WR(R_CTC1, (uint8_t)(tb_line_hz >> 8));
    base_c2 = read_ctc2();
    base_utc = utc;
}

wc_time_t clock_now(uint16_t *frac)
{
    uint16_t a, c1, c2;

    do {                      /* no read-back command: a consistent pair of CTC2 and CTC1 */
        a = read_ctc2();
        c1 = read_ctc1();
        c2 = read_ctc2();
    } while (a != c2);
    *frac = (c1 <= 1 || c1 > tb_line_hz) ? 0 : tb_line_hz - c1;
    a = base_c2 - c2;         /* seconds since base (CTC2 counts down, wraps after 18 h) */
    if (a >= 60) {            /* move the base on, so that it never wraps */
        base_c2 = c2;
        base_utc += a;
        a = 0;
    }
    tb_last_frac = *frac;
    return tb_last_utc = base_utc + a;
}
