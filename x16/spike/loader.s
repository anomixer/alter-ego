; x16/spike/loader.s - boot stub for the alter-ego CX16 port.
;
; The Apple II build boots from STARTUP.BAS (BLOAD the FTM player, BRUN the
; game).  On the X16 the same chain is two KERNAL LOADs from a BASIC SYS stub:
;
;   10 SYS 2061
;
; loads MUSIC to $1000 (its PRG header), loads GAME to $2000 and jumps to the
; STARTUP code that title.s places there.
;
; NOTE: HostFS resolves names byte-exactly, so these must be lower case
; (see x16/docs/PORT-CX16-EVAL.md 7.5).  LOAD returns carry *set* even when
; the transfer succeeds, so the flags must not be used to decide success.

.setcpu "65C02"

.segment "LOADADDR"
        .word $0801

.segment "STARTUP"
        ; 10 SYS 2061  ($080D)
        .byte $0B, $08, $0A, $00, $9E, '2', '0', '6', '1', $00, $00, $00

entry:
        lda #5
        ldx #<music_name
        ldy #>music_name
        jsr $FFBD               ; SETNAM
        lda #1
        ldx #8
        ldy #1                  ; SA=1 -> load address comes from the file header
        jsr $FFBA               ; SETLFS
        lda #0
        ldx #0
        ldy #0
        jsr $FFD5               ; LOAD

        lda #4
        ldx #<game_name
        ldy #>game_name
        jsr $FFBD               ; SETNAM
        lda #1
        ldx #8
        ldy #1
        jsr $FFBA               ; SETLFS
        lda #0
        ldx #0
        ldy #0
        jsr $FFD5               ; LOAD

        jmp $2000               ; title.s: initlib/zerobss/copydata then _main

music_name: .byte "music"
game_name:  .byte "game"
