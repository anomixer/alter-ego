"""List every JSR/JMP site in an image that targets a given address.

Used to answer "who calls this routine, and how often can it be reached" - the
frame tick is supposed to be reached once per frame through ppu_waitnmi().
"""
import sys

which = sys.argv[1]
target = int(sys.argv[2], 16)
if which == 'game':
    d, base = open('build/a2/game.bin', 'rb').read(), 0x6000
else:
    d, base = open('build/a2/cold.bin', 'rb').read(), 0xD000

sites = []
for i in range(len(d) - 2):
    if d[i] in (0x20, 0x4C) and (d[i + 1] | (d[i + 2] << 8)) == target:
        sites.append((base + i, 'jsr' if d[i] == 0x20 else 'jmp'))
print('call sites targeting $%04X in %s:' % (target, which))
for a, mn in sites:
    print('   $%04X  %s $%04X' % (a, mn, target))
if not sites:
    print('   (none)')
