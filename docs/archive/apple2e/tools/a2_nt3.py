import sys
from PIL import Image
import re
# decode title nametable
text = open(r'src\title.h', encoding='utf-8', errors='replace').read()
m = re.search(r'const unsigned char\s+title\s*\[.*?\]\s*=\s*\{(.*?)\}', text, re.S)
data = bytes(int(t, 16) for t in re.findall(r'0[xX][0-9A-Fa-f]{2}', m.group(1)))
tag = data[0]; out = bytearray(); i=1; last=0
while i < len(data):
    b = data[i]; i+=1
    if b != tag: out.append(b); last=b
    else:
        n = data[i]; i+=1
        if n==0: break
        out.extend([last]*n)
nt = out
htiles = open(r'build\hgr_tiles.bin','rb').read()
print("hgr_tiles.bin size:", len(htiles), "tiles:", len(htiles)//8)
# render nametable using htiles, bit6=leftmost
im = Image.new("RGB", (32*8, 32*8)); px = im.load()
for idx, t in enumerate(nt):
    cx=(idx%32)*8; cy=(idx//32)*8
    for r in range(8):
        b = htiles[t*8 + r]
        for k in range(7):
            if (b >> (6-k)) & 1:
                px[cx+k, cy+r] = (255,255,255)
            else:
                px[cx+k, cy+r] = (0,0,0)
im.save(r'build\a2\nt_htiles_b6.png')
# also bit0=leftmost
im2 = Image.new("RGB", (32*8, 32*8)); px2 = im2.load()
for idx, t in enumerate(nt):
    cx=(idx%32)*8; cy=(idx//32)*8
    for r in range(8):
        b = htiles[t*8 + r]
        for k in range(7):
            if (b >> k) & 1:
                px2[cx+k, cy+r] = (255,255,255)
            else:
                px2[cx+k, cy+r] = (0,0,0)
im2.save(r'build\a2\nt_htiles_b0.png')
print("saved nt_htiles_b6.png, nt_htiles_b0.png")
