import re, sys
d = {}
for line in open(sys.argv[1]):
    m = re.match(r'y=\s*(\d+)\s+(.+)$', line)
    if m: d[int(m.group(1))] = [int(b,16) for b in m.group(2).split()]
# count bit7-clear bytes per scanline (stripe indicators)
rows_bit7clear = []
for y in range(192):
    row = d.get(y, [0x80]*40)
    n = sum(1 for b in row if not (b & 0x80))
    if n > 0:
        rows_bit7clear.append((y, n))
print("scanlines with bit7-clear bytes:", len(rows_bit7clear), "of 192")
# group into ranges
if rows_bit7clear:
    ys = [y for y,_ in rows_bit7clear]
    ranges = []
    start = prev = ys[0]
    for y in ys[1:]:
        if y == prev+1: prev = y
        else: ranges.append((start,prev)); start=prev=y
    ranges.append((start,prev))
    print("ranges:", ranges[:12])
# total bit7-clear
total = sum(n for _,n in rows_bit7clear)
print("total bit7-clear bytes:", total, "of", 192*40)
