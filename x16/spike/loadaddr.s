; X16 PRG load-address header: BASIC LOAD ",8,1" reads these two bytes as the
; destination address and loads the rest of the file there.  The cx16 runtime
; normally emits this from crt0; the spike's own startup (title.s) replaces
; crt0, so it is supplied here.
;
; Assemble with -D MUSIC_OVERLAY=1 for the $1000 overlay, default is the
; $2000 main game image.
.ifdef MUSIC_OVERLAY
        .segment "LOADADDR"
        .word $1000
.else
        .segment "LOADADDR"
        .word $2000
.endif
