; Port I/O and monitor helpers for C (the same calling convention for sccz80 and zsdcc: fastcall, the argument
; in HL or DEHL, the result in L).

    SECTION code_user

    PUBLIC  _hw_out
    PUBLIC  _hw_in
    PUBLIC  _hw_ei
    PUBLIC  _hw_di
    PUBLIC  _mon_set_clock
    PUBLIC  _mon_cls

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
