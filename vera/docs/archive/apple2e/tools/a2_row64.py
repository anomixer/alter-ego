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
print('art row 64 (bytes 2560..2599):', ' '.join('%02X' % b for b in o[2560:2600]))
print('art row 0  (bytes 0..39)     :', ' '.join('%02X' % b for b in o[0:40]))
print('art row 8  (bytes 320..359)  :', ' '.join('%02X' % b for b in o[320:360]))
