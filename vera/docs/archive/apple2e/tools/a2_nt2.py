import sys
from PIL import Image
import re
sys.path.insert(0, r'tools')
from a2_assets import chr_tiles, tile_to_hgr
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
# chr tiles -> list of rows (pixel p = ?)
tiles = chr_tiles(open(r'src\tileset.chr','rb').read())
print("chr_tiles: %d tiles, first tile rows:" % len(tiles))
# Draw nametable using chr_tiles rows directly, pixel p drawn at col p
im = Image.new("RGB", (32*8, 32*8)); px = im.load()
for idx, t in enumerate(nt):
    cx = (idx%32)*8; cy=(idx//32)*8
    rows = tiles[t]
    for r in range(8):
        for p in range(8):
            v = rows[r*8+p]
            if v: px[cx+p, cy+r] = (255,255,255) if v==3 else (128,128,128)
            else: px[cx+p, cy+r] = (0,0,0)
im.save(r'build\a2\nt_chr_direct.png')
# Draw nametable using chr_tiles rows REVERSED (pixel p drawn at col 7-p)
im2 = Image.new("RGB", (32*8, 32*8)); px2 = im2.load()
for idx, t in enumerate(nt):
    cx=(idx%32)*8; cy=(idx//32)*8
    rows = tiles[t]
    for r in range(8):
        for p in range(8):
            v = rows[r*8+p]
            if v: px2[cx+(7-p), cy+r] = (255,255,255) if v==3 else (128,128,128)
            else: px2[cx+(7-p), cy+r] = (0,0,0)
im2.save(r'build\a2\nt_chr_rev.png')
print("saved nt_chr_direct.png and nt_chr_rev.png")
# Show tile 0-3 of chr_tiles as hex to inspect
for t in (0,1,2,3):
    rows = tiles[t]
    print("tile %d: %s" % (t, ' '.join('%02X' % sum((rows[r*8+k]&3)<<(7-k) for k in range(8)) for r in range(8))))
