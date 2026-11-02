.setcpu "6502"
.ifndef VERA_BASE
VERA_BASE = $C200
.endif
VERA_ADDR_L = VERA_BASE+$00
VERA_ADDR_M = VERA_BASE+$01
VERA_ADDR_H = VERA_BASE+$02
VERA_DATA0  = VERA_BASE+$03
VERA_CTRL   = VERA_BASE+$05
VERA_DC_VID = VERA_BASE+$09
VERA_DC_HSC = VERA_BASE+$0A
VERA_DC_VSC = VERA_BASE+$0B
VERA_L0_CFG = VERA_BASE+$0D
VERA_L0_MAP = VERA_BASE+$0E
VERA_L0_TIL = VERA_BASE+$0F
VERA_L0_HSC_L = VERA_BASE+$10
VERA_L0_HSC_H = VERA_BASE+$11
VERA_L0_VSC_L = VERA_BASE+$12
VERA_L0_VSC_H = VERA_BASE+$13
VERA_SPR_BASE = $1FC00
.export __STARTUP__: absolute = 1
.import zerobss, copydata, initlib, _main
.importzp c_sp
.import __STACKSTART__

.segment "STARTUP"
.export _start
_start:
        cld
        ldx #$FF
        txs
        lda #<__STACKSTART__
        sta c_sp
        lda #>__STACKSTART__
        sta c_sp+1
        jsr initlib
        jsr zerobss
        jsr copydata

        lda #$00
        sta VERA_CTRL
        sta VERA_DC_VID
        lda #$40
        sta VERA_DC_HSC
        sta VERA_DC_VSC

        ; 4bpp tiles, 64x32 map, 8x8 tiles, native 320x240 viewport.
        lda #$12
        sta VERA_L0_CFG
        lda #$00
        sta VERA_L0_MAP
        lda #$80
        sta VERA_L0_TIL
        lda #$00
        sta VERA_L0_HSC_L
        sta VERA_L0_HSC_H
        sta VERA_L0_VSC_L
        sta VERA_L0_VSC_H
        ; The C runtime now creates and updates NES OAM through VERA sprites.
        jsr _main
@wait:  jmp @wait

.segment "ASSETS"
.export _title_map_rle, _title_screen_prompt, _title_screen_palette
_title_screen_palette:
        .incbin "vera/build/title_screen_palette.bin"
_title_map_rle:
        .incbin "vera/build/title_screen_map_rle.bin"
_title_screen_prompt:
        .incbin "vera/build/title_screen_prompt.bin"
