"""Find what sits at an address in the linked image, using the ld65 map.

Usage: python tools/a2_where.py <map> <hex address>
"""
import re
import sys

mp = open(sys.argv[1], encoding='utf-8', errors='replace').read()
tgt = int(sys.argv[2], 16)

rows = sorted([(int(a, 16), n) for n, a, t in
               re.findall(r'(\S+)\s+([0-9A-F]{6})\s+(RLA|REZ|RLZ|REA)', mp)])

prev = None
for a, n in rows:
    if a > tgt:
        print('next symbol: $%04X  %s' % (a, n))
        break
    if a <= tgt:
        prev = (a, n)
if prev:
    print('prev symbol: $%04X  %s  (target is %d bytes in)'
          % (prev[0], prev[1], tgt - prev[0]))

i = mp.find('Segment list')
print(mp[i:i + 700])
