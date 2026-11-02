import re

game = open(r'build\a2\game.bin', 'rb').read()
mp = open(r'build\a2\game.map', encoding='utf-8', errors='replace').read()

syms = {}
for m in re.finditer(r'(\S+)\s+([0-9A-F]{6})\s+(RLA|REZ|RLZ|REA)', mp):
    syms.setdefault(m.group(1), int(m.group(2), 16))

def expected(y):
    return 0x2000 + (y % 8) * 0x0400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28

for name in ('_hgr_line_off', 'hgr_line_off'):
    if name not in syms:
        continue
    a = syms[name]
    off = a - 0x6000
    tbl = game[off:off + 192 * 2]
    bad = 0
    for y in range(192):
        got = tbl[2 * y] | (tbl[2 * y + 1] << 8)
        exp = expected(y)
        if got != exp:
            bad += 1
            if bad <= 8:
                print('y=%3d  table=$%04X  expected=$%04X' % (y, got, exp))
    print('%s at $%04X: %d/192 entries wrong' % (name, a, bad))
    print('  first 8 entries:', [hex(tbl[i] | (tbl[i+1] << 8)) for i in range(0, 16, 2)])
    break
else:
    print('no hgr_line_off symbol in map')
    cands = [n for n in syms if 'line_off' in n]
    print('candidates:', cands)
