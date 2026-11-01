; Port I/O and interrupt helpers for C (the same calling convention for sccz80 and zsdcc: fastcall,
; the argument in HL, the result in L).

    SECTION code_user

    PUBLIC  _hw_out
    PUBLIC  _hw_in
    PUBLIC  _hw_ei
    PUBLIC  _hw_di

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
