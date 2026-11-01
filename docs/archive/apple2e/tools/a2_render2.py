import sys
from PIL import Image

def decode(path):
    data = open(path, 'rb').read()
    tag = data[0]
    out = bytearray()
    i = 1
    last = 0
    while i < len(data):
        b = data[i]
        i += 1
        if b != tag:
            out.append(b)
            last = b
        else:
            n = data[i]
            i += 1
            if n == 0:
                break
            out.extend([last] * n)
    return out

def render(decoded, path, bit_rightfirst):
    im = Image.new("RGB", (280, 192))
    px = im.load()
    for y in range(192):
        row = decoded[y*40:(y+1)*40]
        for byte in range(40):
            b = row[byte]
            for k in range(7):
                # bit_rightfirst: bit0 = leftmost (OLD/wrong); else bit6 = leftmost
                if bit_rightfirst:
                    bit = (b >> k) & 1
                else:
                    bit = (b >> (6-k)) & 1
                if bit:
                    px[byte*7+k, y] = (187, 54, 255) if (b & 0x80) else (67, 200, 0)
    im.save(path)
    return im

for name, path in (('titleh', r'build\art\titleh.bin'), ('creditsh', r'build\art\creditsh.bin')):
    dec = decode(path)
    render(dec, r'build\a2\off_%s_b6.png' % name, False)
    render(dec, r'build\a2\off_%s_b0.png' % name, True)
    print("rendered %s (len %d)" % (name, len(dec)))
