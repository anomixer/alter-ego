import re
raw = open('build/a2/addrwr_all.txt', 'r').read()
rows = []
for m in re.finditer(r'PC=\$([0-9A-Fa-f]{4})\s+\$([0-9A-Fa-f]{4})\s*<=\s*\$([0-9A-Fa-f]{2})', raw):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
# src_ptr high byte $0081
hi = [(pc, v) for pc, a, v in rows if a == '0081']
print('src high writes:', len(hi))
for pc, v in hi[:40]:
    print('  PC=$%s val=$%02X' % (pc, v))
# also check for src_ptr = $1000-$10FF wrap: find where src low goes FF then 00
low = [v for pc, a, v in rows if a == '0080']
# find indices where low wraps
for i in range(1, len(low)):
    if low[i] < low[i-1]:
        print('wrap at src idx %d: %02X -> %02X' % (i, low[i-1], low[i]))
