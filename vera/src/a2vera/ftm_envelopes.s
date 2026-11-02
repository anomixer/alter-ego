; Advance all eleven original FamiTone envelopes with one small 6502 loop.
; FtmEnvelope is {data:word, pos:byte, repeat:byte, value:byte} (5 bytes).
; The cc65 version did a 16-bit multiply and stack setup for every envelope.
.setcpu "6502"
.segment "CODE"
.export _ftm_step_envelopes
.import _envelopes

; Both game and music linkers use only $80-$99 of zero page. These six bytes
; are scratch while the music call is active and do not change cc65's layout.
env_ptr  = $9A
data_ptr = $9C
env_left = $9E
env_guard = $9F

_ftm_step_envelopes:
        lda #<_envelopes
        sta env_ptr
        lda #>_envelopes
        sta env_ptr+1
        lda #11
        sta env_left
@next_env:
        ldy #3
        lda (env_ptr),y
        beq @new_value
        sec
        sbc #1
        sta (env_ptr),y
        jmp @advance_env

@new_value:
        lda #8
        sta env_guard
@read_value:
        ldy #0
        lda (env_ptr),y
        ldy #2
        clc
        adc (env_ptr),y
        sta data_ptr
        ldy #1
        lda (env_ptr),y
        adc #0
        sta data_ptr+1
        ldy #0
        lda (data_ptr),y
        tax
        ldy #2
        lda (env_ptr),y
        clc
        adc #1
        sta (env_ptr),y
        txa
        bmi @set_value
        cmp #$7F
        beq @loop_value
        ldy #3
        sta (env_ptr),y
        jmp @advance_env

@set_value:
        clc
        adc #$40
        ldy #4
        sta (env_ptr),y
        jmp @advance_env

@loop_value:
        ldy #1
        lda (data_ptr),y
        ldy #2
        sta (env_ptr),y
        dec env_guard
        bne @read_value

@advance_env:
        clc
        lda env_ptr
        adc #5
        sta env_ptr
        bcc :+
        inc env_ptr+1
:
        dec env_left
        bne @next_env
        rts
