/* The machine: detection, start and exit (docs/rozhodnuti.md, "paměť a start"). */
#include "machine.h"
#include "hw.h"
#include "timebase.h"

struct machine mach;

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

void machine_init(void)
{
    /* ROM at 0000h, VRAM at D000h, I/O at E000h on every machine (on an MZ-800 in its own mode it maps all
       ROMs, the CG-ROM at 1000h and the VRAM at 8000h; nothing of ours is there) */
    HW_OUT(0xE4, 0);
    if (MEM8(0x0000) == 0xC3 && MEM8(0x0001) == 0x00 && MEM8(0x0002) == 0xE8) {
        /* 1Z-013B jumps to the IPL: an MZ-800. Into MZ-700 mode, in case the IPL started us in its own
           mode (the IPL has copied the CG-ROM into the CG-RAM either way). */
        mach.model = MODEL_MZ800;
        HW_OUT(0xCE, 0x08);
        HW_OUT(0xE4, 0);
    } else {
        mach.model = MODEL_MZ700;
    }
    mach.jp = rom_has(0x06F3, "1Z-009");
    PPI_CTRL = 0x04;                 /* PC2 = 0: no INT from the 8253, we run with DI */
    mach.lines = tb_measure_lines();
    mach.ntsc = mach.lines < 287;
    mach.line_hz = mach.ntsc ? 15700 : 15611;
}

void machine_exit(uint32_t local_secs)
{
    PPI_CTRL = 0x05;                 /* PC2 = 1: the monitor's clock interrupt */
    mon_set_clock(local_secs);       /* reprograms CTC1/CTC2 and ends with EI */
    mon_cls();
}
