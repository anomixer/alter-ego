"""Make tick_frame() safe on both targets.

apple2enh (//e): poll RDVBLBAR ($C019, the vertical-blank bar) -- bit7 is 1
inside the vertical-blank window, so wait for it to rise then fall.

apple2 (II/II+): $C019 is the keyboard data latch, bit7 is only ever set by a
keypress, so polling it never terminates.  There is no readable V-blank flag on
those machines, so fall back to a bounded timed delay -- the same approach the
pom2games dev kit documents (dev/lib/apple2c/apple2frame.h: "VBLBAR sur IIe,
temporisation sur IIc").
"""
import io
import re

p = r'C:\dev\alter-ego\src\a2\sys.s'
s = io.open(p, encoding='utf-8').read()

old = re.search(r'tick_frame:\n(?:.*\n)*?\trts\n', s)
if not old:
    raise SystemExit('tick_frame body not found')

new = """tick_frame:
.ifdef __APPLE2ENH__
	; //e: RDVBLBAR ($C019) bit7 = 1 inside the vertical-blank window.
@w1:	bit RDVBLBAR
	bpl @w1
@w2:	bit RDVBLBAR
	bmi @w2
	rts
.else
	; II/II+: $C019 is the keyboard latch, so it cannot be polled.
	; Burn roughly one 60 Hz frame (17030 cycles) with a 5-cycle loop.
	lda #$85
	sta frame_lo
	lda #$42
	sta frame_hi
@spin:	dec frame_lo
	bne @spin2
	dec frame_hi
@spin2:	lda frame_hi
	ora frame_lo
	bne @spin
	rts
.endif
"""

s = s[:old.start()] + new + s[old.end():]

# the delay needs two zero-page bytes
if 'frame_lo' not in s.split('tick_frame')[0]:
    m = re.search(r'^(\s*)\.segment "ZEROPAGE"\s*$', s, re.M)
    if not m:
        raise SystemExit('ZEROPAGE segment not found')
    s = s[:m.end()] + '\nframe_lo: .res 1\nframe_hi: .res 1' + s[m.end():]

io.open(p, 'w', encoding='utf-8').write(s)
print('sys.s patched, bytes =', len(s))
