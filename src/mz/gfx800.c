/* The MZ-800's own mode (see gfx800.h and docs/rozhodnuti.md "moderní vzhled").
 *
 * DMD (CEh) 00h: 320x200 in 4 colours from planes I and II, colour = plane II bit << 1 | plane I bit, through
 * the palette (F0h). IN (E0h) maps the VRAM at 8000h-9FFFh and the CG-ROM at 1000h-1FFFh; nothing of the
 * program is there (code and data 2000h-7FFFh, stack below 8000h, BSS at A000h). In this mode the 8255 and
 * the 8253 are ports D0h-D7h (io_native). Drawing overwrites plane I, where MZ-700 mode keeps its CG-RAM and
 * text VRAM: the caller restores them after gfx_off(). */
#include <string.h>
#include "gfx800.h"
#include "hw.h"
#include "text700.h"

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

void gfx_on(const uint8_t *palette)
{
    uint8_t i;

    HW_OUT(0xCE, 0x00);                /* MZ-800 mode, 320x200, 4 colours, frame A */
    io_native = 1;
    IO_WR(R_CTC, 0x30);                /* counter 0 parked in mode 0: GATE0 is forced on in this mode */
    IO_WR(R_CTC0, 0);
    IO_WR(R_CTC0, 0);
    HW_OUT(0xF0, 0x40);                /* palette group 0 */
    for (i = 0; i < 4; ++i)
        HW_OUT(0xF0, palette[i]);
    HW_OUT_BC(0x06CF, 0x00);           /* border black */
    HW_OUT_BC(0x01CF, 0x00);           /* scroll offset 0: no hardware scroll */
    HW_OUT_BC(0x02CF, 0x00);
    HW_OUT(0xCD, 0x01);                /* read format: plane I (not used) */
    gfx_map();
    gfx_wf(WF_BOTH);
    memset((uint8_t *)GFX_VRAM, 0, 8000);
    gfx_unmap();
}

void gfx_off(void)
{
    gfx_unmap();
    HW_OUT(0xCE, 0x08);                /* MZ-700 mode */
    HW_OUT(0xE4, 0x00);                /* ROM 0000h, VRAM D000h, I/O E000h */
    io_native = 0;
}

void gfx_text(uint8_t bx, uint8_t y, const char *s, uint8_t shadow)
{
    const uint8_t *g;
    volatile uint8_t *v;
    const char *c;
    uint8_t k, r;

    if (shadow) {
        gfx_wf(WF_RESET);
        for (c = s, k = bx; *c; ++c, ++k) {
            g = GFX_CGROM + (uint16_t)txt_code(*c) * 8;
            v = GFX_VRAM + (uint16_t)(y + 1) * 40 + k;
            for (r = 0; r < 8; ++r, v += 40) {
                v[0] = g[r] << 1;
                if (k < 39)
                    v[1] = g[r] >> 7;
            }
        }
        gfx_wf(WF_OR);
    } else {
        gfx_wf(WF_BOTH);
    }
    for (c = s, k = bx; *c; ++c, ++k) {
        g = GFX_CGROM + (uint16_t)txt_code(*c) * 8;
        v = GFX_VRAM + (uint16_t)y * 40 + k;
        for (r = 0; r < 8; ++r, v += 40)
            *v = g[r];
    }
}

void gfx_plot(uint16_t x, uint8_t y)
{
    if (x >= 320 || y >= 200)
        return;
    gfx_wf(WF_OR);
    GFX_VRAM[(uint16_t)y * 40 + (x >> 3)] = 1 << (x & 7);
}
