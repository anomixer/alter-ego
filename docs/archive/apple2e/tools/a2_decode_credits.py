import sys
data = open(r'build\art\creditsh.bin', 'rb').read()
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
print("creditsh emitted:", len(out), "src_bytes:", i)
for r in (0, 1, 8, 10):
    row = out[r*40:(r+1)*40]
    nz = sum(1 for b in row if b != 0)
    print("row%d nonzero=%d: %s" % (r, nz, ' '.join('%02X' % b for b in row[:20])))
