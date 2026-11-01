; Port I/O and monitor helpers for C (the same calling convention for sccz80 and zsdcc: fastcall, the argument
; in HL or DEHL, the result in L).

    SECTION code_user

    PUBLIC  _hw_out
    PUBLIC  _hw_in
    PUBLIC  _hw_ei
    PUBLIC  _hw_di
    PUBLIC  _mon_set_clock
    PUBLIC  _mon_cls
    PUBLIC  _hw_out_bc
    PUBLIC  _io_rd
    PUBLIC  _io_wr
    PUBLIC  _io_native
    PUBLIC  _row_out
    PUBLIC  _row_land
    PUBLIC  _row_day
    PUBLIC  _row_dither

    SECTION bss_user
_io_native:
    defs    1
_row_land:
    defs    40
_row_day:
    defs    40
_row_dither:
    defs    1

    SECTION code_user

; void hw_out(uint16_t port_value) __z88dk_fastcall;   L = port, H = value
_hw_out:
    ld      c,l
    ld      a,h
    out     (c),a
    ret

; uint8_t hw_in(uint8_t port) __z88dk_fastcall;
_hw_in:
    ld      c,l
    in      a,(c)
    ld      l,a
    ld      h,0
    ret

; void hw_out_bc(uint32_t port_value) __z88dk_fastcall;   HL = 16-bit port (the GDG's xxCFh family), E = value
_hw_out_bc:
    ld      b,h
    ld      c,l
    ld      a,e
    out     (c),a
    ret

; The 8255 and the 8253: memory-mapped at E000h-E007h in MZ-700 mode, ports D0h-D7h in MZ-800 mode
; (io_native = 1). reg: 0-3 = 8255 PA, PB, PC, control; 4-7 = 8253 counters 0-2, control.
; uint8_t io_rd(uint8_t reg) __z88dk_fastcall;
_io_rd:
    ld      a,(_io_native)
    or      a
    jr      nz,io_rd_port
    ld      h,$E0
    ld      l,(hl)
    ret
io_rd_port:
    ld      a,l
    add     a,$D0
    ld      c,a
    in      l,(c)
    ret

; void io_wr(uint16_t reg_value) __z88dk_fastcall;   L = reg, H = value
_io_wr:
    ld      a,(_io_native)
    or      a
    jr      nz,io_wr_port
    ld      a,h
    ld      h,$E0
    ld      (hl),a
    ret
io_wr_port:
    ld      a,l
    add     a,$D0
    ld      c,a
    out     (c),h
    ret

; void row_out(volatile uint8_t *vram_row) __z88dk_fastcall;
; One map row of the MZ-800's modern look into VRAM (mapped): plane I = ~land & day (sea by day),
; plane II = land & (day | dither) (land by day, dithered by night). _row_land, _row_day: 40 bytes each, in
; screen order; _row_dither: 55h / AAh. (modview.c; the same as tools/modref.py map_row.)
_row_out:
    push    ix
    ld      b,h
    ld      c,l
    push    bc
    ld      a,$01
    out     ($CC),a                     ; write format: SINGLE, plane I
    ld      hl,_row_land
    ld      de,_row_day
    ld      ixl,40
row_p1:
    ld      a,(hl)
    cpl
    ex      de,hl
    and     (hl)
    ex      de,hl
    ld      (bc),a
    inc     hl
    inc     de
    inc     bc
    dec     ixl
    jr      nz,row_p1
    pop     bc
    ld      a,$02
    out     ($CC),a                     ; SINGLE, plane II
    ld      hl,_row_land
    ld      de,_row_day
    ld      a,(_row_dither)
    ld      ixh,a
    ld      ixl,40
row_p2:
    ld      a,(de)
    or      ixh
    and     (hl)
    ld      (bc),a
    inc     hl
    inc     de
    inc     bc
    dec     ixl
    jr      nz,row_p2
    pop     ix
    ret

; void hw_ei(void);
_hw_ei:
    ei
    ret

; void hw_di(void);
_hw_di:
    di
    ret

; void mon_set_clock(uint32_t secs) __z88dk_fastcall;   DEHL = local seconds since midnight (0-86399)
; Starts the monitor's clock (TIMST, 0033h: A = 0 AM / 1 PM, DE = seconds in the half day), which reprograms
; CTC1/CTC2 at E004h-E007h and ends with EI. MZ-700 memory map only.
_mon_set_clock:
    ld      a,e
    or      a
    jr      nz,mon_pm_big               ; 65536 and more: certainly PM
    ld      de,43200
    or      a
    sbc     hl,de
    jr      nc,mon_pm                   ; HL >= 43200: PM, HL already reduced
    add     hl,de
    xor     a                           ; AM
    jr      mon_set
mon_pm_big:
    ld      de,65536-43200
    add     hl,de
mon_pm:
    ld      a,1
mon_set:
    ex      de,hl
    call    $0033
    ret

; void mon_cls(void);   clears the screen through the monitor (PRNT 0012h, code 16h), so that its cursor
; state matches the screen.
_mon_cls:
    ld      a,$16
    call    $0012
    ret
