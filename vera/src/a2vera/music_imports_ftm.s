.setcpu "6502"
.export _music_init := $1000
.export _music_tick_realtime := $1006
.export _music_start := $100C
.export _music_tick := $100F
.export _music_stop := $1012
.export _music_pause := $1015
.export _music_mute := $1021
.export _music_prefetch := $1024
.import _ftm_sfx_start, _ftm_sfx_mute, _ftm_sfx_tick
.export _sfx_start := _ftm_sfx_start
.export _sfx_mute := _ftm_sfx_mute
.export _sfx_tick := _ftm_sfx_tick
