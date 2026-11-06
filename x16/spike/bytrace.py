import re
import os

log = os.path.join(os.environ.get('TEMP', '.'), 'playtest-out.txt')
text = open(log, errors='ignore').read()
vals = [int(m, 16) for m in re.findall(r'User debug 1: \$([0-9a-fA-F]{2})', text)]
print('samples:', len(vals))
print('tail:', ' '.join(f'{b & 0xF8:3d}/{b & 7}' for b in vals[-140:]))
