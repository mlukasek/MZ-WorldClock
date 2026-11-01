/* Low-level hardware access of the Sharp MZ-700 / MZ-800 (hw.asm). */
#ifndef WC_HW_H
#define WC_HW_H

#include <stdint.h>

void hw_out(uint16_t port_value) __z88dk_fastcall;  /* low byte = port, high byte = value */
uint8_t hw_in(uint8_t port) __z88dk_fastcall;
void hw_ei(void);
void hw_di(void);

#define HW_OUT(port, value) hw_out((uint16_t)(port) | ((uint16_t)(value) << 8))

/* Memory-mapped registers in MZ-700 mode */
#define MEM8(addr) (*(volatile uint8_t *)(addr))
#define VRAM_TEXT ((volatile uint8_t *)0xD000)
#define VRAM_ATTR ((volatile uint8_t *)0xD800)
#define PPI_PA MEM8(0xE000)   /* 8255 port A: keyboard column, cursor timer reset */
#define PPI_PB MEM8(0xE001)   /* 8255 port B: keyboard rows (active low) */
#define PPI_PC MEM8(0xE002)   /* 8255 port C: bit 7 = /VBLK */
#define PPI_CTRL MEM8(0xE003)

#endif
