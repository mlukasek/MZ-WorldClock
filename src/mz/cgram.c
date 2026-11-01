/* Own glyphs in the CG-RAM of the MZ-800 in MZ-700 mode (see cgram.h).
 *
 * In MZ-700 mode the MZ-800 draws the text with the CG-RAM (plane I of its VRAM), which its IPL fills from the
 * CG-ROM. IN (E0h) maps the CG-ROM at 1000h and the CG-RAM at C000h-CFFFh (set 0 at C000h, set 1 at C800h,
 * 8 bytes per glyph, bit 0 = the leftmost pixel); IN (E1h) unmaps both. This code and its stack are outside
 * those windows (2000h-7FFFh). */
#include <string.h>
#include "cgram.h"
#include "glyphs.h"
#include "hw.h"

#define CGRAM ((uint8_t *)0xC000)
#define CGROM ((const uint8_t *)0x1000)

void cgram_load(void)
{
    uint8_t i;

    hw_in(0xE0);
    for (i = 0; i < GLYPHS; ++i)
        memcpy(CGRAM + (glyphs[i].set ? 0x800 : 0) + (uint16_t)glyphs[i].code * 8, glyphs[i].rows, 8);
    hw_in(0xE1);
}

void cgram_restore(void)
{
    hw_in(0xE0);
    memcpy(CGRAM, CGROM, 4096);
    hw_in(0xE1);
}
