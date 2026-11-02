import sys
d = open('build/art/titleh.bin', 'rb').read()
tag = d[0]
art = bytearray()
i = 1
last = 0
while i < len(d):
    b = d[i]; i += 1
    if b == tag:
        n = d[i]; i += 1
        if n == 0:
            break
        art += bytes([last]) * n
    else:
        art.append(b); last = b
for row in (0, 1, 2):
    r = art[row * 40:(row + 1) * 40]
    print('art row%d: %s' % (row, ' '.join('%02X' % b for b in r)))
print('emitted:', len(art))
