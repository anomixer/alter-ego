#!/usr/bin/env python3
"""Derive the Apple II HGR line interleave empirically from a real .hgr dump.

Family: addr(y) = A*(y//64) + B*((y//8)%8) + C*(y%8)
Constraints: non-overlapping 40-byte lines, full coverage of the 8KB page.
Score: vertical coherence of the decoded image.
"""
import sys
sys.path.insert(0, r'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages')
from PIL import Image

F = sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\cc65\samples\apple2\werner.hgr'
d = open(F, 'rb').read()
LINES, BPL = 192, 40
N = len(d)


def rows_at(base):
    return [[(d[base + b] >> (7 - k)) & 1 for k in range(7)] for b in range(BPL)]


def build(A, B, C):
    a = [A * (y // 64) + B * ((y // 8) % 8) + C * (y % 8) for y in range(LINES)]
    if len(set(a)) != LINES:
        return None
    if C < BPL:
        return None
    if max(a) + BPL > N:
        return None
    # non-overlap: sort and check gaps
    s = sorted(a)
    for i in range(len(s) - 1):
        if s[i + 1] - s[i] < BPL:
            return None
    return a


def score(a):
    rs = [rows_at(x) for x in a]
    tot = 0
    for y in range(LINES - 1):
        r0, r1 = rs[y], rs[y + 1]
        for b in range(BPL):
            for k in range(7):
                tot += abs(r0[b][k] - r1[b][k])
    return tot / (LINES * BPL * 7)


out = []
for A in (1024, 2048, 4096, 5120, 8192, 3072, 6144):
    for B in (40, 80, 128, 160, 256, 320, 512, 640, 1024):
        for C in (40, 80, 128, 160, 256, 320, 512):
            a = build(A, B, C)
            if a:
                out.append((score(a), A, B, C, a))
out.sort(key=lambda t: t[0])
print('file', F, 'bytes', N)
print('valid candidates:', len(out))
for s, A, B, C, a in out[:10]:
    print(f'  score={s:7.4f} A={A:5d} B={B:5d} C={C:5d} span={max(a)+BPL}')
if not out:
    sys.exit('no valid layout in this family')

s, A, B, C, a = out[0]
print('\nBEST: A=%d B=%d C=%d' % (A, B, C))
print('addr(y) y=0..9 :', [hex(x) for x in a[:10]])
print('addr y=8..17   :', [hex(x) for x in a[8:18]])
print('addr y=63,64,127,128,191:', [hex(x) for x in (a[63], a[64], a[127], a[128], a[191])])

img = Image.new('L', (280, 192))
px = img.load()
for y in range(LINES):
    base = a[y]
    for b in range(BPL):
        v = d[base + b]
        for k in range(7):
            px[b * 7 + k, y] = 255 if (v >> (7 - k)) & 1 else 0
img.save(r'C:\dev\alter-ego\tools\hgr_best.png')
print('saved tools/hgr_best.png')
