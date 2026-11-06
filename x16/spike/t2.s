.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00
entry:
        lda #5
        ldx #<gn
        ldy #>gn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #2
        jsr $FFBA
        lda #0
        ldx #$00
        ldy #$20
        jsr $FFD5
        sta $9FB9
        lda $2000
        sta $9FB9
        jmp $2000
gn:     .byte "gameb"