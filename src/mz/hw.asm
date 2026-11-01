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
    PUBLIC  _land_decode

    SECTION bss_user
ld_end:
    defs    2
ld_ptr:
    defs    2
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
; plane II = land & (day | dither) (land by day, dithered by night); in the 16-colour mode planes III and IV
; cleared (the texts over the map use them). _row_land, _row_day: 40 bytes each, in
; screen order; _row_dither: 55h / AAh. (modview.c; the same as tools/modref.py map_row.)
_row_out:
    push    ix
    ld      b,h
    ld      c,l
    push    bc
    ld      a,$81
    out     ($CC),a                     ; write format: REPLACE colour 1: plane I, planes II-IV cleared
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

; void land_decode(const uint8_t *rle) __z88dk_fastcall;
; One row of the land mask (tools/mkmodern.py rle_bits: runs starting with sea, a run of 255 goes on with
; the next byte; 320 pixels in all) into _row_land, bit 0 = the leftmost pixel, not rotated.
; HL = output byte, C = bit in it, B = run length, DE = scratch, IXL = colour (1 = land), IXH = the run byte;
; the RLE pointer in ld_ptr.
_land_decode:
    push    ix
    ld      (ld_ptr),hl
    ld      hl,_row_land
    ld      b,40
ld_clear:
    ld      (hl),0
    inc     hl
    djnz    ld_clear
    ld      (ld_end),hl                 ; _row_land + 40
    ld      hl,_row_land
    ld      c,0
    ld      ixl,0
ld_run:
    ld      de,(ld_end)                 ; done when HL reaches the end (all 320 pixels)
    or      a
    sbc     hl,de
    add     hl,de
    jr      z,ld_done
    ld      de,(ld_ptr)
    ld      a,(de)
    inc     de
    ld      (ld_ptr),de
    ld      ixh,a
    ld      b,a
    or      a
    jr      z,ld_next                   ; a 0 after a 255: nothing to draw
    ld      a,ixl
    or      a
    jr      nz,ld_land
    ld      a,c                         ; sea: skip B pixels
    add     a,b                         ; C + B, carry = bit 8
    ld      b,a
    rra                                 ; (C + B) >> 1 with bit 8
    srl     a
    srl     a                           ; (C + B) >> 3: whole bytes to skip
    add     a,l
    ld      l,a
    jr      nc,ld_sea1
    inc     h
ld_sea1:
    ld      a,b
    and     7
    ld      c,a
    jr      ld_next
ld_land:                                ; land: set B pixels from bit C
    ld      a,c
    or      a
    ld      a,b
    jr      z,ld_whole
    add     a,c                         ; C + B
    jr      c,ld_first
    cp      8
    jr      nc,ld_first
    ld      b,a                         ; the run ends inside this byte: bits [C, C + B) = lo[C + B] ^ lo[C]
    ld      a,c
    call    ld_lo
    ld      c,a
    ld      a,b
    call    ld_lo
    xor     c
    or      (hl)
    ld      (hl),a
    ld      c,b                         ; the next bit
    jr      ld_next
ld_first:                               ; bits [C, 8) of this byte = ~lo[C]; A = C + B (mod 256)
    ld      b,a
    ld      a,c
    call    ld_lo
    cpl
    or      (hl)
    ld      (hl),a
    inc     hl
    ld      a,b
    sub     8                           ; B - (8 - C), 0-254 (the 8-bit wrap of C + B cancels out)
    ld      c,0
ld_whole:                               ; A = pixels left, from bit 0: whole bytes, then the rest
    cp      8
    jr      c,ld_tail
    ld      (hl),$FF
    inc     hl
    sub     8
    jr      ld_whole
ld_tail:
    ld      c,a                         ; the next bit
    or      a
    jr      z,ld_next
    call    ld_lo
    ld      (hl),a                      ; a fresh byte: nothing set in it yet
ld_next:
    ld      a,ixh                       ; the colour changes unless the run byte was 255
    inc     a
    jr      z,ld_run
    ld      a,ixl
    xor     1
    ld      ixl,a
    jr      ld_run
ld_done:
    pop     ix
    ret

; A = (1 << A) - 1 for A = 0-8; DE destroyed
ld_lo:
    ld      de,ld_lo_tab
    add     a,e
    ld      e,a
    jr      nc,ld_lo1
    inc     d
ld_lo1:
    ld      a,(de)
    ret

ld_lo_tab:
    defb    $00, $01, $03, $07, $0F, $1F, $3F, $7F, $FF

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
