#!/usr/bin/env python3
"""Determine the DHGR line-address interleave empirically from a real .dhgr dump.

We brute-force the family  addr(y) = A*(y//64) + B*((y//8)%8) + C*(y%8)
and score each candidate by vertical coherence of the decoded 640x192 image.
The winner is the layout the real file was stored in.
"""
import sys
sys.path.insert(0, r'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages')
from PIL import Image

F = sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\cc65\samples\apple2\superman.dhgr'
d = open(F, 'rb').read()
N = len(d)
LINES, BPL = 192, 80


def decode(base):
    rows = []
    for b in range(BPL):
        v = d[base + b]
        rows.append([(v >> (6 - 2 * k)) & 3 for k in range(4)])
    return rows


def build(A, B, C):
    addrs = [A * (y // 64) + B * ((y // 8) % 8) + C * (y % 8) for y in range(LINES)]
    if len(set(addrs)) != LINES:
        return None
    if max(addrs) + BPL > N:
        return None
    return addrs


def score(addrs):
    rows = [decode(a) for a in addrs]
    s = 0
    for y in range(LINES - 1):
        r0, r1 = rows[y], rows[y + 1]
        for x in range(BPL):
            for k in range(4):
                s += abs(r0[x][k] - r1[x][k])
    return s / (LINES * BPL * 4)


cands = []
for A in (5120, 4096, 2048, 1024, 15360, 7680):
    for B in (640, 512, 256, 128, 80, 40, 320, 1280):
        for C in (80, 256, 128, 50, 40, 160, 320, 20):
            a = build(A, B, C)
            if a:
                cands.append((score(a), A, B, C, a))
cands.sort(key=lambda t: t[0])
print('file', F, 'bytes', N)
print('top candidates (score, A, B, C):')
for s, A, B, C, a in cands[:8]:
    print(f'  score={s:8.4f}  A={A:6d} B={B:5d} C={C:5d}  maxaddr={max(a)+BPL}')

best = cands[0]
print('\nbest:', best[1:4])
img = Image.new('RGB', (640, 192))
px = img.load()
CA = {0: (0, 0, 0), 1: (0, 160, 0), 2: (160, 0, 160), 3: (255, 255, 255)}
CB = {0: (0, 0, 0), 1: (255, 160, 0), 2: (0, 0, 255), 3: (255, 255, 255)}
for y in range(LINES):
    base = best[4][y]
    for b in range(BPL):
        pal = CA if b % 2 == 0 else CB
        for k in range(4):
            px[b * 4 + k, y] = pal[d[base + b] >> (6 - 2 * k) & 3]
img.save(r'C:\dev\alter-ego\tools\dhgr_best.png')
print('saved C:\\dev\\alter-ego\\tools\\dhgr_best.png')
print('line addr table y=0..9:', [hex(x) for x in best[4][:10]])
print('y=63,64,127,128,191:', [hex(best[4][y]) for y in (63, 64, 127, 128, 191)])
