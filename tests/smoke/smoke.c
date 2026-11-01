/* Toolchain smoke test: own crt0 at 2000h, direct VRAM writes, machine detection by the ROM signature,
 * the BREAK key read straight from the 8255, exit to the monitor.
 * Checked by tests/smoke/run_smoke.py on the emulated MZ-700 EU / JP and MZ-800. */
#include <stdint.h>
#include "../../src/mz/hw.h"

/* ASCII 20h-5Fh -> display code (the monitor's table at 0A92h, the same in 1Z-013A and 1Z-009B) */
static const uint8_t ascii_disp[64] = {
    0x00, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6B, 0x6A, 0x2F, 0x2A, 0x2E, 0x2D,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x4F, 0x2C, 0x51, 0x2B, 0x57, 0x49,
    0x55, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x52, 0x59, 0x54, 0x50, 0x45};

static void put_text(uint8_t col, uint8_t row, const char *s, uint8_t attr)
{
    uint16_t pos = (uint16_t)row * 40 + col;
    while (*s) {
        uint8_t c = (uint8_t)*s++;
        VRAM_TEXT[pos] = (c >= 0x20 && c < 0x60) ? ascii_disp[c - 0x20] : 0x00;
        VRAM_ATTR[pos] = attr;
        ++pos;
    }
}

static uint8_t rom_has(uint16_t addr, const char *s)
{
    while (*s) {
        if (MEM8(addr) != (uint8_t)*s)
            return 0;
        ++addr;
        ++s;
    }
    return 1;
}

int main(void)
{
    const char *name;
    uint16_t i;

    HW_OUT(0xE4, 0);   /* ROM 0000h, VRAM D000h, I/O E000h on every machine */

    if (MEM8(0x0000) == 0xC3 && MEM8(0x0001) == 0x00 && MEM8(0x0002) == 0xE8)
        name = "MZ-800";
    else if (rom_has(0x06F3, "1Z-009"))
        name = "MZ-700 JP";
    else
        name = "MZ-700 EU";

    for (i = 0; i < 1000; ++i) {
        VRAM_TEXT[i] = 0x00;
        VRAM_ATTR[i] = 0x70;
    }
    put_text(0, 0, "*** WORLD CLOCK SMOKE TEST ***", 0x50);
    put_text(0, 2, "MACHINE:", 0x70);
    put_text(9, 2, name, 0x60);
    put_text(0, 4, "PRESS BREAK", 0x20);

    for (;;) {
        PPI_PA = 0xF8;               /* column 8; PA4-7 high (joystick strobes off, cursor timer on) */
        if (!(PPI_PB & 0x80))        /* BREAK */
            break;
    }
    while (!(PPI_PB & 0x80))         /* wait for its release, the monitor would see it too */
        ;
    put_text(0, 6, "BYE", 0x40);
    hw_ei();                         /* the monitor runs with interrupts on; its clock is untouched here */
    return 0;
}
