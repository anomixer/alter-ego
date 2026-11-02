import sys
data = open(r'build\art\titleh.bin', 'rb').read()
tag = data[0]
out = bytearray()
i = 1
last = 0
# Decode full
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
# Now out is the HGR page in display order: 40 bytes x 192 rows
# Row 1 = bytes 40..79
print("total emitted:", len(out))
row0 = out[0:40]
row1 = out[40:80]
row2 = out[80:120]
def show(row, name):
    print(name, "=", ' '.join('%02X' % b for b in row))
show(row0, "row0")
show(row1, "row1")
show(row2, "row2")
# Find nonzero bytes in row1
nz = [(i, row1[i]) for i in range(40) if row1[i] != 0]
print("row1 nonzero:", len(nz), nz[:20])
# Count nonzero in whole page
nz_total = sum(1 for b in out if b != 0)
print("total nonzero:", nz_total)
# Where are nonzero bytes in the page (by row)
for r in range(192):
    row = out[r*40:(r+1)*40]
    nz = sum(1 for b in row if b != 0)
    if nz:
        print("row %d nonzero=%d" % (r, nz))
