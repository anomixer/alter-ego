#!/usr/bin/env python3
"""Render a shipped HGR-screen RLE file (CREDITSH/TITLEH/...) to a PNG.

The stream is the tag form hgr.s:hgr_draw_screen decodes:

    tag = stream[0]
    b != tag -> literal: emit b, last = b
    b == tag -> n = next; n == 0 ends; else emit `last` n times

Output is 192 scanlines x 40 bytes, in the order hgr_draw_screen writes them:
40 bytes at the scanline address from hgr_lines.s, then the next line.

Colour: HGR on the //e renders byte bit7 and the pixel's horizontal parity into
one of green / violet, so a byte's 7 pixels alternate green and violet.  This
approximates that (green for even pixel index, violet for odd, bit7 selecting the
violet branch) purely to eyeball whether the bytes on the emulator match the
bytes in the file.  It is a diagnostic, not a colour-accurate emulator.
"""
import sys
from PIL import Image

COLS, ROWS = 32, 24
GREEN = (67, 200, 0)
VIOLET = (187, 54, 255)
BLACK = (0, 0, 0)


def decode(stream):
    out = bytearray()
    tag = stream[0]
    i, last = 1, 0
    while i < len(stream):
        b = stream[i]
        i += 1
        if b == tag:
            n = stream[i]
            i += 1
            if n == 0:
                break
            out.extend([last] * n)
        else:
            last = b
            out.append(b)
    return bytes(out)


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "build/art/render.png"
    stream = open(path, "rb").read()
    page = decode(stream)
    print("%s: stream %d B -> page %d B (expect 7680)" % (path, len(stream), len(page)))

    img = Image.new("RGB", (COLS * 7, ROWS * 8), BLACK)
    px = img.load()
    for line in range(ROWS * 8):
        base = line * 40
        for col in range(40):
            if base + col >= len(page):
                break
            v = page[base + col]
            for k in range(7):
                if not (v >> (6 - k)) & 1:
                    continue
                x = col * 7 + k
                if x >= COLS * 7:
                    break
                px[x, line] = VIOLET if (k & 1) or (v & 0x80) else GREEN
    img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(out)
    nz = sum(1 for b in page if b)
    print("nonzero bytes %d of %d -> %s" % (nz, len(page), out))


if __name__ == "__main__":
    main()
