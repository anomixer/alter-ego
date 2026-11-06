; x16/spike/gate_cx16.s - extra game code that does not fit in the main CODE
; area.  The game's RAM area is full to within a few bytes (see x16/README.md
; "記憶體餘裕"), but ld65 still has a hole between FTMTABLE ($92DB) and
; FTM_HIGH_BSS ($93A0), so game.cfg places segment "GATE" at $92DC.  The
; loader LOADs the whole GAME image, padding included, so this code arrives
; with the rest of it.
;
; uint8_t __fastcall__ ae_midair_ok(void)
;
; Returns 1 when an exchange may be started while the Ego is falling.
;  * Horizontal mirror levels (sync_type == 0) always allow it: the other Ego
;    sits at the same height, so the Ego just keeps falling in the mirrored
;    column and the ordinary gravity test still decides where it stops.
;  * Vertically mirrored levels (sync_type != 0) put the other Ego at
;    240-player_y, so a mid-air swap would move the Ego to the mirrored height
;    - straight through the platform, possibly to a spot in mid-air under it.
;    Only allow it when the mirror position has a floor under it, i.e. the swap
;    really ends on a landing spot.
;
; Hand-written because the C version is about 30 bytes larger: the check needs
; collision_map[(feet-48)>>3)*32 + (x>>3] and check_map() is a static function.

.setcpu "65C02"
.import _sync_type, _player_x, _player_y, _collision_map
.importzp ptr1, ptr2
.export _ae_midair_ok

.segment "GATE"

_ae_midair_ok:
        lda     _sync_type
        beq     @ok                  ; horizontal mirror: swap whenever asked

        lda     #240
        sec
        sbc     _player_y            ; A = mirrored y (player_y < 240)
        cmp     #48
        bcs     @high
        lda     #48
@high:  cmp     #208
        bcc     @feet
        lda     #208
@feet:  clc
        adc     #8                   ; tile row under the mirror position
        cmp     #208
        bcs     @ok                  ; outside the map: check_map() calls it wall
        sec
        sbc     #48
        and     #$F8
        sta     ptr1
        lda     #0
        sta     ptr1+1
        asl     ptr1                 ; (row * 8) * 4 = row * 32
        rol     ptr1+1
        asl     ptr1
        rol     ptr1+1
        lda     _player_x
        lsr
        lsr
        lsr
        clc
        adc     ptr1
        sta     ptr1
        bcc     :+
        inc     ptr1+1
:       lda     #<_collision_map
        clc
        adc     ptr1
        sta     ptr2
        lda     #>_collision_map
        adc     ptr1+1
        sta     ptr2+1
        ldy     #0
        lda     (ptr2),y
        and     #$13                 ; TILE_WALL|TILE_LADDER|TILE_BRIDGE
        beq     @no
@ok:    lda     #1
        ldx     #0
        rts
@no:    lda     #0
        ldx     #0
        rts
