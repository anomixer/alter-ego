#!/usr/bin/env python3
"""Empirically find the HGR scanline interleave from a raw .hgr dump.

Family: addr(y) = A*(y//64) + B*((y//8)%8) + C*(y%8)
  C = step between consecutive lines inside an 8-line group
  B = step between groups
  A = step between the three 64-line blocks
Constraints: 40-byte lines must not overlap; layout must fit the file.
Score: vertical coherence (sum |row[y]-row[y+1]| over bytes) -> lower is better.
"""
import sys
sys.path.insert(0, r'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages')
from PIL import Image

F = sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\cc65\samples\apple2\werner.hgr'
d = open(F, 'rb').read()
N = len(d)
LINES, BPL = 192, 40


def score(addrs):
    prev = d[addrs[0]:addrs[0] + BPL]
    tot = 0
    for y in range(1, LINES):
        cur = d[addrs[y]:addrs[y] + BPL]
        tot += sum(abs(a - b) for a, b in zip(cur, prev))
        prev = cur
    return tot


best = []
for C in range(40, 160, 8):
    for B in range(8 * C, 8 * C + 72, 8):
        for A in range(8 * B, 8 * B + 72, 8):
            addrs = [A * (y // 64) + B * ((y // 8) % 8) + C * (y % 8) for y in range(LINES)]
            if max(addrs) + BPL > N:
                continue
            s = sorted(addrs)
            if any(s[i + 1] - s[i] < BPL for i in range(LINES - 1)):
                continue
            best.append((score(addrs), A, B, C, addrs))
best.sort(key=lambda t: t[0])
print('file', F, 'bytes', N, 'valid layouts:', len(best))
for s, A, B, C, a in best[:6]:
    print(f'  score={s:9d}  A={A:5d}(${A:04X}) B={B:4d}(${B:04X}) C={C:3d}(${C:02X})  span={max(a)+BPL}')

if not best:
    sys.exit('none')
s, A, B, C, a = best[0]
print('\nWINNER A=%d B=%d C=%d' % (A, B, C))
print('offsets y=0..9 :', [hex(x) for x in a[:10]])
print('offsets y=8,16,63,64,128,191:', [hex(a[y]) for y in (8, 16, 63, 64, 128, 191)])

img = Image.new('L', (280, 192))
px = img.load()
for y in range(LINES):
    base = a[y]
    for b in range(BPL):
        v = d[base + b] & 0x7F
        for k in range(7):
            px[b * 7 + k, y] = 255 if (v >> (6 - k)) & 1 else 0
img.save(r'C:\dev\alter-ego\tools\hgr_win.png')
print('saved tools/hgr_win.png')
