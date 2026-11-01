import re, sys

m = open(r'build\a2\game.map', encoding='utf-8', errors='replace').read()
syms = {}
for l in m.splitlines():
    mm = re.match(r'^(\S+)\s+([0-9A-F]{6})\s+(RLA|REZ|RLZ|REA)\s*$', l.strip())
    if mm:
        syms[int(mm.group(2), 16)] = mm.group(1)
addrs = sorted(syms)

def near(a):
    best = None
    for x in addrs:
        if x <= a and (best is None or x > best[0]):
            best = (x, syms[x])
    return best

d = open(r'build\a2\ae2_stk.bin', 'rb').read()
sp = int(sys.argv[1], 16)
print('stack from SP=%04X up to 01FF:' % sp)
a = sp
while a < 0x200:
    lo = d[a - 0x100]
    hi = d[a + 1 - 0x100] if a + 1 < 0x200 else 0
    v = lo | (hi << 8)
    n = near(v)
    tag = 'after %s+%d at %s' % (n[1], v - n[0], hex(n[0])) if n else 'no symbol below'
    print('  %04X: %04X  %s' % (a, v, tag))
    a += 2
