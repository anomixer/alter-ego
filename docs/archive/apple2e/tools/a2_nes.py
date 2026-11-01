data = open(r'C:\dev\Alter_Ego.nes', 'rb').read()
hdr = data[:16]
prg_size = hdr[4] * 16384
chr_size = hdr[5] * 8192
print("mapper", hdr[6] >> 4, "prg", prg_size, "chr", chr_size)
prg = data[16:16+prg_size]
chr = data[16+prg_size:16+prg_size+chr_size]
# The NES palette (3 bytes per entry: 2 color + unused).  Look for the palette
# block the title uses.  Standard NES palette is 16 entries of 3 bytes at some
# address in PRG.  Dump plausible palettes near the CHR or at PRG start.
print("PRG len", len(prg), "first 32 bytes:", prg[:32].hex())
# The title art uses 4 palettes (0..3).  Scan PRG for a block of 16*3 bytes
# that looks like a palette (all entries < 0x40, valid NES colors).
best = None
for i in range(0, len(prg) - 48, 1):
    blk = prg[i:i+48]
    if all(b < 0x40 for b in blk):
        # palette colors are 0x0F (black) or 0x10+...  check plausibility
        if best is None:
            best = i
if best is not None:
    print("candidate palette at PRG+", hex(best))
    for p in range(4):
        e = prg[best + p*12 : best + p*12 + 12]
        print(" palette", p, [hex(x) for x in e])
# Also dump the last 64 bytes of PRG (often palette area)
print("PRG tail:", prg[-64:].hex())
