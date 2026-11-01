; FamiTone2 audio for Alter Ego on silky-gs.
;
; The driver, song, instruments and SFX are the original NES FamiTone2 data
; (Public Domain).  The only change is in audio_famitone.s: writes to the NES
; APU registers are redirected through the fixed $7E30 trampolines to the APU
; model in silky-gs/src/apu/apu.s.

        .include "memmap.inc"
        .include "audio_famitone.s"

        .include "../../src/music_instruments.s"

        .export _music_title_data
        .export _music_level1_data
        .export _music_level2_data
        .export _music_level3_data
        .export _music_level4_data
        .export _music_level5_data
        .export _music_gameover_data
        .export _music_done_data
        .export sounds

_music_title_data:
        .include "../../src/music_title.s"

; The original level 1 tune fits in the remaining PRG space.  The other level
; songs still point at it; game over and the ending reuse the title theme.
_music_level1_data:
        .include "../../src/music_level1.s"

_music_level2_data:
        .include "../../src/music_level2.s"

_music_level3_data:
        .include "../../src/music_level3.s"

_music_level4_data:
        .include "../../src/music_level4.s"

_music_level5_data:
        .include "../../src/music_level5.s"

_music_gameover_data:
        .include "../../src/music_gameover.s"

_music_done_data:
        .include "../../src/music_done.s"

        .include "../../src/sounds.s"
