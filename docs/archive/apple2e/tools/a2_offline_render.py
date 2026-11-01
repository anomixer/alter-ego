import sys
from PIL import Image

def decode_rle(path):
    data = open(path, 'rb').read()
    tag = data[0]; out = bytearray(); i = 1; last = 0
    while i < len(data):
        b = data[i]; i += 1
        if b != tag:
            out.append(b); last = b
        else:
            n = data[i]; i += 1
            if n == 0: break
            out.extend([last] * n)
    return out

def render(dec, bitorder, path):
    """Render a 192x40 HGR page (in scanline order) with the real NTSC artifact.

    Rule copied from the kit's emulator (pom2games/dev/tools/a2run/a2run.c:374-418):
        pal[hi][x&1]:  hi=0 -> violet (even col) / green (odd col);
                       hi=1 -> blue   (even col) / orange (odd col).
        a pixel with a lit neighbour reads WHITE; an isolated dot takes its
        column colour and is drawn two pixels wide.
    """
    from PIL import Image
    PAL = ((0xD0, 0x43, 0xE5), (0x2F, 0xB8, 0x1F),   # [hi=0] violet, green
           (0x1A, 0x8F, 0xFF), (0xF0, 0x6A, 0x1C))   # [hi=1] blue,   orange
    WHITE = (0xFF, 0xFF, 0xFF)
    im = Image.new("RGB", (280, 192))
    px = im.load()
    for y in range(192):
        on = [0] * 282                       # 1-indexed: on[1+x] = pixel x
        hi = [0] * 280
        for byte in range(40):
            b = dec[y * 40 + byte]
            for k in range(7):
                bit = (b >> k) & 1 if bitorder == 0 else (b >> (6 - k)) & 1
                on[1 + byte * 7 + k] = bit
                hi[byte * 7 + k] = b >> 7
        col = [0] * 280
        for x in range(280):
            if on[1 + x]:
                col[x] = WHITE if (on[x] or on[2 + x]) else PAL[hi[x] * 2 + (x & 1)]
        for x in range(279, 0, -1):
            if not on[1 + x] and on[x] and col[x - 1] != WHITE:
                col[x] = col[x - 1]
        for x in range(280):
            px[x, y] = col[x]
    im.save(path)

dec = decode_rle(r'build\art\titleh.bin')
render(dec, 0, r'build\a2\off_bit0.png')
render(dec, 1, r'build\a2\off_bit6.png')
print("wrote off_bit0.png (pixel k = bit k) and off_bit6.png (pixel k = bit 6-k)")
