import re
t = open('build/a2/watch80.txt', encoding='utf-8', errors='replace').read()
vals = []
for m in re.finditer(r'\$0080 <= \$([0-9A-Fa-f]{2})', t):
    vals.append(int(m.group(1), 16))
print('writes:', len(vals))
if vals:
    print('max low: 0x%02X' % max(vals))
    print('tail:', ' '.join('%02X' % v for v in vals[-8:]))
else:
    print('none')
