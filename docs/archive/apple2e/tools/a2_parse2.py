import re
raw = open('build/a2/watch3.txt', 'rb').read()
t = raw.decode('utf-16-le', errors='replace') if raw[:2] == b'\xff\xfe' else raw.decode('utf-8', errors='replace')
rows = []
for m in re.finditer(r'PC=(\$[0-9A-Fa-f]{4})\s+(\$00[0-9A-Fa-f]{2})\s+<=\s+\$([0-9A-Fa-f]{2})', t):
    rows.append((m.group(1), m.group(2), int(m.group(3), 16)))
for addr in ('$007C', '$0080'):
    seq = [v for pc, a, v in rows if a == addr]
    # only unique values / first 80
    print('%s first80: %s' % (addr, ' '.join('%02X' % v for v in seq[:80])))
    # show where it transitions to large values
    big = [v for v in seq if v > 0x40]
    if big:
        print('%s >0x40 count=%d first=%s last=%s' % (addr, len(big), ' '.join('%02X' % x for x in big[:10]), ' '.join('%02X' % x for x in big[-5:])))
    print('%s total=%d max=%s' % (addr, len(seq), '%02X' % max(seq)))
