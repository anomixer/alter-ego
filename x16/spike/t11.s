.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        lda #4
        ldx #<fn
        ldy #>fn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #2
        jsr $FFBA
        lda #2                  ; SA=2 -> low RAM at X/Y
        ldx #$00
        ldy #$A0
        jsr $FFD5
        sta $9FB9
        ; read back 6 bytes via VERA from $A000 (bank 0)
        lda #$00
        sta $9F20
        lda #$A0
        sta $9F21
        lda #$10
        sta $9F22
        ldx #6
@rd:    lda $9F23
        sta $9FB9
        dex
        bne @rd
        lda #$4A
        sta $9FB9
halt:   jmp halt
fn:     .byte "lv00"