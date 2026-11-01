/* Low-level hardware access of the Sharp MZ-700 / MZ-800 / MZ-1500 (hw.asm). */
#ifndef WC_HW_H
#define WC_HW_H

#include <stdint.h>

void hw_out(uint16_t port_value) __z88dk_fastcall;  /* low byte = port, high byte = value */
uint8_t hw_in(uint8_t port) __z88dk_fastcall;
void hw_out_bc(uint32_t port_value) __z88dk_fastcall; /* bits 0-15 = 16-bit port, bits 16-23 = value */
void hw_ei(void);
void hw_di(void);
void mon_set_clock(uint32_t secs) __z88dk_fastcall; /* monitor clock (TIMST) := local seconds of the day, EI */
void mon_cls(void);                                 /* clear the screen through the monitor */

#define HW_OUT(port, value) hw_out((uint16_t)(port) | ((uint16_t)(value) << 8))
#define HW_OUT_BC(port, value) hw_out_bc((uint32_t)(port) | ((uint32_t)(value) << 16))

/* The 8255 and the 8253: memory-mapped at E000h-E007h in MZ-700 mode, ports D0h-D7h in the MZ-800's own mode
 * (io_native = 1, set by gfx800.c) */
extern uint8_t io_native;
uint8_t io_rd(uint8_t reg) __z88dk_fastcall;
void io_wr(uint16_t reg_value) __z88dk_fastcall;
#define IO_WR(reg, value) io_wr((uint16_t)(reg) | ((uint16_t)(value) << 8))
#define R_PA 0               /* 8255 port A: keyboard column, cursor timer reset */
#define R_PB 1               /* 8255 port B: keyboard rows (active low) */
#define R_PC 2               /* 8255 port C: bit 7 = /VBLK (1 while the screen is drawn) */
#define R_PPI 3              /* 8255 control: bit set/reset of port C (PC2 = INT enable) */
#define R_CTC0 4             /* 8253 counter 0: sound */
#define R_CTC1 5             /* 8253 counter 1: clocked by HSYNC */
#define R_CTC2 6             /* 8253 counter 2: clocked by OUT1, OUT2 -> INT (with PC2) */
#define R_CTC 7              /* 8253 control */

/* Memory in MZ-700 mode */
#define MEM8(addr) (*(volatile uint8_t *)(addr))
#define VRAM_TEXT ((volatile uint8_t *)0xD000)
#define VRAM_ATTR ((volatile uint8_t *)0xD800)

#endif
