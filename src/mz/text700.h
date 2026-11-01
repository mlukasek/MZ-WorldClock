/* Text screen of the MZ-700 (and of the MZ-800 in MZ-700 mode): 40x25, display codes at D000h, attributes
 * at D800h (bits 6-4 foreground, 2-0 background, bit 7 the second character set). */
#ifndef WC_TEXT700_H
#define WC_TEXT700_H

#include <stdint.h>

#define ATTR(fg, bg) (uint8_t)((fg) << 4 | (bg))
#define C_BLACK 0
#define C_BLUE 1
#define C_RED 2
#define C_MAGENTA 3
#define C_GREEN 4
#define C_CYAN 5
#define C_YELLOW 6
#define C_WHITE 7

extern const uint8_t txt_ascii[64];                  /* ASCII 20h-5Fh -> display code (gfx.asm too) */
uint8_t txt_code(char c);                          /* ASCII -> display code */
void txt_fill(uint8_t code, uint8_t attr);
void txt_putc(uint8_t row, uint8_t col, uint8_t code, uint8_t attr);
void txt_puts(uint8_t row, uint8_t col, const char *s, uint8_t attr);
void txt_dec2(uint8_t row, uint8_t col, uint8_t v, uint8_t attr);   /* two digits */
void txt_attr(uint8_t row, uint8_t col, uint8_t n, uint8_t attr);   /* recolour n cells */

#endif
