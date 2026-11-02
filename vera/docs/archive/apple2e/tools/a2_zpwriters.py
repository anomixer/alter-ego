"""Find every instruction in the COLD image that writes a zero-page byte through
ANY form: zero-page, zero-page indexed, and the absolute-form encodings that
cc65 emits for a zero-page symbol referenced as a full address (sta $00F0).

The ay_out merge loop's counter kept landing on values the loop cannot produce,
so something else writes the same cell.
"""
import sys

target = int(sys.argv[1], 16)
d = open('build/a2/cold.bin', 'rb').read()
base = 0xD000

# Zero-page forms.
ZP = {0x85: 'sta zp', 0x86: 'stx zp', 0x84: 'sty zp', 0xE6: 'inc zp', 0xC6: 'dec zp',
      0x06: 'asl zp', 0x26: 'rol zp', 0x46: 'lsr zp', 0x66: 'ror zp',
      0x95: 'sta zp,x', 0x94: 'sty zp,x', 0x96: 'ldx zp'}
# Absolute forms that land on the same byte ($00F0).
ABS = {0x8D: 'sta abs', 0x8E: 'stx abs', 0x8C: 'sty abs', 0xEE: 'inc abs', 0xCE: 'dec abs',
       0x0E: 'asl abs', 0x2E: 'rol abs', 0x4E: 'lsr abs', 0x6E: 'ror abs',
       0x9D: 'sta abs,x', 0x9C: 'stz abs', 0x99: 'sta abs,y'}

hits = []
for i in range(len(d) - 3):
    op = d[i]
    if op in ZP and d[i + 1] == target:
        hits.append((base + i, ZP[op]))
    if op in ABS and (d[i + 1] | (d[i + 2] << 8)) == target:
        hits.append((base + i, ABS[op]))
print('writers of $%02X (and $00%02X) in cold.bin:' % (target, target))
for a, mn in hits:
    print('   $%04X  %s' % (a, mn))
if not hits:
    print('   (none)')
