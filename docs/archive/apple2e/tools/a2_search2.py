import sys
def decode(path):
    data = open(path, 'rb').read()
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
    return tag, out
pat = [0x3F, 0x31, 0x1E, 0x7F, 0x31]
for path in (r'build\art\titleh.bin', r'build\art\creditsh.bin'):
    tag, out = decode(path)
    print("== %s tag=%02X bytes=%d" % (path, tag, len(out)))
    found = []
    for r in range(192):
        row = out[r*40:(r+1)*40]
        for c in range(40 - len(pat) + 1):
            if row[c:c+len(pat)] == pat:
                found.append((r, c))
    print("   pattern found at:", found)
    # also print the emu y=100..103 cols 3-7 pattern region for this file
    for rr in range(100, 104):
        row = out[rr*40:(rr+1)*40]
        nz = [(c, b) for c, b in enumerate(row) if b]
        print("   row %d nonzero: %s" % (rr, ' '.join('c%d:%02X' % x for x in nz[:20])))
