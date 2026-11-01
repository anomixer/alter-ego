import sys
emu = open(r'build\a2\emu_page.bin', 'rb').read()
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
print("titleh emitted:", len(out), "src_bytes:", i)
print("emu_page.bin size:", len(emu))
# Compare first 8192 bytes
e = emu[:8192]
diff = 0
for c in range(7680):
    if e[c] != out[c]:
        diff += 1
print("byte diffs emu vs title:", diff)
# Show row1 and row8
def show_row(page, name, r):
    row = page[r*40:(r+1)*40]
    nz = [(c, row[c]) for c in range(40) if row[c] != 0x80 and row[c] != 0]
    print("%s row%d nonzero: %s" % (name, r, ' '.join("%d=%02X" % (c, v) for c, v in nz)))
show_row(e, "emu", 1)
show_row(out, "title", 1)
show_row(e, "emu", 8)
show_row(out, "title", 8)
