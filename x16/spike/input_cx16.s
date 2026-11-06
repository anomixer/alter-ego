; x16/spike/input_cx16.s - Commander X16 input layer for the alter-ego port.
;
; Replaces vera/src/a2vera/input.s (Apple II PDL paddles + $C061/$C062 buttons).
; The game's pad encoding is
;   A=$01 B=$02 SELECT=$04 START=$08 UP=$10 DOWN=$20 LEFT=$40 RIGHT=$80
;
; Two sources are merged:
;   1. SNES controllers on ports 1-4 via joystick_scan ($FF53) / joystick_get
;      ($FF56), which give a real held-state bitfield.
;   2. The KERNAL "keyboard joystick" (joystick_get device 0), also a real
;      held-state bitfield, but only for the cursor keys; the KERNAL IRQ
;      refreshes it every jiffy.  That is what makes a held cursor key walk
;      continuously: reading key events through GETIN would stop after the
;      first step and resume only when the KERNAL/SMC key repeat kicks in
;      (about 0.5 s later, and the host OS controls that delay in x16emu).
;   3. Keyboard key events via GETIN ($FFE4) for buttons (Enter/Space = START,
;      X = A, Z = B, 1 = SELECT).  Buttons are NOT taken from the keyboard
;      joystick: its button bits are held state and would retrigger actions
;      every frame, so those stay edge-filtered through KEY_LOCK.
;      Cursor keys are also mirrored from key events so a tap still moves even
;      when the keyboard joystick state has not been refreshed yet.

.setcpu "65C02"

.export _joystick_init, _joystick_pad, _sound_test_edge, _ae_irq_install, _ae_irq_frames
.export _ae_rdtim
.export _ae_key_m, _ae_key_n, _ae_key_t
.import _pause_last_dirs

.define HOLD_FRAMES 8   ; direction stays pressed this long after the last char
.define KEY_LOCK    12   ; ignore repeated button chars (auto-repeat) this long

.segment "BSS"
pad:     .res 1
_ae_irq_frames: .res 1
oldirq:  .res 2
upd:     .res 1
dnd:     .res 1
lfd:     .res 1
rtd:     .res 1
lock:    .res 1
kbcount: .res 1
tmp0:    .res 1
tmp1:    .res 1
tmp2:    .res 1
tmp3:    .res 1
lastbtn: .res 1
kbpresent: .res 1
; One-frame flags for the Apple II "special keys" that live in the game's
; keyboard_pad(): M/N toggle music/SFX mute, T opens (and Escape closes) the
; sound-test selector.  Cleared at the start of every _joystick_pad call.
_ae_key_m: .res 1
_ae_key_n: .res 1
_ae_key_t: .res 1

.segment "CODE"

_joystick_init:
        jsr $FFCC            ; CLRCHN: input back to the keyboard
        jsr _ae_irq_install
        lda #0
        sta pad
        sta upd
        sta dnd
        sta lfd
        sta rtd
        sta lock
        ; throw away keys buffered before the game started
        ldx #16
@flush: jsr $FFE4
        beq @done
        dex
        bne @flush
@done:  rts

_joystick_pad:
        lda #0
        sta pad
        sta _ae_key_m
        sta _ae_key_n
        sta _ae_key_t
        jsr decay

        ; --- SNES controllers -------------------------------------------
        jsr $FF53            ; joystick_scan: refresh the saved pad states
        lda #1
        jsr snes
        lda #2
        jsr snes
        lda #3
        jsr snes
        lda #4
        jsr snes
        jsr kbjoy

        ; --- keyboard buffer --------------------------------------------
        lda #8
        sta kbcount
@drain: jsr $FFE4            ; GETIN: A = next char, 0 = empty
        beq @out
        jsr mapkey
        dec kbcount
        bne @drain
@out:   jsr apply_dirs
        lda pad
        ldx #0
        rts

; Turn the still-live direction hold timers into pad bits.
apply_dirs:
        lda pad
        ldx upd
        beq :+
        ora #$10
:       ldx dnd
        beq :+
        ora #$20
:       ldx lfd
        beq :+
        ora #$40
:       ldx rtd
        beq :+
        ora #$80
:       sta pad
        rts

; Merge the KERNAL keyboard joystick (device 0, live held state) into pad.
; byte0: 7=B 6=Y 5=SEL 4=STA 3=UP 2=DOWN 1=LEFT 0=RIGHT (active-low)
; byte1: 7=A 6=X 5=L 4=R
; Directions, B and A are level-sensitive, matching a real controller (and the
; NES): holding a cursor key walks, and holding B keeps the exchange input
; asserted so the game's per-tile-boundary check can see it - notably while
; falling, where that check only runs once per eight-pixel step.  SELECT and
; START stay one-frame pulses, because the game opens/toggles menus on START
; and a held Enter would reopen the pause menu every frame.
kbjoy:  lda #0
        jsr $FF56            ; A = byte0, X = byte1, Y = present
        cpy #0
        beq @present
        lda #0
        sta kbpresent        ; no keyboard joystick: fall back to key events
        rts
@present:
        eor #$FF
        sta tmp0             ; byte0, active-high
        txa
        eor #$FF
        sta tmp1             ; byte1, active-high
        lda #1
        sta kbpresent

        ; --- directions -------------------------------------------------
        lda tmp0
        and #$0F
        sta tmp2
        lda tmp2             ; UP (bit3) -> $10
        asl a
        and #$10
        sta tmp3
        lda tmp2             ; DOWN (bit2) -> $20
        asl a
        asl a
        asl a
        and #$20
        ora tmp3
        sta tmp3
        lda tmp2             ; LEFT (bit1) -> $40
        asl a
        asl a
        asl a
        asl a
        asl a
        and #$40
        ora tmp3
        sta tmp3
        lda tmp2             ; RIGHT (bit0) -> $80
        asl a
        asl a
        asl a
        asl a
        asl a
        asl a
        asl a
        and #$80
        ora tmp3
        ora pad
        sta pad

        ; --- B and A: level-sensitive ----------------------------------
        lda tmp0
        and #$80             ; B -> $02
        beq :+
        lda pad
        ora #$02
        sta pad
:       lda tmp1
        and #$80             ; A -> $01
        beq :+
        lda pad
        ora #$01
        sta pad
:
        ; --- SELECT and START: one-frame pulses ------------------------
        lda tmp0
        and #$30             ; SEL (bit5) / STA (bit4)
        sta tmp2
        lda lastbtn
        eor #$FF
        and tmp2             ; buttons that went down since the last call
        sta tmp3
        lda tmp2
        sta lastbtn
        lda tmp3
        and #$20             ; SELECT -> $04
        beq :+
        lda pad
        ora #$04
        sta pad
:       lda tmp3
        and #$10             ; START -> $08
        beq :+
        lda pad
        ora #$08
        sta pad
:       rts

; OR one SNES controller into pad.  A = device 1..4.
snes:   jsr $FF56            ; A = byte0, X = byte1, Y = present
        cpy #0
        beq @present
        rts                  ; Y != 0 -> nothing connected
@present:
        eor #$FF             ; byte0 is active-low
        sta tmp0
        txa
        eor #$FF
        sta tmp1
        lda tmp0
        and #$80             ; B
        beq :+
        lda pad
        ora #$02
        sta pad
:       lda tmp0
        and #$20             ; SELECT
        beq :+
        lda pad
        ora #$04
        sta pad
:       lda tmp0
        and #$10             ; START
        beq :+
        lda pad
        ora #$08
        sta pad
:       lda tmp0
        and #$08             ; UP
        beq :+
        lda pad
        ora #$10
        sta pad
:       lda tmp0
        and #$04             ; DOWN
        beq :+
        lda pad
        ora #$20
        sta pad
:       lda tmp0
        and #$02             ; LEFT
        beq :+
        lda pad
        ora #$40
        sta pad
:       lda tmp0
        and #$01             ; RIGHT
        beq :+
        lda pad
        ora #$80
        sta pad
:       lda tmp1
        and #$80             ; A button
        beq @out
        lda pad
        ora #$01
        sta pad
@out:   rts

; Install a VSYNC interrupt counter.  The X16 KERNAL drives its whole IRQ
; (jiffy clock, keyboard scan) from the VERA VSYNC interrupt, so the game must
; leave that interrupt enabled and take its frame pacing from here instead of
; polling the VERA status register.  The original handler is chained, so the
; keyboard keeps working.
; unsigned char ae_rdtim(void)  -- KERNAL RDTIM low byte (60 Hz clock)
_ae_rdtim:
        jsr $FFDE
        rts

_ae_irq_install:
        lda $0315
        cmp #>irq_tick
        bne @install
        lda $0314
        cmp #<irq_tick
        beq @done
@install:
        sei
        lda $0314
        sta oldirq
        lda $0315
        sta oldirq+1
        lda #<irq_tick
        sta $0314
        lda #>irq_tick
        sta $0315
        cli
@done:  rts

irq_tick:
        inc _ae_irq_frames
        jmp (oldirq)

; Decay the direction hold timers and the button repeat lock.
decay:  jsr decl_upd
        jsr decl_dnd
        jsr decl_lfd
        jsr decl_rtd
        ldx lock
        beq :+
        dec lock
:       rts
decl_upd: ldx upd
        beq :+
        dec upd
:       rts
decl_dnd: ldx dnd
        beq :+
        dec dnd
:       rts
decl_lfd: ldx lfd
        beq :+
        dec lfd
:       rts
decl_rtd: ldx rtd
        beq :+
        dec rtd
:       rts

; Map one keyboard character to a pad bit.  A = PETSCII code.
; With the KERNAL keyboard joystick present the cursor keys are already held
; state, so their characters are ignored here (the hold timer would overshoot).
mapkey:
        cmp #$11             ; cursor down
        bne :+
        ldx kbpresent
        bne @dirout
        lda #HOLD_FRAMES
        sta dnd
@dirout: rts
:       cmp #$91             ; cursor up
        bne :+
        ldx kbpresent
        bne @dirout
        lda #HOLD_FRAMES
        sta upd
        rts
:       cmp #$9D             ; cursor left
        bne :+
        ldx kbpresent
        bne @dirout
        lda #HOLD_FRAMES
        sta lfd
        rts
:       cmp #$1D             ; cursor right
        bne :+
        ldx kbpresent
        bne @dirout
        lda #HOLD_FRAMES
        sta rtd
        rts
:       ldy lock
        bne @out             ; ignore auto-repeat of a held button
        cmp #$20             ; Space = START (not in the keyboard joystick map)
        beq @start
        cmp #$31             ; '1' = SELECT (cow level), also not in the map
        beq @sel
        ; The Apple II port maps T to the NES Start+A+B chord that opens the
        ; sound test, and lets T/Escape leave it.  The X16 keyboard has both the
        ; chord (hold X+Z, tap Space) and these direct keys, so keep them.
        cmp #$54             ; 'T'
        beq @tst
        cmp #$D4             ; shifted 'T'
        beq @tst
        cmp #$4D             ; 'M' = music mute shortcut
        beq @mus
        cmp #$CD
        beq @mus
        cmp #$4E             ; 'N' = sound mute shortcut
        beq @snd
        cmp #$CE
        beq @snd
        cmp #$1B             ; Escape leaves the sound test
        beq @tst
        ldx kbpresent
        bne @out             ; Enter/Z/X arrive as edges from the joystick state
        cmp #$0D             ; Enter = START
        beq @start
        cmp #$5A             ; 'Z' = B
        beq @bb
        cmp #$DA             ; shifted 'Z'
        beq @bb
        cmp #$4B             ; 'K' = B (Apple II mapping)
        beq @bb
        cmp #$58             ; 'X' = A
        beq @aa
        cmp #$D8             ; shifted 'X'
        beq @aa
        cmp #$4A             ; 'J' = A (Apple II mapping)
        bne @out
        lda #$01
        jsr set_btn
        rts
@sel:   lda #$04
        jsr set_btn
        rts
@tst:   lda #1
        sta _ae_key_t
        lda #$0B             ; START|A|B: the sound-test chord
        jsr set_btn
        rts
@mus:   lda #1
        sta _ae_key_m
        rts
@snd:   lda #1
        sta _ae_key_n
        rts
@start: lda #$08
        jsr set_btn
        rts
@bb:    lda #$02
        jsr set_btn
        rts
@aa:    lda #$01
        jsr set_btn
@out:   rts
; OR the bit in A into pad for this frame and arm the repeat lock.
set_btn:
        ora pad
        sta pad
        lda #KEY_LOCK
        sta lock
        rts

; Same edge filter as the Apple II build: held directions and K/PAD_B must not
; retrigger in the sound test.
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
