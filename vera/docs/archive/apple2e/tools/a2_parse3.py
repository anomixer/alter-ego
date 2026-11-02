import re
raw = open('build/a2/watch3.txt', 'rb').read()
t = raw.decode('utf-16-le', errors='replace') if raw[:2] == b'\xff\xfe' else raw.decode('utf-8', errors='replace')
# find the ADDRWR section
idx = t.find('writes to the watched addresses')
seg = t[idx:]
rows = []
for m in re.finditer(r'PC=\$([0-9A-Fa-f]{4})\s+\$([0-9A-Fa-f]{4})\s*<=\s*\$([0-9A-Fa-f]{2})', seg):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
print('total rows parsed:', len(rows))
for addr in ('$007C', '$0080'):
    seq = [v for pc, a, v in rows if a == addr]
    print('%s count=%d max=%s first=%s' % (addr, len(seq), '%02X' % max(seq) if seq else '-', ' '.join('%02X' % v for v in seq[:20])))
# where does src_ptr go
big = [v for pc, a, v in rows if a == '$0080']
if big:
    print('src all: %s' % ' '.join('%02X' % v for v in big[:60]))
    print('src max: %02X count: %d' % (max(big), len(big)))
# OVERRUN section
if 'ran past' in t:
    o = t[t.find('ran past'):]
    print('OVERRUN found, first 1500 chars:')
    print(o[:1500])
