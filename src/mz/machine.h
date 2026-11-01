/* The machine: detection, start and exit (MZ-700 EU / JP, MZ-800). */
#ifndef WC_MACHINE_H
#define WC_MACHINE_H

#include <stdint.h>

#define MODEL_MZ700 0        /* and anything MZ-700 compatible without the MZ-800's GDG */
#define MODEL_MZ800 1        /* GDG present: the modern look in 320x200 is possible */
#define MODEL_MZ1500 2       /* Japanese, NTSC, MZ-700 compatible; has a PCG (not used yet) */

struct machine {
    uint8_t model;       /* MODEL_... */
    uint8_t jp;          /* Japanese monitor 1Z-009 (and CG-ROM with hiragana) */
    uint8_t ntsc;        /* 262 lines per frame (60 Hz), else 312 (50 Hz) */
    uint16_t lines;      /* measured lines per frame */
    uint16_t line_hz;    /* line frequency (the monitor's 1 s count: 15611 PAL, 15700 NTSC) */
};

extern struct machine mach;

/* Test hook at 2003h (crt0.asm), written by the emulator tests */
struct test_hook {
    char magic[4];       /* "WCTH" */
    uint8_t flags;       /* bit 0: utc is valid, skip the time dialog */
    uint32_t utc;
    uint8_t reserved[7];
};
#define TEST_TIME_VALID 1
extern struct test_hook test_hook;

void machine_init(void);
/* Back to the monitor: its clock set to `local_secs` (seconds since local midnight), interrupts on. */
void machine_exit(uint32_t local_secs);

#endif
