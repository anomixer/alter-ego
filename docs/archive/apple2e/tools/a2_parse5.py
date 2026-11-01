import re
raw = open('build/a2/addrwr_all.txt', 'r').read()
rows = []
for m in re.finditer(r'PC=\$([0-9A-Fa-f]{4})\s+\$([0-9A-Fa-f]{4})\s*<=\s*\$([0-9A-Fa-f]{2})', raw):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
print('rows:', len(rows))
for addr in ('007C', '0080'):
    seq = [v for pc, a, v in rows if a == addr]
    print('%s count=%d max=%s last=%s' % (addr, len(seq), '%02X' % max(seq) if seq else '-', '%02X' % seq[-1] if seq else '-'))
    # transitions
    print('   %s' % ' '.join('%02X' % v for v in seq[:40]))
# where src goes above $08
big = [v for pc, a, v in rows if a == '$0080' and v > 8]
if big:
    print('src>8 count=%d first=%s last=%s' % (len(big), '%02X' % big[0], '%02X' % big[-1]))
