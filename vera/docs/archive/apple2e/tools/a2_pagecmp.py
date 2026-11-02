import sys
page = open('build/a2/at_2000_1E00.bin', 'rb').read()  # display order: page[y*40+b]
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
diff = 0
first = None
for y in range(192):
    for b in range(40):
        e = page[y * 40 + b]
        a = art[y * 40 + b] | 0x80
        if e != a:
            diff += 1
            if first is None:
                first = (y, b, e, a)
print('total diff bytes:', diff)
if first:
    print('first diff: y=%d b=%d emu=%02X art=%02X' % (first[0], first[1], first[2], first[3]))
# print first 3 rows of both
for y in range(3):
    print('emu row%d: %s' % (y, ' '.join('%02X' % page[y*40:(y+1)*40][b] for b in range(40))))
    print('art row%d: %s' % (y, ' '.join('%02X' % (art[y*40+b] | 0x80) for b in range(40))))
