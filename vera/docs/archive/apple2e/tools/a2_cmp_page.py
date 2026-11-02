import sys
# Emulator page dump
emu = open(r'build\a2\at_2000_1E00.bin', 'rb').read()
# titleh.bin decode
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
print("titleh emitted:", len(out))
# Compare row8
def show_row(page, name, r):
    row = page[r*40:(r+1)*40]
    nz = [(c, row[c]) for c in range(40) if row[c] != 0x80 and row[c] != 0]
    print("%s row%d nonzero: %s" % (name, r, ' '.join("%d=%02X" % (c, v) for c, v in nz)))
show_row(emu, "emu", 8)
show_row(out, "title", 8)
# Compare emu vs title byte by byte for row8
row_e = emu[8*40:(9*40)]
row_t = out[8*40:(9*40)]
diffs = [(c, row_e[c], row_t[c]) for c in range(40) if row_e[c] != row_t[c]]
print("row8 diffs (col, emu, title):", diffs[:20])
# Where does emu page differ from title decode overall?
diff_count = 0
for c in range(7680):
    if emu[c] != out[c]:
        diff_count += 1
print("total byte diffs emu vs title:", diff_count)
