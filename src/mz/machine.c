/* The machine: detection, start and exit (docs/rozhodnuti.md, "paměť a start").
 *
 * Detection:
 *   - monitor at 0000h: JP 004Ah on the MZ-700 (1Z-013A, 1Z-009A/B); JP E800h (the IPL) on the MZ-800 (1Z-013B)
 *     and on the MZ-1500 (whose monitor shows 1Z-009B and has the Japanese CG-ROM);
 *   - for the latter two the hardware decides: the MZ-800's GDG status port CEh has /VBLN in bit 6, the same
 *     signal as 8255 PC7; on the MZ-700 and the MZ-1500 the port does not exist and reads a constant bus value;
 *   - Japanese: the monitor banner at 06F3h starts with 1Z-009 (the hiragana CG-ROM comes with it);
 *   - PAL / NTSC: the lines per frame are measured (312 / 262). */
#include "machine.h"
#include "hw.h"
#include "timebase.h"
#include "cgram.h"

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

/* 1 when bit 6 of port CEh follows /VBLK (PC7) over a few frames; either polarity is accepted (the real
   polarity is in docs/hw-otazky.md) */
static uint8_t gdg_present(void)
{
    uint16_t i, same = 0;
    uint8_t vblk, last = 0, edges = 0;

    for (i = 0; i < 2000; ++i) {
        vblk = PPI_PC & 0x80;
        if (!vblk == !(hw_in(0xCE) & 0x40))
            ++same;
        if (i && vblk != last)
            ++edges;
        last = vblk;
    }
    return edges >= 2 && (same >= 1960 || same <= 40);
}

void machine_init(void)
{
    /* ROM at 0000h, VRAM at D000h, I/O at E000h on every machine (on an MZ-800 in its own mode it maps all
       ROMs, the CG-ROM at 1000h and the VRAM at 8000h; nothing of ours is there) */
    HW_OUT(0xE4, 0);
    mach.model = MODEL_MZ700;
    if (MEM8(0x0000) == 0xC3 && MEM8(0x0001) == 0x00 && MEM8(0x0002) == 0xE8) {
        /* An MZ-800 may have been started by its IPL in its own mode: into MZ-700 mode (the IPL has copied the
           CG-ROM into the CG-RAM either way). Ports CCh-CFh do not exist on the MZ-1500, the write is harmless. */
        HW_OUT(0xCE, 0x08);
        HW_OUT(0xE4, 0);
        if (gdg_present())
            mach.model = MODEL_MZ800;
        else if (rom_has(0x06F3, "1Z-009"))
            mach.model = MODEL_MZ1500;
    }
    mach.jp = rom_has(0x06F3, "1Z-009");
    PPI_CTRL = 0x04;                 /* PC2 = 0: no INT from the 8253, we run with DI */
    mach.lines = tb_measure_lines();
    mach.ntsc = mach.lines < 287;
    mach.line_hz = mach.ntsc ? 15700 : 15611;
}

void machine_exit(uint32_t local_secs)
{
    if (mach.model == MODEL_MZ800)
        cgram_restore();             /* the CG-RAM as the IPL left it: a copy of the CG-ROM */
    PPI_CTRL = 0x05;                 /* PC2 = 1: the monitor's clock interrupt */
    mon_set_clock(local_secs);       /* reprograms CTC1/CTC2 and ends with EI */
    mon_cls();
}
