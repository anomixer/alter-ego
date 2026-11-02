import re
raw = open('build/a2/addrwr_all.txt', 'r').read()
rows = []
for m in re.finditer(r'PC=\$([0-9A-Fa-f]{4})\s+\$([0-9A-Fa-f]{4})\s*<=\s*\$([0-9A-Fa-f]{2})', raw):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
src = [v for pc, a, v in rows if a == '0080']
print('src count:', len(src))
# print src progression in chunks
for i in range(0, len(src), 64):
    chunk = src[i:i+64]
    print('  [%d] %s' % (i, ' '.join('%02X' % v for v in chunk)))
