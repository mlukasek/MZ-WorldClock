; Drawing in the MZ-800's 320x200 VRAM (mapped at 8000h, the CG-ROM at 1000h; gfx800.h). zsdcc's calling
; convention: the arguments on the stack from the right, 8-bit ones as one byte, the caller removes them;
; IX kept. The tools/clockref.py reference does the same, pixel for pixel.

    SECTION code_user

    PUBLIC  _gfx_ctext
    PUBLIC  _gfx_ptext
    PUBLIC  _gfx_hspan
    PUBLIC  _gfx_line

    EXTERN  _txt_ascii

    defc    VRAM = $8000
    defc    CGROM = $1000

; HL = VRAM + A * 40; DE destroyed
gfx_row:
    ld      l,a
    ld      h,0
    add     hl,hl
    add     hl,hl
    add     hl,hl
    ld      d,h
    ld      e,l
    add     hl,hl
    add     hl,hl
    add     hl,de
    ld      de,VRAM
    add     hl,de
    ret

; A = an ASCII character (20h-5Fh, else a space) -> HL = its glyph in the CG-ROM; DE destroyed
gfx_glyph:
    sub     $20
    cp      $40
    jr      c,gg_in
    xor     a
    jr      gg_code
gg_in:
    ld      e,a
    ld      d,0
    ld      hl,_txt_ascii
    add     hl,de
    ld      a,(hl)
gg_code:
    ld      l,a
    ld      h,0
    add     hl,hl
    add     hl,hl
    add     hl,hl
    ld      de,CGROM
    add     hl,de
    ret

; DE >>= 3
shr3:
    srl     d
    rr      e
    srl     d
    rr      e
    srl     d
    rr      e
    ret

; void gfx_ctext(uint8_t bx, uint8_t y, const char *s, uint8_t colour, uint8_t sx, uint8_t sy);
; Opaque text (REPLACE): each glyph pixel sx (1-4) pixels wide, sy rows tall.
; IX: +0 bx, +1 y, +2 s, +4 colour, +5 sx, +6 sy
_gfx_ctext:
    push    ix
    ld      ix,4
    add     ix,sp
    ld      a,(ix+4)
    or      $80
    out     ($CC),a
ct_char:
    ld      l,(ix+2)
    ld      h,(ix+3)
    ld      a,(hl)
    or      a
    jr      z,ct_done
    inc     hl
    ld      (ix+2),l
    ld      (ix+3),h
    call    gfx_glyph
    push    hl
    ld      a,(ix+1)
    call    gfx_row
    ld      e,(ix+0)
    ld      d,0
    add     hl,de
    ex      de,hl                       ; DE = VRAM
    pop     hl                          ; HL = glyph
    ld      c,8
ct_row:
    ld      a,(hl)
    inc     hl
    push    hl
    call    ct_expand
    ld      b,(ix+6)
ct_rep:
    push    bc
    push    de
    ld      hl,ct_e
    ld      c,(ix+5)
    ld      b,0
    ldir
    pop     de
    ld      hl,40
    add     hl,de
    ex      de,hl
    pop     bc
    djnz    ct_rep
    pop     hl
    dec     c
    jr      nz,ct_row
    ld      a,(ix+0)
    add     a,(ix+5)
    ld      (ix+0),a
    jr      ct_char
ct_done:
    pop     ix
    ret

; A = a glyph row -> ct_e: each pixel (IX+5) pixels wide, bit 0 = the left one; BC, DE kept
ct_expand:
    push    bc
    push    de
    ld      hl,ct_e
    ld      b,a
    ld      a,(ix+5)
    dec     a
    jr      nz,ce_wide
    ld      (hl),b
    jr      ce_done
ce_wide:
    ld      c,8                         ; glyph pixels
    ld      e,0                         ; bits gathered in D
ce_px:
    ld      a,(ix+5)
ce_rep:
    push    af
    ld      a,b
    rra                                 ; carry = this glyph pixel
    rr      d                           ; in from the top: the first one ends at bit 0
    pop     af
    inc     e
    bit     3,e
    jr      z,ce_next
    ld      (hl),d
    inc     hl
    ld      e,0
ce_next:
    dec     a
    jr      nz,ce_rep
    srl     b
    dec     c
    jr      nz,ce_px
ce_done:
    pop     de
    pop     bc
    ret

; void gfx_ptext(uint16_t x, uint8_t y, const char *s, uint8_t colour);
; Only the glyph pixels (PSET), at any x. IX: +0 x, +2 y, +3 s, +5 colour
_gfx_ptext:
    push    ix
    ld      ix,4
    add     ix,sp
    ld      a,(ix+5)
    or      $C0
    out     ($CC),a
pt_char:
    ld      l,(ix+3)
    ld      h,(ix+4)
    ld      a,(hl)
    or      a
    jr      z,pt_done
    inc     hl
    ld      (ix+3),l
    ld      (ix+4),h
    call    gfx_glyph
    push    hl
    ld      a,(ix+2)
    call    gfx_row
    ld      e,(ix+0)
    ld      d,(ix+1)
    ld      a,e
    and     7
    ld      c,a                         ; the shift
    call    shr3
    add     hl,de
    ex      de,hl                       ; DE = VRAM
    pop     hl                          ; HL = glyph
    ld      b,8
pt_row:
    push    bc
    ld      a,(hl)
    inc     hl
    push    hl
    ld      l,a
    ld      h,0
    ld      b,c
    inc     b
    jr      pt_sh_next
pt_sh:
    add     hl,hl
pt_sh_next:
    djnz    pt_sh
    ex      de,hl                       ; HL = VRAM, DE = the shifted row
    ld      (hl),e
    inc     hl
    ld      a,c
    or      a
    jr      z,pt_one
    ld      (hl),d
pt_one:
    ld      de,39
    add     hl,de
    ex      de,hl                       ; DE = VRAM, the next row
    pop     hl
    pop     bc
    djnz    pt_row
    ld      l,(ix+0)
    ld      h,(ix+1)
    ld      de,8
    add     hl,de
    ld      (ix+0),l
    ld      (ix+1),h
    jr      pt_char
pt_done:
    pop     ix
    ret

; void gfx_hspan(uint16_t x0, uint16_t x1, uint8_t y, uint8_t colour);
; Pixels x0..x1 (PSET). IX: +0 x0, +2 x1, +4 y, +5 colour
_gfx_hspan:
    push    ix
    ld      ix,4
    add     ix,sp
    ld      a,(ix+5)
    or      $C0
    out     ($CC),a
    ld      a,(ix+4)
    call    gfx_row
    ld      e,(ix+0)
    ld      d,(ix+1)
    ld      a,e
    and     7
    ld      b,a
    call    shr3
    push    de                          ; the first byte
    ld      a,$FF
    inc     b
    jr      hs_m0_next
hs_m0:
    add     a,a
hs_m0_next:
    djnz    hs_m0
    ld      c,a                         ; FFh << (x0 & 7)
    ld      e,(ix+2)
    ld      d,(ix+3)
    ld      a,e
    and     7
    xor     7
    ld      b,a
    call    shr3
    ld      a,$FF
    inc     b
    jr      hs_m1_next
hs_m1:
    srl     a
hs_m1_next:
    djnz    hs_m1
    ld      b,a                         ; FFh >> (7 - (x1 & 7))
    ld      a,e                         ; the last byte
    pop     de
    add     hl,de
    sub     e
    jr      nz,hs_more
    ld      a,c
    and     b
    ld      (hl),a
    pop     ix
    ret
hs_more:
    ld      (hl),c
    inc     hl
    dec     a
    jr      z,hs_last
hs_full:
    ld      (hl),$FF
    inc     hl
    dec     a
    jr      nz,hs_full
hs_last:
    ld      (hl),b
    pop     ix
    ret

; void gfx_line(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t colour, uint8_t width);
; A line on the screen (no clipping), |x1 - x0| and |y1 - y0| below 256, width 1-3: copies shifted by 1 pixel
; across it (sideways when steep, else up and down), from -((width - 1) >> 1). Bresenham along the major
; axis: err = major / 2; at each pixel: plot, step along the major axis, err -= minor, when below 0 err += major
; and a step along the minor axis. IX: +0 x0, +2 y0, +4 x1, +6 y1, +8 colour, +9 width
_gfx_line:
    push    ix
    ld      ix,4
    add     ix,sp
    ld      a,(ix+8)
    or      $C0
    out     ($CC),a
    ld      l,(ix+4)
    ld      h,(ix+5)
    ld      e,(ix+0)
    ld      d,(ix+1)
    xor     a
    sbc     hl,de                       ; x1 - x0
    ld      c,0
    jr      nc,ln_xpos
    inc     c                           ; to the left
    xor     a
    sub     l
    ld      l,a
ln_xpos:
    ld      a,l
    ld      (ln_adx),a
    ld      a,c
    ld      (ln_left),a
    ld      a,(ix+6)
    sub     (ix+2)                      ; y1 - y0
    ld      hl,40
    jr      nc,ln_ypos
    neg
    ld      hl,-40
ln_ypos:
    ld      (ln_ady),a
    ld      (ln_dy),hl
    ld      b,a
    ld      a,(ln_adx)
    cp      b                           ; carry: adx < ady, steep
    ld      a,0
    rla
    ld      (ln_steep),a
    ld      l,(ix+0)
    ld      h,(ix+1)
    ld      (ln_x),hl
    ld      a,(ix+2)
    ld      (ln_y),a
    ld      a,(ix+9)
    ld      (ln_w),a
    dec     a
    srl     a
    neg
    ld      c,a                         ; the first copy's offset
    call    ln_offset
ln_copy:
    call    ln_draw
    ld      c,1
    call    ln_offset
    ld      hl,ln_w
    dec     (hl)
    jr      nz,ln_copy
    pop     ix
    ret

; the start moved by C (signed): x when steep, else y
ln_offset:
    ld      a,(ln_steep)
    or      a
    jr      z,lo_y
    ld      hl,(ln_x)
    ld      a,c
    ld      e,a
    rla
    sbc     a,a
    ld      d,a
    add     hl,de
    ld      (ln_x),hl
    ret
lo_y:
    ld      a,(ln_y)
    add     a,c
    ld      (ln_y),a
    ret

; one copy from (ln_x, ln_y): HL = the VRAM byte, C = the pixel's bit, DE = the row step, B = pixels
ln_draw:
    ld      a,(ln_y)
    call    gfx_row
    ld      de,(ln_x)
    ld      a,e
    and     7
    ld      b,a
    call    shr3
    add     hl,de
    ld      a,1
    inc     b
    jr      ld_bit_next
ld_bit:
    add     a,a
ld_bit_next:
    djnz    ld_bit
    ld      c,a
    ld      de,(ln_dy)
    ld      a,(ln_steep)
    or      a
    jr      nz,ln_tall
    ld      a,(ln_adx)                  ; x is the major axis
    ld      b,a
    inc     b
    srl     a
    ld      (ln_err),a
lw_loop:
    ld      (hl),c
    call    ln_xstep
    ld      a,(ln_err)
    push    hl
    ld      hl,ln_ady
    sub     (hl)
    jr      nc,lw_keep
    ld      hl,ln_adx
    add     a,(hl)
    pop     hl
    add     hl,de
    jr      lw_next
lw_keep:
    pop     hl
lw_next:
    ld      (ln_err),a
    djnz    lw_loop
    ret
ln_tall:
    ld      a,(ln_ady)                  ; y is the major axis
    ld      b,a
    inc     b
    srl     a
    ld      (ln_err),a
lt_loop:
    ld      (hl),c
    add     hl,de
    ld      a,(ln_err)
    push    hl
    ld      hl,ln_adx
    sub     (hl)
    jr      nc,lt_keep
    ld      hl,ln_ady
    add     a,(hl)
    pop     hl
    ld      (ln_err),a
    call    ln_xstep
    jr      lt_next
lt_keep:
    pop     hl
    ld      (ln_err),a
lt_next:
    djnz    lt_loop
    ret

; one pixel right or left: C = the bit, HL = the byte
ln_xstep:
    ld      a,(ln_left)
    or      a
    jr      nz,lx_left
    rlc     c
    ret     nc
    inc     hl
    ret
lx_left:
    rrc     c
    ret     nc
    dec     hl
    ret

    SECTION bss_user
ct_e:
    defs    4
ln_x:
    defs    2
ln_dy:
    defs    2
ln_y:
    defs    1
ln_adx:
    defs    1
ln_ady:
    defs    1
ln_left:
    defs    1
ln_steep:
    defs    1
ln_w:
    defs    1
ln_err:
    defs    1
