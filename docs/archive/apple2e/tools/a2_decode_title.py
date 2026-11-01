import sys
data = open(r'build\art\titleh.bin', 'rb').read()
tag = data[0]
out = bytearray()
i = 1
last = 0
steps = 0
while i < len(data):
    b = data[i]
    i += 1
    if b != tag:
        out.append(b)
        last = b
        steps += 1
    else:
        n = data[i]
        i += 1
        if n == 0:
            print("STOP at byte %d (0x%X): read tag=%02X then n=0. emitted=%d, src_bytes=%d" % (i-2, i-2, tag, len(out), i))
            break
        out.extend([last] * n)
        steps += n
else:
    print("EOF without terminator: emitted=%d src_bytes=%d" % (len(out), i))
print("total emitted=%d (expected 7680)" % len(out))
# Find where the decode's src_ptr would be at the end
print("src_ptr end = $%04X" % (0x1000 + i))
# Check the last bytes before terminator
print("last 12 source bytes:", ' '.join('%02X' % x for x in data[max(0,i-12):i]))
