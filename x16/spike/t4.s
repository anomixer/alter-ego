.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00
entry:
        lda #5
        ldx #<fn
        ldy #>fn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #2
        jsr $FFBA
        lda #3                  ; SA=3 -> VRAM bank 1
        ldx #0
        ldy #0
        jsr $FFD5
        sta $9FB9               ; LOAD status
        ; read VRAM $10000+$1000
        lda #$00
        sta $9F20
        lda #$10
        sta $9F21
        lda #$11                ; A16=1, increment 1
        sta $9F22
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda $9F23
        sta $9FB9
        lda #$00
        sta $9F20
        lda #$00
        sta $9F21
        lda #$11
        sta $9F22
        lda $9F23
        sta $9FB9
        lda #$4A
        sta $9FB9
halt:   jmp halt
fn:     .byte "tiles"