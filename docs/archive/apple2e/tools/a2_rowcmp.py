import sys
def decode(path):
    d = open(path, 'rb').read()
    tag = d[0]
    out = bytearray()
    i = 1
    last = 0
    while i < len(d):
        b = d[i]; i += 1
        if b == tag:
            n = d[i]; i += 1
            if n == 0:
                break
            out += bytes([last]) * n
        else:
            out.append(b); last = b
    return out
for p in ['build/art/titleh.bin', 'build/art/creditsh.bin']:
    out = decode(p)
    r = out[100 * 40:100 * 40 + 40]
    print('%-30s row100: %s' % (p, ' '.join('%02X' % b for b in r)))
