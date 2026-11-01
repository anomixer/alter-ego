"""Show raw bytes for a few HGR scanlines from a dump, flagging bit 7."""
import sys

d = open(sys.argv[1], 'rb').read()

def addr(y):
    return (y % 8) * 0x400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28

for y in (8, 40, 64, 120, 184):
    a = addr(y)
    line = d[a:a + 40]
    hi = sum(1 for b in line if b & 0x80)
    print('y=%3d  bit7 set on %2d/40 bytes' % (y, hi))
    print('        ' + line[:20].hex(' '))
    print('        ' + line[20:40].hex(' '))
