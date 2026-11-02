import re

p = r'C:\dev\alter-ego\src\a2\ftm.s'
src = open(p, encoding='utf-8').read()

# --- replace the stub ch_envelope with a real envelope stepper --------------
start = src.index('ch_envelope:')
end = src.index(';--- push the AY registers')
new = """ch_envelope:
\t; instrument block = 6 bytes: word pitchEnv, word volEnv, word arpEnv,
\t; byte sample, byte option   (from music_instruments.s)
\tlda chan+CH_INSTR,x
\tasl a
\tasl a
\tasl a
\tclc
\tadc envp
\tsta insp
\tlda envp+1
\tadc #$00
\tsta insp+1
\t; is the instrument the same as last tick?  if not, restart the envelope
\tlda chan+CH_INSTR,x
\tcmp chan+CH_PREV,x
\tbeq @step
\tsta chan+CH_PREV,x
\tldy #$02
\tlda (insp),y
\tsta env+EV_PTR_L,x
\tiny
\tlda (insp),y
\tsta env+EV_PTR_H,x
\tlda #$00
\tsta env+EV_PTRIDX,x
\tsta env+EV_REPEAT,x
\tlda #$0F
\tsta env+EV_VALUE,x
@step:
\t; envelopeStep, mirroring famitone.s:752-785
\tlda env+EV_REPEAT,x
\tbeq @norep
\tdec env+EV_REPEAT,x
\tjmp @out
@norep:
\tlda env+EV_PTR_L,x
\tsta tmpptr
\tlda env+EV_PTR_H,x
\tsta tmpptr+1
\tldy env+EV_PTRIDX,x
@read:
\tlda (tmpptr),y
\tiny
\tora #$00
\tbpl @special
\t; output value: byte - $C0  (0..15 volume)
\tclc
\tadc #$40
\tsta env+EV_VALUE,x
\ttya
\tsta env+EV_PTRIDX,x
\tjmp @out
@special:
\tcmp #$7F
\tbeq @loop
\tsta env+EV_REPEAT,x
\ttya
\tsta env+EV_PTRIDX,x
\tjmp @out
@loop:
\tlda (tmpptr),y
\ttay
\tjmp @read
@out:
\tlda env+EV_VALUE,x
\tand #$0F
\tsta chan+CH_VOL,x
\trts

"""
src = src[:start] + new + src[end:]

# --- channel record grows by one byte (CH_PREV); widen the layout -----------
if 'CH_PREV' not in src:
    raise SystemExit('CH_PREV missing')
src = src.replace('.define CH_VOL     8\n', '.define CH_VOL     8\n.define CH_PREV    9\n')
src = src.replace('.define CH_SIZE    9\n', '.define CH_SIZE   10\n')

# --- envelope record needs the byte index -----------------------------------
src = src.replace('.define EV_COUNT   3\n', '.define EV_COUNT   3\n.define EV_PTRIDX  4\n')
src = src.replace('.define EV_SIZE    5\n', '.define EV_SIZE    6\n')

# --- reset CH_PREV when a module starts -------------------------------------
src = src.replace("""	sta chan+CH_VOL,x
	txa
	clc
	adc #CH_SIZE""", """	sta chan+CH_VOL,x
	sta chan+CH_PREV,x
	txa
	clc
	adc #CH_SIZE""")

open(p, 'w', encoding='utf-8').write(src)
print('patched, bytes =', len(src))
for pat in ('CH_PREV', 'EV_PTRIDX', 'ch_envelope:', '@out:'):
    print(pat, '->', len(re.findall(re.escape(pat), src)))
