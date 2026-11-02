.setcpu "6502"
.export _joystick_init, _joystick_pad, _sound_test_edge
.import _pause_last_dirs

.segment "BSS"
connected: .res 1
buttons: .res 1
pad: .res 1

.segment "CODE"
; PDL0/PDL1 are RC timers, not axis registers. With no controller attached
; both remain high. Allow more than the maximum ~2816-cycle discharge time.
_joystick_init:
        lda #0
        sta connected
        sta buttons
        bit $C070
        ldy #3
@outer: ldx #220
@delay: dex
        bne @delay
        dey
        bne @outer
        lda $C064
        and $C065
        bmi @done
        inc connected
@done:  rts

; Sample both axes together around positions 80 and 184, leaving a generous
; centre dead zone. Roughly 2 ms per poll, independent of stick position.
; PB0 = exchange (held); PB1 = Start/pause (rising edge only).
_joystick_pad:
        lda #0
        sta pad
        lda connected
        beq @return
        bit $C070
        ldx #170
@low:   dex
        bne @low
        bit $C064
        bmi :+
        lda #$40
        sta pad
:       bit $C065
        bmi :+
        lda pad
        ora #$10
        sta pad
:       ldx #230
@high:  dex
        bne @high
        bit $C064
        bpl :+
        lda pad
        ora #$80
        sta pad
:       bit $C065
        bpl :+
        lda pad
        ora #$20
        sta pad
:       bit $C061
        bpl :+
        lda pad
        ora #$01
        sta pad
:       lda $C062
        and #$80
        cmp buttons
        beq @return
        sta buttons
        cmp #0
        beq @return
        lda pad
        ora #$08
        sta pad
@return:
        lda pad
        ldx #0
        rts

; Filter held directions and the SFX trigger (K/PAD_B) in the sound test.
; Restarting the SFX on every held-key frame traps it on its first sound.
; Fastcall receives the pad in A and returns the newly pressed bits in A.
_sound_test_edge:
        pha
        and #$F2
        cmp _pause_last_dirs
        sta _pause_last_dirs
        beq @held
        pla
        ldx #0
        rts
@held:  pla
        and #$0D
        ldx #0
        rts
