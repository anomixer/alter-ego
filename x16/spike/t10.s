.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        lda #$FF
        sta last
@loop:  lda #0
        jsr $FF56
        sta a0
        stx x0
        sty y0
        cmp last
        beq @loop
        sta last
        lda a0
        jsr phex
        lda #$20
        jsr $FFD2
        lda x0
        jsr phex
        lda #$20
        jsr $FFD2
        lda y0
        jsr phex
        lda #13
        jsr $FFD2
        jmp @loop

phex:   pha
        lsr
        lsr
        lsr
        lsr
        jsr pnib
        pla
        pha
        and #$0F
        jsr pnib
        pla
        rts
pnib:   cmp #10
        bcc @d
        adc #6
@d:     adc #$30
        jmp $FFD2

last:   .byte 0
a0:     .byte 0
x0:     .byte 0
y0:     .byte 0