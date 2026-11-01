/* The MZ-800's own mode: 320x200 in 4 colours (planes I and II), drawn through the GDG's write formats. */
#ifndef WC_GFX800_H
#define WC_GFX800_H

#include <stdint.h>

#define GFX_VRAM ((volatile uint8_t *)0x8000)      /* while mapped: 40 bytes per line, bit 0 = left pixel */
#define GFX_CGROM ((const uint8_t *)0x1000)        /* while mapped: the font, 8 bytes per glyph */

/* Write format register (CCh): mode in bits 7-5, planes in bits 3-0 */
#define WF_PLANE_I 0x01        /* SINGLE: the byte goes into plane I */
#define WF_PLANE_II 0x02       /* SINGLE: into plane II */
#define WF_BOTH 0x03           /* SINGLE: into both: 1 = colour 3, 0 = colour 0 */
#define WF_OR 0x43             /* OR into both: colour 3 where the byte has 1 */
#define WF_RESET 0x63          /* RESET in both: colour 0 where the byte has 1 */

void gfx_on(const uint8_t *palette);   /* into MZ-800 mode, palette (4 values for port F0h), VRAM cleared */
void gfx_off(void);                    /* back to MZ-700 mode and its memory map */
void gfx_map(void);                    /* IN (E0h): VRAM at 8000h, CG-ROM at 1000h */
void gfx_unmap(void);                  /* IN (E1h) */
void gfx_wf(uint8_t wf);
/* Text from the CG-ROM at byte column bx, pixel row y (mapped): with a black shadow 1 pixel right and down
 * over what is there, or opaque (colour 3 on colour 0) */
void gfx_text(uint8_t bx, uint8_t y, const char *s, uint8_t shadow);
void gfx_plot(uint16_t x, uint8_t y);  /* colour 3 (mapped, any write format; sets WF_OR) */

/* hw.asm: one map row of the modern look, both planes (row_land, row_day in screen order, row_dither) */
extern uint8_t row_land[40], row_day[40], row_dither;
void row_out(volatile uint8_t *vram_row) __z88dk_fastcall;
/* hw.asm: one RLE row of the land mask (tools/mkmodern.py) into row_land, not rotated */
void land_decode(const uint8_t *rle) __z88dk_fastcall;

#endif
