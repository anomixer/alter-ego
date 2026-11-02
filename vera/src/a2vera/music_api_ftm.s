.setcpu "6502"
.segment "STARTUP"
.export _music_init, _music_start, _music_tick, _music_stop, _music_pause
.export _music_mute, _music_prefetch, _music_tick_realtime
.import _music_init_impl, _music_start_impl, _music_tick_impl
.import _music_tick_realtime_impl
.import _music_stop_impl, _music_pause_impl, _music_mute_impl
.import _music_prefetch_impl, zerobss

_music_init:     jsr zerobss
                 jmp _music_init_impl
_music_tick_realtime: jmp _music_tick_realtime_impl
                 .res 3, $EA
_music_start:    jmp _music_start_impl
_music_tick:     jmp _music_tick_impl
_music_stop:     jmp _music_stop_impl
_music_pause:    jmp _music_pause_impl
                 .res 9, $EA
_music_mute:     jmp _music_mute_impl
_music_prefetch: jmp _music_prefetch_impl
