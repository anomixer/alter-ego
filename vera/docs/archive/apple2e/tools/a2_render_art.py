"""Render an Apple //e HGR screen offline from the packed art payload and the
packed tileset, so the asset mapping can be judged without the emulator.

The runtime path is: unrle_vram() decodes the (count, value) stream into the
nametable shadow, put_tile() looks the index up in the 512-entry HGR tileset
(8 bytes per tile) and writes the tile's 8 scanlines at (col*8, row*8).
This reproduces exactly that and emits a 280x192 PNG.
"""
import sys

COLS, ROWS = 32, 30          # one NES nametable = 32x30 tiles = 256x240 px
TILE_PX = 8


def decode(stream):
    """NES neslib.s _unrle_vram (neslib.s:334-372), the tag form:

        tag = *p++
        loop: b = *p++
              b == tag -> count = *p++; count == 0 ends the stream;
                           otherwise repeat the previous byte `count` times
              b != tag -> literal: write b, and b becomes "last"

    The C shim in src/a2/neslib.c reads (count, value) pairs instead, which is
    a different stream - see the length report below.
    """
    out = bytearray()
    i = 0
    tag = stream[0]
    i = 1
    last = 0
    while i < len(stream):
        b = stream[i]
        i += 1
        if b == tag:
            count = stream[i]
            i += 1
            if count == 0:
                break
            out.extend([last] * count)
        else:
            last = b
            out.append(b)
    return out


def hgr_bytes(tileset, nametable, cols=COLS, rows=ROWS):
    """Build the HGR page: 192 scanlines x 40 bytes, in scanline order."""
    lines = [bytearray(40) for _ in range(192)]
    for idx, tile in enumerate(nametable):
        col, row = idx % cols, idx // cols
        base = tile * 8
        for r in range(8):
            y = row * 8 + r
            if y >= 192 or col >= 40:
                continue
            lines[y][col] = tileset[base + r]      # already HGR (tile_to_hgr):
            # 7 pixels in bits 6..0, bit 7 set only on a fully solid row.  Forcing
            # "| 0x80" here lit the leftmost pixel of every cell, which is what the
            # emulator showed as evenly spaced stripes.
    return lines


def main():
    art_path = sys.argv[1]
    out_png = sys.argv[2]
    stream = open(art_path, 'rb').read()
    tileset = open(r'build\hgr_tiles.bin', 'rb').read()
    nt = decode(stream)
    print('%s: stream %d bytes -> nametable %d bytes' % (art_path, len(stream), len(nt)))
    print('  first 32 indices:', ' '.join('%02X' % b for b in nt[:32]))

    lines = hgr_bytes(tileset, nt)

    # Decode the HGR bytes back to pixels: bit7 = white, the low 7 bits give
    # 4 pixels at 2 bits each (odd/even colour pairs, standard HGR colour).
    from PIL import Image
    img = Image.new('RGB', (280, 192))
    px = img.load()
    palette = [
        (0, 0, 0), (0x80, 0, 0x80), (0, 0, 0x80), (0xC0, 0, 0xC0),
        (0x40, 0, 0), (0x80, 0x80, 0x80), (0, 0, 0xC0), (0x60, 0x60, 0xC0),
        (0x80, 0x40, 0), (0xC0, 0xC0, 0), (0xC0, 0x60, 0), (0xC0, 0xC0, 0x60),
        (0, 0x80, 0), (0x00, 0xC0, 0), (0x60, 0xC0, 0x60), (0xFF, 0xFF, 0xFF),
    ]
    for y in range(192):
        for b in range(40):
            v = lines[y][b] & 0x7F
            for k in range(4):
                pair = (v >> (6 - 2 * k)) & 3
                c1 = palette[pair * 2]
                c2 = palette[pair * 2 + 1]
                x = b * 7 + k * 2
                px[x, y] = c1
                if x + 1 < 280:
                    px[x + 1, y] = c2
    img.save(out_png)
    print('wrote', out_png)


if __name__ == '__main__':
    main()
