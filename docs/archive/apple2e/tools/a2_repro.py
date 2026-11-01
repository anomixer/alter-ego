import re, sys
# replicate a2_art.py's hgr_page + decode
SRC = 'src/a2'
COLS, ROWS = 32, 24
ROW0 = 3
BYTE = re.compile(r'\$([0-9A-Fa-f]{2})')
ARRAY = re.compile(r'const unsigned char\s+(\w+)\s*\[\s*\d*\s*\]\s*=\s*\{(.*?)\}', re.S)
BYTE = re.compile(r'0[xX][0-9A-Fa-f]{2}')

def decode(stream):
    tag = stream[0]
    out = bytearray()
    i = 1
    last = 0
    while i < len(stream):
        b = stream[i]; i += 1
        if b == tag:
            n = stream[i]; i += 1
            if n == 0:
                break
            out += bytes([last]) * n
        else:
            out.append(b); last = b
    return out

tileset = open('build/hgr_tiles.bin', 'rb').read()
text = open('src/title.h', encoding='utf-8', errors='replace').read()
m = ARRAY.search(text)
data = bytes(int(t, 16) for t in BYTE.findall(m.group(2)))
nametable = decode(data)
print('nametable len:', len(nametable), 'tile count:', len(nametable))
# hgr_page
page = bytearray(192 * 40)
for idx, tile in enumerate(nametable):
    col, row = idx % COLS, idx // COLS
    if col >= 40:
        continue
    out_row = row - ROW0
    if out_row < 0 or out_row >= ROWS:
        continue
    b = tileset[tile * 8:tile * 8 + 8]
    for r in range(8):
        page[(out_row * 8 + r) * 40 + col] = b[r]
for row in (0, 1, 2):
    print('hgr_page row%d: %s' % (row, ' '.join('%02X' % page[row*40:(row+1)*40][b] for b in range(40))))
nz = sum(1 for x in page if x)
print('nonzero bytes in hgr_page:', nz)
