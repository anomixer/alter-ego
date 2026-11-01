; Audio is disabled in the title-screen PoC.  The C game only takes the
; addresses of these arrays and passes them to the no-op music entry points.
        .export _music_title_data
        .export _music_level1_data
        .export _music_level2_data
        .export _music_level3_data
        .export _music_level4_data
        .export _music_level5_data
        .export _music_gameover_data
        .export _music_done_data

        .segment "RODATA"

_music_title_data:   .byte 0
_music_level1_data:  .byte 0
_music_level2_data:  .byte 0
_music_level3_data:  .byte 0
_music_level4_data:  .byte 0
_music_level5_data:  .byte 0
_music_gameover_data:.byte 0
_music_done_data:    .byte 0
