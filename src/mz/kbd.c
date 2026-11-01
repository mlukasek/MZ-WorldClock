/* Keyboard read straight from the 8255 (MZ-700 memory map): PA0-3 select one of 10 columns, PB reads its
 * 8 keys (active low). The matrix is the same on the MZ-700 (EU, JP) and the MZ-800. */
#include "kbd.h"
#include "hw.h"

/* [column][bit] -> key code */
static const uint8_t keymap[10][8] = {
    {K_CR, ':', ';', 0, 0, 0, 0, 0},                        /* ALPHA, down arrow, GRAPH, BLANK unused */
    {0, 0, 0, ']', '[', '@', 'Z', 'Y'},
    {'X', 'W', 'V', 'U', 'T', 'S', 'R', 'Q'},
    {'P', 'O', 'N', 'M', 'L', 'K', 'J', 'I'},
    {'H', 'G', 'F', 'E', 'D', 'C', 'B', 'A'},
    {'8', '7', '6', '5', '4', '3', '2', '1'},
    {'.', ',', '9', '0', ' ', '-', '^', '\\'},
    {'/', '?', K_LEFT, K_RIGHT, K_DOWN, K_UP, K_DEL, 0},   /* INST unused */
    {0, 0, 0, 0, 0, 0, 0, K_BREAK},                       /* SHIFT, CTRL unused */
    {0, 0, 0, 0, 0, 0, 0, 0},                             /* F1-F5 unused */
};

static uint8_t held[10];

uint8_t kbd_get(void)
{
    uint8_t col, bit, now, fresh;
    uint8_t key = K_NONE;

    for (col = 0; col < 10; ++col) {
        IO_WR(R_PA, 0xF0 | col);          /* PA4-7 high: joystick strobes off, cursor timer runs */
        now = ~io_rd(R_PB);
        fresh = now & ~held[col];
        held[col] = now;
        if (fresh && key == K_NONE) {
            for (bit = 0; bit < 8; ++bit) {
                if ((fresh >> bit) & 1 && keymap[col][bit]) {
                    key = keymap[col][bit];
                    break;
                }
            }
        }
    }
    return key;
}

void kbd_wait_release(void)
{
    uint8_t col, any;

    do {
        any = 0;
        for (col = 0; col < 10; ++col) {
            IO_WR(R_PA, 0xF0 | col);
            if (io_rd(R_PB) != 0xFF)
                any = 1;
        }
    } while (any);
}
