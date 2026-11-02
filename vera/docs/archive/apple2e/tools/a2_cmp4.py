import re
def decode(path):
    data = open(path, 'rb').read()
    tag = data[0]; out = bytearray(); i=1; last=0
    while i < len(data):
        b = data[i]; i+=1
        if b != tag: out.append(b); last=b
        else:
            n = data[i]; i+=1
            if n==0: break
            out.extend([last]*n)
    return out
def load_emu(path):
    d = {}
    for line in open(path):
        m = re.match(r'y=\s*(\d+)\s+(.+)$', line)
        if m: d[int(m.group(1))] = [int(b,16) for b in m.group(2).split()]
    return d
def hgr_addr(row):
    return 0x2000 + (row%8)*0x400 + ((row//8)%8)*0x80 + (row//64)*0x28
def find_row(addr):
    for r in range(192):
        if hgr_addr(r)==addr: return r
    return None
import sys
emu = load_emu(sys.argv[1] if len(sys.argv)>1 else r'build\a2\emu_gp.txt')
for name in ('titleh','creditsh'):
    out = decode(r'build\art\%s.bin' % name)
    diffs=0
    for y in range(192):
        r = find_row(hgr_addr(y))
        if r is None: continue
        for c in range(40):
            e = emu[y][c]
            t = out[r*40+c]
            if (e & 0x7F) != (t & 0x7F): diffs+=1
    print("%s: %d diffs" % (name, diffs))
# also show nonzero row ranges of emu_gp
nz = [y for y in range(192) if any(b!=0x80 for b in emu[y])]
if nz: print("emu_gp nonzero rows: %d..%d (%d)" % (nz[0], nz[-1], len(nz)))
