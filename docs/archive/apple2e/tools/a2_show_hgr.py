"""Render a raw HGR page dumped from the emulator so the screen content can be
judged offline.  Usage: python tools/a2_show_hgr.py <dump.bin> <out.png>
"""
import sys

d = open(sys.argv[1], 'rb').read()
out = sys.argv[2]

# Scanline order in memory: addr(y) = base + (y%8)*$400 + ((y//8)%8)*$80 + (y//64)*$28
def addr(y):
    return (y % 8) * 0x400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28

palette = [
    (0, 0, 0), (0x80, 0, 0x80), (0, 0, 0x80), (0xC0, 0, 0xC0),
    (0x40, 0, 0), (0x80, 0x80, 0x80), (0, 0, 0xC0), (0x60, 0x60, 0xC0),
    (0x80, 0x40, 0), (0xC0, 0xC0, 0), (0xC0, 0x60, 0), (0xC0, 0xC0, 0x60),
    (0, 0x80, 0), (0x00, 0xC0, 0), (0x60, 0xC0, 0x60), (0xFF, 0xFF, 0xFF),
]

from PIL import Image
img = Image.new('RGB', (280, 192))
px = img.load()
for y in range(192):
    a = addr(y)
    for b in range(40):
        if a + b >= len(d):
            continue
        v = d[a + b] & 0x7F
        for k in range(4):
            pair = (v >> (6 - 2 * k)) & 3
            x = b * 7 + k * 2
            px[x, y] = palette[pair * 2]
            if x + 1 < 280:
                px[x + 1, y] = palette[pair * 2 + 1]
img.save(out)

nz = sum(1 for b in d if b)
print('dump %d bytes, %d nonzero' % (len(d), nz))
print('first 40 raw:', d[:40].hex(' '))
print('wrote', out)
