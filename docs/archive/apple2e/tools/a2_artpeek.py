import sys
from collections import Counter


def decode(path):
    d = open(path, 'rb').read()
    tag = d[0]
    i, last, out = 1, 0, []
    while i < len(d):
        b = d[i]
        i += 1
        if b != tag:
            out.append(b)
            last = b
        else:
            n = d[i]
            i += 1
            if n == 0:
                break
            out.extend([last] * n)
    return out


for p in ('build/art/titleh.bin', 'build/art/creditsh.bin'):
    o = decode(p)
    c = Counter(o)
    print(p, 'emitted', len(o), 'top:', [(hex(v), n) for v, n in c.most_common(6)])
    print('   count of 28:', c.get(0x28, 0), ' count of 00:', c.get(0, 0))
    print('   row0:', ' '.join('%02X' % b for b in o[:40]))
