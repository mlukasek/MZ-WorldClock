; Startup code of MZ-WorldClock for the Sharp MZ-700 / MZ-800 (one MZF for all of them).
;
; Derived from z88dk lib/target/mz/classic/mz_crt0.asm (Stefano Bodrato, UncleBod; z88dk Clarified
; Artistic License). Changes:
;   - ORG 2000h: on the MZ-800, IN (E0h) maps the CG-ROM over 1000h-1FFFh together with the VRAM,
;     so neither code nor stack may live there;
;   - DI first: the monitor starts the program with interrupts enabled, we never use them;
;   - our own stack below 8000h (the monitor's one is at 10F0h, inside the CG-ROM window);
;   - no console, no atexit stack; the exit restores the monitor's SP and jumps to its command loop
;     (00ADh in 1Z-013A, 1Z-013B and 1Z-009B). Restoring the machine (MZ-700 mode, CG-RAM, clock,
;     interrupts) is done by the program before main() returns.

    MODULE  wc_crt0

    defc    crt0 = 1
    INCLUDE "zcc_opt.def"

    EXTERN  _main

    PUBLIC  __Exit
    PUBLIC  l_dcal

IF !DEFINED_CRT_ORG_CODE
    defc    CRT_ORG_CODE = $2000
ENDIF

    defc    CONSOLE_COLUMNS = 40
    defc    CONSOLE_ROWS = 25

    defc    TAR__no_ansifont = 1
    defc    TAR__clib_exit_stack_size = 0
    defc    TAR__register_sp = $8000
    defc    TAR__crt_enable_eidi = 0
    defc    __CPU_CLOCK = 3546875
    INCLUDE "crt/classic/crt_rules.inc"

; Uninitialised variables at A000h (zeroed at start, not stored in the MZF). A000h-BFFFh is RAM in every
; mode we use (the MZ-800 320x200 VRAM window is 8000h-9FFFh). The classic crt_rules do not map
; CRT_ORG_BSS, so it is done here.
IF DEFINED_CRT_ORG_BSS
    defc    __crt_org_bss = CRT_ORG_BSS
ELSE
    defc    __crt_org_bss = $A000
ENDIF

    org     CRT_ORG_CODE

    jp      start

; Test hook at 2003h, written by the emulator tests (tools/emu) after loading and before running:
; struct test_hook in src/mz/machine.h. Zero in normal use.
    PUBLIC  _test_hook
_test_hook:
    defm    "WCTH"                      ; 2003h magic
    defb    0                           ; 2007h flags: bit 0 = utc below is valid, skip the time dialog
    defb    0, 0, 0, 0                  ; 2008h UTC, seconds since 2000-01-01, little endian
    defb    0, 0, 0, 0, 0, 0, 0         ; 200Ch reserved

start:
    di
    ld      (__restore_sp_onexit+1),sp  ; the monitor's stack, valid again after the exit
    INCLUDE "crt/classic/crt_init_sp.inc"
    call    crt0_init
    INCLUDE "crt/classic/crt_init_heap.inc"

    call    _main

__Exit:
    call    crt0_exit
__restore_sp_onexit:
    ld      sp,0
    jp      $00AD                       ; monitor command loop

l_dcal:
    jp      (hl)                        ; function pointer calls

    INCLUDE "crt/classic/crt_runtime_selection.inc"

    INCLUDE "crt/classic/crt_section.inc"
