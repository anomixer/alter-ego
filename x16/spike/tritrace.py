import re
import os
import sys

log = os.path.join(os.environ.get('TEMP', '.'), 'playtest-out.txt')
text = open(log, errors='ignore').read()
vals = [int(m, 16) for m in re.findall(r'User debug 1: \$([0-9a-fA-F]{2})', text)]
if len(vals) < 3:
    print('samples:', len(vals))
    sys.exit()
triples = [vals[i:i + 3] for i in range(0, len(vals) - 2, 3)]
print('samples:', len(vals), 'triples:', len(triples))
for i, (x, y, pad) in enumerate(triples):
    print(f'{i:4d} x={x:3d} y={y:3d} pad=0x{pad:02x}')
