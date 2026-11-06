.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        lda #$00
        sta $9F25
        ; write 0x33 to $10000, read back
        lda #$00
        sta $9F20
        lda #$00
        sta $9F21
        lda #$11
        sta $9F22
        lda #$33
        sta $9F23
        lda #$00
        sta $9F20
        lda #$00
        sta $9F21
        lda #$11
        sta $9F22
        lda $9F23
        jsr phex
        lda #13
        jsr $FFD2

        ; write 0x55 to $2000, read back
        lda #$00
        sta $9F20
        lda #$20
        sta $9F21
        lda #$11
        sta $9F22
        lda #$55
        sta $9F23
        lda #$00
        sta $9F20
        lda #$20
        sta $9F21
        lda #$11
        sta $9F22
        lda $9F23
        jsr phex
        lda #13
        jsr $FFD2

        ; register readbacks
        lda $9F29
        jsr phex
        lda $9F2D
        jsr phex
        lda $9F2E
        jsr phex
        lda $9F2F
        jsr phex
        lda $9F2A
        jsr phex
        lda $9F2B
        jsr phex
        lda #13
        jsr $FFD2
halt:   jmp halt

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