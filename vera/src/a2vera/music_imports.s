.setcpu "6502"
.export _music_init := $1000
.export _music_start := $100C
.export _music_tick := $100F
.export _music_stop := $1012
.export _music_pause := $1015
.export _sfx_start := $1018
.export _sfx_mute := $101B
.export _sfx_tick := $101E
.export _music_mute := $1021
.export _music_prefetch := $1024
