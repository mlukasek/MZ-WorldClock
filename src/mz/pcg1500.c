/* The PCG of the MZ-1500 (see pcg1500.h). How it works, from the mz800emu sources and the MZ-1500 IPL:
 *
 *   - OUT (F0h): bit 0 = MZ-1500 mode (PCG), bit 1 = priority BFP (text first, non-zero PCG pixels over it);
 *     write only, the IPL leaves 00h;
 *   - OUT (E5h),1..3 maps PCG bank 1..3 (the bits of the PCG colour index) at D000h-EFFFh, 8 bytes per glyph,
 *     bit 7 = the leftmost pixel; meanwhile the VRAM, the I/O at E000h and F000h-FFFFh are gone (this code
 *     and its stack are at 2000h-7FFFh, interrupts are off); OUT (E6h) unmaps;
 *   - per cell: PCGLO at D400h + position (glyph number), PCGHI at DC00h + position (bit 3: PCG on);
 *   - the IPL sets the identity palette (index i shows MZ-700 colour i), so index 3 is magenta.
 * The half glyph is BAR_HALF of data/glyphs.txt in planes 1 and 2 (index 3), plane 3 clear. */
#include <string.h>
#include "pcg1500.h"
#include "glyphs.h"
#include "historic.h"
#include "hw.h"

#define PCG_GLYPH 1                         /* glyph number in the PCG banks */
#define PCG_BANK ((uint8_t *)0xD000 + PCG_GLYPH * 8)
#define PCGLO ((volatile uint8_t *)0xD400 + HIST_BAR_ROW * 40 + HIST_BAR_COL)
#define PCGHI ((volatile uint8_t *)0xDC00 + HIST_BAR_ROW * 40 + HIST_BAR_COL)
#define PCGHI_OFF 0x71                      /* what the monitor's CLS writes there (bit 3 = 0) */
#define PCGHI_ON 0x08

static uint8_t reverse(uint8_t b)
{
    uint8_t r = 0, i;

    for (i = 0; i < 8; ++i) {
        r = r << 1 | (b & 1);
        b >>= 1;
    }
    return r;
}

void pcg_init(void)
{
    uint8_t rows[8], i;

    for (i = 0; i < 8; ++i)                 /* glyphs.c has the leftmost pixel in bit 0, the PCG in bit 7 */
        rows[i] = reverse(glyphs[GLYPH_BAR_HALF].rows[i]);
    HW_OUT(0xE5, 1);
    memcpy(PCG_BANK, rows, 8);
    HW_OUT(0xE5, 2);
    memcpy(PCG_BANK, rows, 8);
    HW_OUT(0xE5, 3);
    memset(PCG_BANK, 0, 8);
    HW_OUT(0xE6, 0);
    for (i = 0; i < HIST_BAR_CELLS; ++i) {
        PCGLO[i] = PCG_GLYPH;
        PCGHI[i] = PCGHI_OFF;
    }
    HW_OUT(0xF0, 0x03);                     /* MZ-1500 mode, priority BFP */
}

void pcg_half(uint8_t cell, uint8_t on)
{
    PCGHI[cell] = on ? PCGHI_ON : PCGHI_OFF;
}

void pcg_exit(void)
{
    HW_OUT(0xF0, 0x00);                     /* MZ-700 mode, as the IPL leaves it */
}
