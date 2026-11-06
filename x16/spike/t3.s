.setcpu "65C02"
.segment "LOADADDR"
        .word $0801
.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00
entry:
        ; MUSIC (PRG with header) -> $1000
        lda #5
        ldx #<mn
        ldy #>mn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #1
        jsr $FFBA
        lda #0
        ldx #0
        ldy #0
        jsr $FFD5
        sta $9FB9
        lda $1000
        sta $9FB9
        ; GAME (PRG with header) -> $2000
        lda #4
        ldx #<gn
        ldy #>gn
        jsr $FFBD
        lda #1
        ldx #8
        ldy #1
        jsr $FFBA
        lda #0
        ldx #0
        ldy #0
        jsr $FFD5
        sta $9FB9
        lda $2000
        sta $9FB9
        lda $2001
        sta $9FB9
        lda #$4A
        sta $9FB9
        jmp $2000
mn:     .byte "music"
gn:     .byte "game"