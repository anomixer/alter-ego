import io
import re
import sys

path = r'C:\dev\alter-ego\build\a2\hgrtest_p.map'
t = io.open(path, encoding='utf-8', errors='replace').read()
lines = t.split('\n')

targets = [0x67F9, 0x4DC9, 0x48BF]

print('--- lines mentioning the crt0 target addresses ---')
for i, l in enumerate(lines):
    s = l.strip()
    for a in targets:
        hexes = ('%04X' % a, '$%04X' % a, '%04X:' % a, '0x%04X' % a)
        if any(h in s for h in hexes):
            print('  0x%04X  line %4d: %s' % (a, i + 1, s[:110]))

print('--- segment layout ---')
for l in lines:
    if re.match(r'^\s*(STARTUP|CODE|MAIN|RODATA|BSS|ZEROPAGE|LOWBSS|HEAP|ONCE|INIT|VECTORS)\s+Offs', l):
        print('  ' + l.strip()[:95])

print('--- memory areas ---')
for l in lines:
    if 'Area:' in l or 'Memory' in l:
        print('  ' + l.strip()[:95])

print('--- exports (first 40) ---')
start = None
for i, l in enumerate(lines):
    if l.strip().startswith('Exports'):
        start = i
        break
if start is not None:
    for l in lines[start + 1:start + 41]:
        if l.strip():
            print('  ' + l.strip()[:95])
