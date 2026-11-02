; Small interpreter for original FamiTone APU SFX streams, mapped to VERA voices 4-7.
.setcpu "6502"
.ifndef VERA_BASE
VERA_BASE = $C200
.endif
.include "ftm_sfx_layout.inc"
ADDR_L = VERA_BASE+$00
ADDR_M = VERA_BASE+$01
ADDR_H = VERA_BASE+$02
DATA   = VERA_BASE+$03

.segment "BSS"
sfx_ptr:   .res 2
sfx_regs:  .res 11
sfx_repeat:.res 1
sfx_timer: .res 2
sfx_phase: .res 2
sfx_level: .res 1
sfx_gain:  .res 1
sfx_wave:  .res 1
sfx_base:  .res 1
sfx_voice: .res 1

.segment "FTMSFX"
.export _ftm_sfx_start, _ftm_sfx_tick, _ftm_sfx_mute
sfx_muted: .res 1

_ftm_sfx_start:
        tax
        lda sfx_muted
        bne @start_done
        txa
        asl a
        tax
        lda FTM_SFX_TABLE,x
        sta sfx_ptr
        lda FTM_SFX_TABLE+1,x
        sta sfx_ptr+1
        lda #0
        sta sfx_repeat
        ldx #10
@clear:
        sta sfx_regs,x
        dex
        bpl @clear
        lda #$30             ; match FamiTone's cleared pulse/noise duty bits
        sta sfx_regs
        sta sfx_regs+3
        sta sfx_regs+9
@start_done:
        rts

_ftm_sfx_tick:
        lda sfx_muted
        bne @tick_done
        lda sfx_ptr+1
        beq @tick_done
        lda sfx_repeat
        beq @parse
        dec sfx_repeat
        jmp @render
@parse:
        jsr sfx_read_byte
        cmp #$10
        bcc @write_reg
        cmp #$FF
        beq @stop
        sec
        sbc #$10             ; FamiTone repeats for (command - $10) frames
        sta sfx_repeat
        jsr sfx_advance
        jmp @render
@write_reg:
        tax
        jsr sfx_advance
        jsr sfx_read_byte
        sta sfx_regs,x
        jsr sfx_advance
        jmp @parse
@render:
        ldx #0
        ldy #0
        jsr sfx_render_pulse
        ldx #3
        ldy #1
        jsr sfx_render_pulse
        jsr sfx_render_triangle
        jsr sfx_render_noise
@tick_done:
        rts
@stop:
        lda #0
        sta sfx_ptr+1
        sta sfx_repeat
        jsr sfx_silence
        rts

; X = FamiTone pulse register base (0 or 3), Y = VERA voice number 0 or 1.
sfx_render_pulse:
        stx sfx_base
        sty sfx_voice
        lda sfx_regs,x
        and #$0F
        sta sfx_level
        beq @pulse_off
        ldx sfx_base
        lda sfx_regs+1,x
        sta sfx_timer
        lda sfx_regs+2,x
        and #$07
        sta sfx_timer+1
        cmp #$07
        bne @pulse_active
        lda sfx_timer
        cmp #$F8
        bcs @pulse_off
@pulse_active:
        jsr sfx_lookup_phase
        ldx sfx_base
        lda sfx_regs,x
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a
        and #$03
        tax
        lda pulse_width,x
        sta sfx_wave
        jsr sfx_make_gain
        ldy sfx_voice
        jmp sfx_write_voice
@pulse_off:
        lda #0
        sta sfx_phase
        sta sfx_phase+1
        sta sfx_gain
        lda #$0F
        sta sfx_wave
        ldy sfx_voice
        jmp sfx_write_voice

sfx_render_triangle:
        lda sfx_regs+6
        beq @tri_off
        lda sfx_regs+7
        sta sfx_timer
        lda sfx_regs+8
        and #$07
        sta sfx_timer+1
        cmp #$07
        bne @tri_active
        lda sfx_timer
        cmp #$F8
        bcs @tri_off
@tri_active:
        jsr sfx_lookup_phase
        ; The NES triangle advances once per 32 CPU cycles, while pulse is
        ; once per 16. The shared timer table stores pulse phase increments.
        lsr sfx_phase+1
        ror sfx_phase
        lda #$80
        sta sfx_wave
        lda #$F0             ; cap sharp transients below full PSG volume
        sta sfx_gain
        ldy #2
        jmp sfx_write_voice
@tri_off:
        lda #0
        sta sfx_phase
        sta sfx_phase+1
        sta sfx_gain
        lda #$80
        sta sfx_wave
        ldy #2
        jmp sfx_write_voice

sfx_render_noise:
        lda sfx_regs+9
        and #$0F
        sta sfx_level
        beq @noise_off
        lda sfx_regs+10
        and #$0F
        asl a
        tax
        lda FTM_SFX_NOISE_TABLE,x
        sta sfx_phase
        lda FTM_SFX_NOISE_TABLE+1,x
        sta sfx_phase+1
        lda #$C0
        sta sfx_wave
        jsr sfx_make_gain
        ldy #3
        jmp sfx_write_voice
@noise_off:
        lda #0
        sta sfx_phase
        sta sfx_phase+1
        sta sfx_gain
        lda #$C0
        sta sfx_wave
        ldy #3
        jmp sfx_write_voice

sfx_make_gain:
        ldx sfx_level
        lda sfx_volume_curve,x
        cmp #$3C
        bcc @gain_capped
        lda #$3C             ; leave a little headroom while raising SFX level
@gain_capped:
        ora #$C0             ; apply the same nonlinear +6 dB curve as music
        sta sfx_gain
        rts

; Timer/phase pairs are generated only for values present in sounds.s.
sfx_lookup_phase:
        ldx #0
@search:
        lda FTM_SFX_PERIOD_TABLE,x
        cmp sfx_timer
        bne @next
        lda FTM_SFX_PERIOD_TABLE+1,x
        cmp sfx_timer+1
        beq @found
@next:
        txa
        clc
        adc #4
        tax
        cpx #(FTM_SFX_PERIOD_COUNT*4)
        bcc @search
        lda #0
        sta sfx_phase
        sta sfx_phase+1
        rts
@found:
        lda FTM_SFX_PERIOD_TABLE+2,x
        sta sfx_phase
        lda FTM_SFX_PERIOD_TABLE+3,x
        sta sfx_phase+1
        rts

sfx_write_voice:
        tya
        asl a
        asl a
        clc
        adc #$D0
        sta ADDR_L
        lda #$F9
        sta ADDR_M
        lda #$11
        sta ADDR_H
        lda sfx_phase
        sta DATA
        lda sfx_phase+1
        sta DATA
        lda sfx_gain
        sta DATA
        lda sfx_wave
        sta DATA
        rts

_ftm_sfx_mute:
        sta sfx_muted
        beq @mute_done
        jsr sfx_silence
@mute_done:
        rts

sfx_silence:
        lda #$D2
        jsr psg_address
        lda #0
        sta DATA
        lda #$D6
        jsr psg_address
        lda #0
        sta DATA
        lda #$DA
        jsr psg_address
        lda #0
        sta DATA
        lda #$DE
        jsr psg_address
        lda #0
        sta DATA
        rts

psg_address:
        sta ADDR_L
        lda #$F9
        sta ADDR_M
        lda #$11
        sta ADDR_H
        rts

sfx_read_byte:
        lda sfx_ptr
        sta @read+1
        lda sfx_ptr+1
        sta @read+2
; Keep this a three-byte absolute LDA. $0000 assembles as the two-byte
; zero-page form; then the high-byte patch would overwrite the following RTS.
@read:  lda $FFFF
        rts

sfx_advance:
        inc sfx_ptr
        bne @advanced
        inc sfx_ptr+1
@advanced:
        rts

pulse_width:
        .byte $0F,$1F,$3F,$1F
sfx_volume_curve:
        .byte 0,18,24,29,35,40,44,49,55,60,60,60,60,60,60,60
