import sys
from PIL import Image
import re
# parse title.h
text = open(r'src\title.h', encoding='utf-8', errors='replace').read()
m = re.search(r'const unsigned char\s+title\s*\[.*?\]\s*=\s*\{(.*?)\}', text, re.S)
data = bytes(int(t, 16) for t in re.findall(r'0[xX][0-9A-Fa-f]{2}', m.group(1)))
print("nametable bytes:", len(data), "-> 32x30 =", 32*30)
# load tileset
tileset = open(r'build\hgr_tiles.bin', 'rb').read()
# draw the nametable as 8x8 per tile (using bit0 of tile byte as pixel)
im = Image.new("RGB", (32*8, 30*8))
px = im.load()
for idx, t in enumerate(data):
    cx = (idx % 32) * 8
    cy = (idx // 32) * 8
    for r in range(8):
        b = tileset[t*8 + r]
        for k in range(8):
            if (b >> k) & 1:   # NES: bit0 = leftmost
                px[cx+k, cy+r] = (255,255,255)
            else:
                px[cx+k, cy+r] = (0,0,0)
im.save(r'build\a2\nt_title.png')
print("saved nt_title.png")
