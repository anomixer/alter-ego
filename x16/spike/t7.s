.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        lda #$00
        sta $9F25
        lda #$51
        sta $9F29
        lda #$12
        sta $9F2D
        lda #$10
        sta $9F2E
        lda #$80
        sta $9F2F
        lda #$00
        sta $9F30
        sta $9F31
        sta $9F32
        sta $9F33

        lda #$00
        sta $9F20
        lda #$FA
        sta $9F21
        lda #$11
        sta $9F22
        lda #$00
        sta $9F23
        lda #$00
        sta $9F23
        lda #$00
        sta $9F23
        lda #$0F
        sta $9F23

        lda #$00
        sta $9F20
        lda #$00
        sta $9F21
        lda #$11
        sta $9F22
        ldx #32
@fill:  lda #$11
        sta $9F23
        dex
        bne @fill

        lda #$00
        sta $9F20
        lda #$20
        sta $9F21
        lda #$11
        sta $9F22
        ldy #0
@outer: ldx #16
@inner: lda #$00
        sta $9F23
        sta $9F23
        dex
        bne @inner
        dey
        bne @outer

        lda #$4A
        sta $9FB9
halt:   jmp halt