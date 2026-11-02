import sys
data = open(r'build\art\titleh.bin', 'rb').read()
tag = data[0]
out = bytearray()
i = 1
last = 0
while i < len(data):
    b = data[i]
    i += 1
    if b != tag:
        out.append(b)
        last = b
    else:
        n = data[i]
        i += 1
        if n == 0:
            break
        out.extend([last] * n)
print("decoded bytes:", len(out), "tag=%02X" % tag)
# emu y=100 cols 3-7 pattern (bit7 cleared)
pat = [0x3F, 0x31, 0x1E, 0x7F, 0x31]
print("searching for", ' '.join('%02X' % p for p in pat))
for r in range(192):
    row = out[r*40:(r+1)*40]
    for c in range(40 - len(pat) + 1):
        if row[c:c+len(pat)] == pat:
            print("  FOUND at titleh row=%d col=%d" % (r, c))
# also list which titleh rows are nonzero and their ranges
nzrows = [r for r in range(192) if any(b != 0 for b in out[r*40:(r+1)*40])]
if nzrows:
    print("titleh nonzero rows: %d..%d  count=%d" % (nzrows[0], nzrows[-1], len(nzrows)))
# show titleh row 100 and 32
for rr in (32, 100, 101, 102, 103):
    row = out[rr*40:(rr+1)*40]
    nz = [(c, b) for c, b in enumerate(row) if b]
    print("titleh row %d nonzero: %s" % (rr, ' '.join('c%d:%02X' % x for x in nz[:14])))
