.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        ; --- TILES -> VRAM bank1 $0000
        lda #5
        ldx #<tn
        ldy #>tn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #2
        jsr $FFBA
        lda #3
        ldx #0
        ldy #0
        jsr $FFD5
        sta $9FB9
        lda #$20
        sta vlo
        lda #$00
        sta vmid
        lda #$11
        sta vhi
        jsr vset
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9

        ; --- CRPAL -> VRAM bank1 $FA00
        lda #5
        ldx #<cn
        ldy #>cn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #2
        jsr $FFBA
        lda #3
        ldx #$00
        ldy #$FA
        jsr $FFD5
        sta $9FB9
        lda #$00
        sta vlo
        lda #$FA
        sta vmid
        lda #$11
        sta vhi
        jsr vset
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda #$4A
        sta $9FB9
halt:   jmp halt

vset:
        lda vlo
        sta $9F20
        lda vmid
        sta $9F21
        lda vhi
        sta $9F22
        rts

vlo:    .byte 0
vmid:   .byte 0
vhi:    .byte 0
tn:     .byte "tiles"
cn:     .byte "crpal"