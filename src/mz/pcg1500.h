/* The PCG of the MZ-1500: the half cell of the seconds bar (1 s steps). */
#ifndef WC_PCG1500_H
#define WC_PCG1500_H

#include <stdint.h>

void pcg_init(void);                        /* the glyph into the PCG, MZ-1500 mode with text under the PCG */
void pcg_half(uint8_t cell, uint8_t on);    /* the half glyph over bar cell `cell` on / off */
void pcg_exit(void);                        /* MZ-700 mode again (the monitor's CLS restores the cell bytes) */

#endif
