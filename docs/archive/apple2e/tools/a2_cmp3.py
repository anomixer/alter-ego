import sys
# Parse emu_page3.txt (display order y=0..191)
emu_disp = {}
for line in open(r'build\a2\emu_page3.txt'):
    import re
    m = re.match(r'y=\s*(\d+)\s+(.+)$', line)
    if m:
        y = int(m.group(1))
        emu_disp[y] = [int(b, 16) for b in m.group(2).split()]
# titleh.bin decode (scanline order row=0..191)
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
# For each display y, compute the HGR address, then find the titleh scanline row
# that maps to that address.
# HGR layout: addr[y] = 0x2000 + (y%8)*0x0400 + ((y/8)%8)*0x80 + (y//64)*0x28
# titleh.bin row r is written to HGR page starting at 0x2000 + (r%8)*0x0400 + ((r//8)%8)*0x80 + (r//64)*0x28
# So display y == titleh scanline r for the SAME address. But the page is written
# sequentially by the RLE in scanline order. To find which scanline row r owns
# a given display y, we need: the page byte address for scanline r is
#   addr(r) = 0x2000 + (r%8)*0x400 + ((r//8)%8)*0x80 + (r//64)*0x28
# and display y's address is the same formula. So display y == scanline r if
# they produce the same address. But different (y,r) can map to same addr.
# Simpler: build addr->(row) map.
def hgr_addr(row):
    return 0x2000 + (row % 8) * 0x400 + ((row // 8) % 8) * 0x80 + (row // 64) * 0x28
# For each row r in titleh.bin, its bytes are at out[r*40:(r+1)*40]
# For each display y, its bytes are at the addr hgr_addr(y), which equals hgr_addr(r)
# for the row r that owns that address. Actually the RLE writes scanline r's bytes
# to hgr_addr(r). Display y reads the same hgr_addr(y). They match iff hgr_addr(y)==hgr_addr(r).
# But multiple rows map to the same addr? No - each row maps to a unique addr within
# $2000-$3FFF (192 rows, 40 bytes each, 7680 bytes = exactly the page).
# So build a map: addr -> (row, col).
# Actually display y reads addr hgr_addr(y), col c. The byte there was written by
# scanline row r where hgr_addr(r) == hgr_addr(y) AND col c. Since the RLE writes
# scanline row r's col c to hgr_addr(r)+c, display y col c reads the byte written by
# the row r with hgr_addr(r)==hgr_addr(y). There's exactly one such r (since the
# page is fully covered). Find r such that hgr_addr(r) == hgr_addr(y).
# Since hgr_addr is injective over rows 0..191? Let's just compute.
def find_row(addr):
    for r in range(192):
        if hgr_addr(r) == addr:
            return r
    return None
# Compare
diffs = []
for y in range(192):
    addr = hgr_addr(y)
    r = find_row(addr)
    if r is None:
        print("NO ROW for y=%d addr=%04X" % (y, addr))
        continue
    for c in range(40):
        e = emu_disp[y][c]
        t = out[r*40 + c]
        # emulator stores bit7 SET. titleh.bin stores raw. Compare (e|0x80)==(t|0x80)? 
        # Actually emulator does ora #$80 so e == (t | 0x80). titleh.bin raw t.
        if (e & 0x7F) != (t & 0x7F):
            diffs.append((y, c, e, t, r))
print("diffs (y,c,emu,title,row):", len(diffs))
for d in diffs[:20]:
    print("  y=%d c=%d emu=%02X title=%02X row=%d" % d)
# Show first matching row
print("\nRow 100 emu vs title:")
print("  emu  :", ' '.join('%02X' % b for b in emu_disp[100][:10]))
r100 = find_row(hgr_addr(100))
print("  title (row %d):" % r100, ' '.join('%02X' % out[r100*40 + c] for c in range(10)))
