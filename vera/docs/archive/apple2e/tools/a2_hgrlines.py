"""Per-line report on a raw HGR dump: how much of each scanline the tile
renderer actually wrote (it covers 32 of HGR's 40 byte columns)."""
import sys

d = open(sys.argv[1], 'rb').read()

def addr(y):
    return (y % 8) * 0x400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28

for y in range(0, 192, 8):
    a = addr(y)
    line = d[a:a + 40]
    left = sum(1 for b in line[:32] if b)
    right = sum(1 for b in line[32:] if b)
    print('y=%3d addr=$%04X  cols0-31 nonzero=%2d  cols32-39 nonzero=%2d  tail=%s'
          % (y, 0x2000 + a, left, right, line[32:].hex(' ')))
