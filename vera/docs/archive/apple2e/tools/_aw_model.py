"""AppleWin DHGR-RGB decode model + err.png comparison (diagnostic tool).

Established here:
  * Scanner walks byte addresses 0..39 per line; DHGR80 call x (0..39) covers
    bytes (2k, 2k+1) for pairs k = x//2; each pair = aux[2k], main[2k],
    aux[2k+1], main[2k+1] = slots 4k..4k+3; 7 nibbles per pair, 4 out px each;
    140 cells per line.
  * nibble -> colour: ((bits&7)<<1)|((bits&8)>>3), palette 12+color.
  * isMixMode false => pure colour branch, no bit7 gating.
"""
import sys
sys.path.insert(0, r'C:\dev\alter-ego\tools')
import a2_assets as A
from PIL import Image
from collections import Counter

PAL = [(0, 0, 0), (157, 9, 102), (42, 42, 165), (199, 52, 255), (0, 128, 0),
       (128, 128, 128), (13, 161, 255), (170, 170, 255), (85, 85, 0), (242, 94, 0),
       (192, 192, 192), (255, 137, 229), (56, 203, 0), (213, 213, 26),
       (98, 246, 153), (255, 255, 255)]


def split(line80):
    main = bytearray(192 * 40)
    aux = bytearray(192 * 40)
    for y in range(192):
        for b in range(80):
            off, is_aux = A.dhgr_slot(b)
            if is_aux:
                aux[y * 40 + off] = line80[y * 80 + b]
            else:
                main[y * 40 + off] = line80[y * 80 + b]
    return main, aux


def render(main, aux, out):
    img = Image.new('RGB', (560, 192))
    px = img.load()
    for y in range(192):
        for k in range(20):
            ka = 2 * k
            b1 = aux[y * 40 + ka]
            b2 = main[y * 40 + ka]
            b3 = aux[y * 40 + ka + 1] if ka + 1 < 40 else 0
            b4 = main[y * 40 + ka + 1] if ka + 1 < 40 else 0
            dword = (b1 & 0x7F) | ((b2 & 0x7F) << 7) | ((b3 & 0x7F) << 14) | ((b4 & 0x7F) << 21)
            for i in range(7):
                bits = (dword >> (4 * i)) & 0xF
                color = ((bits & 7) << 1) | ((bits & 8) >> 3)
                rgb = PAL[color] if color < 16 else (255, 0, 255)
                for sx in range(4):
                    px[(7 * k + i) * 4 + sx, y] = rgb
    img.save(out)
    return img


def decode_rle(stream):
    tag = stream[0]
    buf = bytearray()
    i, last = 1, 0
    while i < len(stream):
        b = stream[i]
        i += 1
        if b != tag:
            buf.append(b)
            last = b
            continue
        n = stream[i]
        i += 1
        if n == 0:
            break
        buf.extend([last] * n)
    return buf


def main():
    stream = open(r'C:\dev\alter-ego\build\art\titledh.bin', 'rb').read()
    buf = decode_rle(stream)
    print('art decoded:', len(buf))
    main, aux = split(buf)
    img = render(main, aux, r'C:\dev\alter-ego\build\a2\aw_decode_sim3.png')
    print('rendered build/a2/aw_decode_sim3.png')

    # Compare with err.png pixel colours
    err = Image.open(r'C:\dev\alter-ego\err.png').convert('RGB')
    ew, eh = err.size
    cnt_err = Counter()
    for x in range(0, ew, 3):
        for y in range(0, eh, 3):
            cnt_err[err.getpixel((x, y))] += 1
    print('err.png top colours:')
    for c, n in cnt_err.most_common(12):
        print('   %s x%d' % (c, n))
    cnt_sim = Counter()
    for x in range(0, 560, 3):
        for y in range(0, 192, 3):
            cnt_sim[img.getpixel((x, y))] += 1
    print('sim3 top colours:')
    for c, n in cnt_sim.most_common(12):
        print('   %s x%d' % (c, n))


if __name__ == '__main__':
    main()
