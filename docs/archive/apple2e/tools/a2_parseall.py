import re
raw = open('build/a2/watchall.txt', 'rb').read()
if raw[:2] == b'\xff\xfe':
    t = raw.decode('utf-16-le', errors='replace')
else:
    t = raw.decode('utf-8', errors='replace')
rows = []
for m in re.finditer(r'PC=(\$[0-9A-Fa-f]{4})\s+(\$00[0-9A-Fa-f]{2})\s+<=\s+\$([0-9A-Fa-f]{2})', t):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
# group by address, show first 40 of each
for addr in ('$007C', '$0080', '$0084', '$0085', '$0086'):
    seq = [v for pc, a, v in rows if a == addr]
    print('%s: %s' % (addr, ' '.join('%02X' % v for v in seq[:60])))
    if len(seq) > 60:
        print('   ... %d more' % (len(seq) - 60))
