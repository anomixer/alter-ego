; x16/spike/t1.s - probe: headerless LOAD (SA=2) of the game and music images.
.setcpu "65C02"

.segment "LOADADDR"
        .word $0801

.segment "STARTUP"
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        ; --- MUSICB -> $1000 (SA=2, headerless)
        lda #6
        ldx #<mn
        ldy #>mn
        jsr $FFBD               ; SETNAM
        lda #1
        ldx #8
        ldy #2                  ; SA=2 -> headerless, X/Y is the address
        jsr $FFBA               ; SETLFS
        lda #0
        ldx #$00
        ldy #$10
        jsr $FFD5               ; LOAD
        sta $9FB9               ; LOAD status byte
        lda $1000
        sta $9FB9

        ; --- GAMEB -> $2000 (SA=2, headerless)
        lda #5
        ldx #<gn
        ldy #>gn
        jsr $FFBD               ; SETNAM
        lda #1
        ldx #8
        ldy #2
        jsr $FFBA               ; SETLFS
        lda #0
        ldx #$00
        ldy #$20
        jsr $FFD5               ; LOAD
        sta $9FB9
        lda $2000
        sta $9FB9
        lda $2001
        sta $9FB9
        lda #$4A
        sta $9FB9

        jmp $2000

mn:     .byte "MUSICB"
gn:     .byte "GAMEB"
