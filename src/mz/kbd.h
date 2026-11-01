/* Keyboard read straight from the 8255 (MZ-700 memory map). */
#ifndef WC_KBD_H
#define WC_KBD_H

#include <stdint.h>

/* Key codes: ASCII for letters (upper case), digits and space, plus these */
#define K_NONE 0
#define K_DEL 0x08
#define K_CR 0x0D
#define K_DOWN 0x11
#define K_UP 0x12
#define K_RIGHT 0x13
#define K_LEFT 0x14
#define K_BREAK 0x1B

uint8_t kbd_get(void);       /* a newly pressed key (one per call), or K_NONE */
void kbd_wait_release(void); /* until no key is pressed */

#endif
