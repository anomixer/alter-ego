import re
raw = open('build/a2/watch3.txt', 'rb').read()
t = raw.decode('utf-16-le', errors='replace') if raw[:2] == b'\xff\xfe' else raw.decode('utf-8', errors='replace')
# ALL rows in the watch section
idx = t.find('writes to the watched addresses')
seg = t[idx:]
rows = []
for m in re.finditer(r'PC=(\$[0-9A-Fa-f]{4})\s+(\$00[0-9A-Fa-f]{2})\s+<=\s+\$([0-9A-Fa-f]{2})', seg):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
print('rows parsed:', len(rows))
for addr in ('$007C', '$0080'):
    seq = [v for pc, a, v in rows if a == addr]
    print('%s count=%d max=%s first20=%s' % (addr, len(seq), '%02X' % max(seq) if seq else '-', ' '.join('%02X' % v for v in seq[:20])))
# OVERRUN
if 'ran past' in t:
    o = t[t.find('ran past'):]
    print('\n--- OVERRUN ---')
    print(o[:1200])
