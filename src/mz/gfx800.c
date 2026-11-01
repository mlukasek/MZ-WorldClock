/* The MZ-800's own mode (see gfx800.h and docs/rozhodnuti.md "moderní vzhled", "hodiny").
 *
 * DMD (CEh) 00h: 320x200 in 4 colours from planes I and II, colour = plane II bit << 1 | plane I bit, through
 * the palette (F0h). DMD 02h: 320x200 in 16 colours from planes I-IV (the VRAM extension); a colour whose
 * planes III, IV match the palette group (0) goes through the palette, the others are IGRB as they are.
 * IN (E0h) maps the VRAM at 8000h-9FFFh and the CG-ROM at 1000h-1FFFh; nothing used then is there (the main
 * part of the program is at 2000h-7FFFh, the BSS at A000h, the stack below C000h; the cold part at 1200h-1FFFh
 * is not called while mapped). In this mode the 8255 and the 8253 are ports D0h-D7h (io_native). Drawing
 * overwrites plane I, where MZ-700 mode keeps its CG-RAM and text VRAM: gfx_end() leaves them cleared, the
 * caller rebuilds the CG-RAM.
 *
 * The GDG's write formats (WF, CCh; mz800emu vramctrl): SINGLE / EXOR / OR / RESET write the selected planes,
 * REPLACE writes the byte in the colour's planes and 0 in the others, PSET sets the pixels of the byte to the
 * colour and leaves the rest. REPLACE and PSET work on planes I, II in the 4-colour mode, on all four in the
 * 16-colour one, so the same drawing serves both. The text, span and line drawing is in gfx.asm. */
#include <string.h>
#include "gfx800.h"
#include "hw.h"
#include "machine.h"

static const uint8_t pal_black[4] = {0x00, 0x10, 0x20, 0x30};
static uint8_t ext_known;              /* 0 not yet tested, 1 no VRAM extension, 2 extension */

void gfx_map(void)
{
    hw_in(0xE0);
}

void gfx_unmap(void)
{
    hw_in(0xE1);
}

void gfx_wf(uint8_t wf)
{
    HW_OUT(0xCC, wf);
}

static void palette(const uint8_t *p)
{
    uint8_t i;

    HW_OUT(0xF0, 0x40);                /* palette group 0 */
    for (i = 0; i < 4; ++i)
        HW_OUT(0xF0, p[i]);
}

/* A black screen at once (the 4-colour mode with a black palette), then all four planes cleared; mapped */
static void blank(void)
{
    palette(pal_black);
    HW_OUT(0xCE, 0x00);
    gfx_map();
    gfx_wf(WF_SINGLE_ALL);
    memset((uint8_t *)GFX_VRAM, 0, 0x2000);    /* 8 KB: also the MZ-700 mode's text VRAM and CG-RAM */
}

uint8_t gfx_begin(const uint8_t *pal4, const uint8_t *pal16)
{
    uint8_t ext;

    if (!io_native) {                  /* from MZ-700 mode: its text screen goes dark first */
        memset((uint8_t *)0xD800, 0, 1000);
        /* The speaker is CTC0 OUT (and PC0). MZ-800 mode holds GATE0 at 1, so whatever the monitor left in
           counter 0 (the beep: mode 3) would start to sound. A control word alone stops the counter, sets OUT
           high (as the monitor leaves it) and waits for a count that never comes: no edge, no click. */
        IO_WR(R_CTC, 0x36);
        blank();
        io_native = 1;
        HW_OUT_BC(0x06CF, 0x00);       /* border black */
        HW_OUT_BC(0x01CF, 0x00);       /* scroll offset 0: no hardware scroll */
        HW_OUT_BC(0x02CF, 0x00);
    } else {
        blank();
    }
    if (!ext_known) {                  /* planes III, IV read FFh without the extension */
        ext_known = 1;
        if (!(test_hook.flags & TEST_NO_EXTVRAM)) {
            gfx_wf(0x04);              /* SINGLE, plane III */
            HW_OUT(0xCD, 0x04);        /* read format: plane III */
            GFX_VRAM[0] = 0x5A;
            if (GFX_VRAM[0] == 0x5A) {
                GFX_VRAM[0] = 0xA5;
                if (GFX_VRAM[0] == 0xA5)
                    ext_known = 2;
            }
            GFX_VRAM[0] = 0;
        }
    }
    HW_OUT(0xCD, 0x01);                /* read format: plane I (not used) */
    ext = pal16 && ext_known == 2;
    HW_OUT(0xCE, ext ? 0x02 : 0x00);
    palette(ext ? pal16 : pal4);
    gfx_unmap();
    return ext;
}

void gfx_end(void)
{
    blank();
    gfx_unmap();
    HW_OUT(0xCE, 0x08);                /* MZ-700 mode: its text screen is all 0, i.e. black */
    HW_OUT(0xE4, 0x00);                /* ROM 0000h, VRAM D000h, I/O E000h */
    io_native = 0;
}

/* The shadow: the glyphs in colour 0 one pixel right and down, then the glyphs in the colour */
void gfx_text(uint8_t bx, uint8_t y, const char *s, uint8_t colour)
{
    if (colour & GFX_SHADOW) {
        gfx_ptext((uint16_t)bx * 8 + 1, y + 1, s, 0);
        gfx_ptext((uint16_t)bx * 8, y, s, colour & 0x0F);
    } else {
        gfx_ctext(bx, y, s, colour, 1, 1);
    }
}

void gfx_plot(uint16_t x, uint8_t y)
{
    if (x >= 320 || y >= 200)
        return;
    gfx_wf(WF_OR);
    GFX_VRAM[(uint16_t)y * 40 + (x >> 3)] = 1 << (x & 7);
}
