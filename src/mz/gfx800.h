/* The MZ-800's own mode: 320x200 in 4 colours (planes I and II) or 16 colours (planes I-IV, the VRAM extension),
 * drawn through the GDG's write formats. */
#ifndef WC_GFX800_H
#define WC_GFX800_H

#include <stdint.h>

#define GFX_VRAM ((volatile uint8_t *)0x8000)      /* while mapped: 40 bytes per line, bit 0 = left pixel */
#define GFX_CGROM ((const uint8_t *)0x1000)        /* while mapped: the font, 8 bytes per glyph */

/* Write format register (CCh): mode in bits 7-5, planes in bits 3-0 */
#define WF_PLANE_I 0x01        /* SINGLE: the byte goes into plane I */
#define WF_PLANE_II 0x02       /* SINGLE: into plane II */
#define WF_BOTH 0x03           /* SINGLE: into both: 1 = colour 3, 0 = colour 0 */
#define WF_SINGLE_ALL 0x0F     /* SINGLE: into planes I-IV */
#define WF_OR 0x43             /* OR into both: colour 3 where the byte has 1 */
#define WF_RESET 0x63          /* RESET in both: colour 0 where the byte has 1 */
#define WF_REPLACE(c) (0x80 | (c))     /* colour c where the byte has 1, colour 0 elsewhere */
#define WF_PSET(c) (0xC0 | (c))        /* colour c where the byte has 1, the rest unchanged */

/* From MZ-700 mode (its text screen darkened first) or from another MZ-800 screen: black at once, all planes
 * cleared, then 320x200 in 16 colours with the palette pal16 if given and the VRAM extension is there (returns
 * 1), else in 4 colours with pal4 (palettes: 4 values for port F0h); unmapped */
uint8_t gfx_begin(const uint8_t *pal4, const uint8_t *pal16);
void gfx_end(void);                    /* black at once, back to MZ-700 mode, its text VRAM and CG-RAM all 0 */
void gfx_map(void);                    /* IN (E0h): VRAM at 8000h, CG-ROM at 1000h */
void gfx_unmap(void);                  /* IN (E1h) */
void gfx_wf(uint8_t wf);

/* Drawing, while mapped (gfx.asm: gfx_ctext, gfx_ptext, gfx_hspan, gfx_line). Texts: ASCII 20h-5Fh. */
/* Text from the CG-ROM at byte column bx, pixel row y: with a black shadow 1 pixel right and down over what
 * is there (colour 3, 4-colour mode), or opaque (colour 3 on colour 0) */
void gfx_text(uint8_t bx, uint8_t y, const char *s, uint8_t shadow);
/* Opaque text in colour on colour 0, each glyph pixel sx (1, 2 or 4) wide and sy tall */
void gfx_ctext(uint8_t bx, uint8_t y, const char *s, uint8_t colour, uint8_t sx, uint8_t sy);
void gfx_ptext(uint16_t x, uint8_t y, const char *s, uint8_t colour);   /* only the glyph pixels, any x */
void gfx_hspan(uint16_t x0, uint16_t x1, uint8_t y, uint8_t colour);    /* pixels x0..x1 */
/* A line on the screen, both extents below 256, width 1-3: copies shifted by 1 pixel across it (sideways when
 * steep, else up and down) */
void gfx_line(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t colour, uint8_t width);
void gfx_plot(uint16_t x, uint8_t y);  /* colour 3 (sets WF_OR) */

/* hw.asm: one map row of the modern look, both planes (row_land, row_day in screen order, row_dither) */
extern uint8_t row_land[40], row_day[40], row_dither;
void row_out(volatile uint8_t *vram_row) __z88dk_fastcall;
/* hw.asm: one RLE row of the land mask (tools/mkmodern.py) into row_land, not rotated */
void land_decode(const uint8_t *rle) __z88dk_fastcall;

#endif
