import re
text = open(r'src\title.h', encoding='utf-8', errors='replace').read()
m = re.search(r'const unsigned char\s+title\s*\[.*?\]\s*=\s*\{(.*?)\}', text, re.S)
# RLE stream
data = bytes(int(t, 16) for t in re.findall(r'0[xX][0-9A-Fa-f]{2}', m.group(1)))
# decode RLE: tag = data[0]
tag = data[0]
out = bytearray()
i = 1
last = 0
while i < len(data):
    b = data[i]; i += 1
    if b != tag:
        out.append(b); last = b
    else:
        n = data[i]; i += 1
        if n == 0: break
        out.extend([last]*n)
print("decoded nametable len:", len(out), "tag=%02X" % tag)
# grid: 32 cols. Show which cells are nonzero (tile != background)
# background tile = 0x00 usually. Print as a compact map.
for row in range(0, 32):
    cells = out[row*32:(row+1)*32]
    line = ''.join('#' if c != 0 else '.' for c in cells)
    print("%2d %s" % (row, line))
