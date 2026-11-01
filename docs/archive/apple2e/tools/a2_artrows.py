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


o = decode('build/art/titleh.bin')
print('rows 0..6 of decoded titleh:')
for r in range(7):
    print(' row %d: %s' % (r, ' '.join('%02X' % b for b in o[r * 40:(r + 1) * 40])))
