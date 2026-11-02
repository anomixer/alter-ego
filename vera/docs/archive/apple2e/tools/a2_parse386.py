import re
raw = open('build/a2/watch386.txt', 'rb').read()
# detect UTF-16 BOM
if raw[:2] == b'\xff\xfe':
    t = raw.decode('utf-16-le', errors='replace')
else:
    t = raw.decode('utf-8', errors='replace')
rows = []
for m in re.finditer(r'PC=(\$[0-9A-Fa-f]{4})\s+(\$00[0-9A-Fa-f]{2})\s+<=\s+\$([0-9A-Fa-f]{2})', t):
    pc = m.group(1)
    addr = m.group(2)
    val = int(m.group(3), 16)
    rows.append((pc, addr, val))
n = 0
for pc, addr, val in rows:
    if addr == '$0080':
        n += 1
        if n <= 130:
            print('src[%d]=0x%02X' % (n, val))
print('total src writes:', n)
