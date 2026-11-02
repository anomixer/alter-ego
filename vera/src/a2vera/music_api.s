.setcpu "6502"

.segment "STARTUP"
.export _music_init, _music_start, _music_tick, _music_stop, _music_pause, _music_prefetch
.export _sfx_start, _sfx_mute, _sfx_tick, _music_mute
.import _music_init_impl, _music_start_impl, _music_tick_impl, _music_stop_impl, _music_pause_impl, _music_prefetch_impl
.import _sfx_start_impl, _sfx_mute_impl, _sfx_tick_impl, _music_mute_impl
.import initlib, zerobss, copydata

_music_init:  jsr initlib
              jsr zerobss
              jsr copydata
              jmp _music_init_impl
_music_start: jmp _music_start_impl
_music_tick:  jmp _music_tick_impl
_music_stop:  jmp _music_stop_impl
_music_pause: jmp _music_pause_impl
_sfx_start:   jmp _sfx_start_impl
_sfx_mute:    jmp _sfx_mute_impl
_sfx_tick:    jmp _sfx_tick_impl
_music_mute:  jmp _music_mute_impl
_music_prefetch: jmp _music_prefetch_impl
