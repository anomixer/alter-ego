.setcpu "6502"
.importzp c_sp
.import incsp4
.export _oam_spr, _vera_oam_init, _vera_oam_present

.ifndef VERA_BASE
VERA_BASE = $C200
.endif
ADDR_L = VERA_BASE+$00
ADDR_M = VERA_BASE+$01
ADDR_H = VERA_BASE+$02
DATA = VERA_BASE+$03

.ifdef FTM_VERA
.segment "FTM_HIGH_BSS"
.else
.segment "BSS"
.endif
oam: .res 256
.segment "BSS"
dirty: .res 8
sprid: .res 1
mask: .res 1
zvalue: .res 1

.segment "RODATA"
bits: .byte 1,2,4,8,16,32,64,128

.segment "CODE"
_vera_oam_init:
        ; Initialize all 128 hardware entries, including the unused half.
        lda #0
        sta ADDR_L
        lda #$FC
        sta ADDR_M
        lda #$11
        sta ADDR_H
        ldx #4
        ldy #0
        lda #0
@clear: sta DATA
        iny
        bne @clear
        dex
        bne @clear
        ldx #0
@entry: lda #0
        sta oam,x
        sta oam+2,x
        sta oam+3,x
        lda #240
        sta oam+1,x
        txa
        clc
        adc #4
        tax
        bne @entry
        ldx #7
        lda #$FF
@dirty: sta dirty,x
        dex
        bpl @dirty
        jmp _vera_oam_present

; fastcall: id in A, attr/tile/y/x at c_sp+0/1/2/3. Clean four bytes.
_oam_spr:
        sta sprid
        cmp #64
        bcs @return
        asl
        asl
        tax
        ldy #3
        lda (c_sp),y
        cmp oam,x
        bne @copy
        dey
        lda (c_sp),y
        cmp oam+1,x
        bne @copy
        dey
        lda (c_sp),y
        cmp oam+2,x
        bne @copy
        dey
        lda (c_sp),y
        cmp oam+3,x
        beq @return
@copy:  ldy #3
        lda (c_sp),y
        sta oam,x
        dey
        lda (c_sp),y
        sta oam+1,x
        dey
        lda (c_sp),y
        sta oam+2,x
        dey
        lda (c_sp),y
        sta oam+3,x
        lda sprid
        lsr
        lsr
        lsr
        tay
        lda sprid
        and #7
        tax
        lda bits,x
        ora dirty,y
        sta dirty,y
@return:
        lda sprid
        clc
        adc #1
        ldx #0
        jmp incsp4

_vera_oam_present:
        lda #$11
        sta ADDR_H
        lda #1
        sta mask
        ldy #0
        ldx #0
@entry:
        lda dirty,y
        and mask
        beq @next
        txa                     ; X = id*4, hardware address low = id*8
        asl
        sta ADDR_L
        lda #$FC
        cpx #128
        bcc :+
        lda #$FD
:       sta ADDR_M
        lda oam+2,x
        sta DATA
        lda #$08                ; 4bpp tile graphics at $10000
        sta DATA
        lda oam,x
        clc
        adc #32                 ; center NES viewport
        sta DATA
        lda #0
        adc #0
        sta DATA
        lda oam+1,x
        sta DATA
        lda #0
        sta DATA
        lda oam+1,x
        cmp #240
        bcs @hidden
        lda oam+3,x
        lsr
        lsr
        lsr
        lsr
        lsr
        lsr
        ora #$0C                ; front of both layers + NES flips
        sta zvalue
        lda oam+3,x
        and #$20
        beq @front
        lda zvalue
        and #$F7                ; NES background priority -> VERA z=1
        bne @z
@front: lda zvalue
        bne @z
@hidden:
        lda #0
@z:     sta DATA
        lda oam+3,x
        and #3
        ora #4                  ; NES sprite palettes in VERA banks 4..7
        sta DATA
@next:  txa
        clc
        adc #4
        tax
        beq @done
        asl mask
        beq @group
        jmp @entry
@group:
        lda #0
        sta dirty,y
        iny
        lda #1
        sta mask
        jmp @entry
@done:  lda #0
        sta dirty,y
        rts
