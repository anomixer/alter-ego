import re

SRC = r'C:\dev\alter-ego\iigs\src\games\alterego\credits.h'

GLYPH = {' ': 0x00}
for ch, code in zip('ABCDEFGHIJKLMNOP', range(0x80, 0x90)):
    GLYPH[ch] = code
for ch, code in zip('RSTUV', range(0x6B, 0x70)):
    GLYPH[ch] = code
GLYPH['X'] = 0x7B
GLYPH['Y'] = 0x7C
GLYPH['Z'] = 0x7D
for d in range(10):
    GLYPH[str(d)] = 0xF0 + d


def enc(text):
    out = []
    quote_open = True
    for ch in text:
        if ch == '\xa9':
            out += [0x7E, 0x7F]
        elif ch == '"':
            out.append(0xFC if quote_open else 0xFD)
            quote_open = not quote_open
        else:
            if ch not in GLYPH:
                raise SystemExit('no glyph for %r' % ch)
            out.append(GLYPH[ch])
    return out


BLUE, RED, RED2 = 3, 1, 2   # measured: attribute 3 = blue, 1 = red with yellow highlight,
                            # 2 = salmon/dark-orange red (the palette the original used for
                            # the ALEX SHABANOV line)
COL = 3                 # left text column (tiles)

# One blank row between every line (the original rhythm), colours alternate per
# line, the two section headers moved up, and the IIgs credit added at the
# bottom -- every line lands in its own 2x2 attribute quadrant, so the colours
# stay correct without the old 3-row gaps.
LAYOUT = [
    (7,  BLUE, 'ORIGINAL ZX SPECTRUM GAME'),
    (9,  RED,  '\xa92011 DENIS GRATCHEV'),
    (11, BLUE, 'NES CONVERSION BY'),
    (13, RED,  'SHIRU'),
    (15, BLUE, 'NES MUSIC BY'),
    (17, RED,  'RICHARD "KULOR" ARMIJO'),
    (19, BLUE, 'HACKED BY'),
    (21, RED2, 'ALEX SHABANOV'),
    (23, BLUE, 'APPLE IIGS VERSION BY'),
    (25, RED2, 'ANOMIXER 2026'),
]

nt = [[0] * 32 for _ in range(30)]
pal = [0] * 30
for row, colour, line in LAYOUT:
    for c, v in enumerate(enc(line)):
        nt[row][COL + c] = v
    pal[row] = colour

# an attribute quadrant is 2 tile rows tall: rows 4k,4k+1 share the top quadrant
# of the block, rows 4k+2,4k+3 share the bottom one
def quad(a, b):
    for r in (a, b):
        if r < len(pal) and pal[r]:
            return pal[r]
    return 0


attributes = [0x00] * 64
for blk in range(8):
    r0 = blk * 4
    top, bot = quad(r0, r0 + 1), quad(r0 + 2, r0 + 3)
    value = (top & 3) | ((top & 3) << 2) | ((bot & 3) << 4) | ((bot & 3) << 6)
    for col in range(8):
        attributes[blk * 8 + col] = value

flat = [v for row in nt for v in row] + attributes
assert len(flat) == 1024, len(flat)

# RLE used by unrle_vram: tag byte, then "tag count" repeats the previous byte
TAG = 0x01
out = [TAG]
i = 0
while i < len(flat):
    v = flat[i]
    run = 1
    while i + run < len(flat) and flat[i + run] == v:
        run += 1
    out.append(v)
    rest = run - 1
    while rest > 0:                  # the count is one byte, so chunk long runs
        chunk = min(rest, 255)
        out += [TAG, chunk]
        rest -= chunk
    i += run

body = []
for k in range(0, len(out), 16):
    body.append('    ' + ','.join('0x%02x' % b for b in out[k:k + 16]) + (',' if k + 16 < len(out) else ''))
text = 'const unsigned char credits[%d]={\n%s\n};\n' % (len(out), '\n'.join(body))
open(SRC, 'w', encoding='utf-8').write(text)
print('compressed', len(out), 'uncompressed', len(flat))

# round trip check
data = [int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{2})', text)]
dec, last, i = [], 0, 1
while i < len(data):
    b = data[i]; i += 1
    if b == TAG:
        c = data[i]; i += 1
        if c: dec.extend([last] * c)
    else:
        dec.append(b); last = b
print('round trip ok' if dec == flat else 'ROUND TRIP MISMATCH')
for r in range(6, 27):
    mark = 'B' if pal[r] == BLUE else 'R' if pal[r] == RED else '.'
    print('%2d %s |%s|' % (r, mark, ''.join('..' if v == 0 else '%02X' % v for v in nt[r][:26])))
print('attr per block', ['%02X' % attributes[b * 8] for b in range(8)])
