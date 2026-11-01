/* Text screen of the MZ-700 (see text700.h). */
#include <string.h>
#include "text700.h"
#include "hw.h"

/* ASCII 20h-5Fh -> display code (the monitor's table at 0A92h, the same in 1Z-013A and 1Z-009B) */
const uint8_t txt_ascii[64] = {
    0x00, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6B, 0x6A, 0x2F, 0x2A, 0x2E, 0x2D,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x4F, 0x2C, 0x51, 0x2B, 0x57, 0x49,
    0x55, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x52, 0x59, 0x54, 0x50, 0x45};

uint8_t txt_code(char c)
{
    uint8_t u = (uint8_t)c;

    if (u >= 'a' && u <= 'z')
        u -= 0x20;
    return (u >= 0x20 && u < 0x60) ? txt_ascii[u - 0x20] : 0x00;
}

void txt_fill(uint8_t code, uint8_t attr)
{
    memset((uint8_t *)VRAM_TEXT, code, 1000);
    memset((uint8_t *)VRAM_ATTR, attr, 1000);
}

void txt_putc(uint8_t row, uint8_t col, uint8_t code, uint8_t attr)
{
    uint16_t i = (uint16_t)row * 40 + col;

    VRAM_TEXT[i] = code;
    VRAM_ATTR[i] = attr;
}

void txt_puts(uint8_t row, uint8_t col, const char *s, uint8_t attr)
{
    uint16_t i = (uint16_t)row * 40 + col;

    while (*s) {
        VRAM_TEXT[i] = txt_code(*s++);
        VRAM_ATTR[i] = attr;
        ++i;
    }
}

void txt_dec2(uint8_t row, uint8_t col, uint8_t v, uint8_t attr)
{
    txt_putc(row, col, 0x20 + v / 10, attr);
    txt_putc(row, col + 1, 0x20 + v % 10, attr);
}

void txt_attr(uint8_t row, uint8_t col, uint8_t n, uint8_t attr)
{
    memset((uint8_t *)VRAM_ATTR + (uint16_t)row * 40 + col, attr, n);
}
