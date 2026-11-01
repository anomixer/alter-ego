#!/usr/bin/env python3
"""Extract the NES RLE art payloads from the C headers into DOS 3.3 files.

The Apple //e build does not link the title, credits, game-over and well-done
screens into the program: src/game.c reaches them through ART() in
src/a2/level_stream.h, which BLOAD-s the named disk file into the $1000 staging
page and hands that address to unrle_vram().  These are the files it loads.

The payload is the byte array exactly as the NES build stores it - the same
_unrle_vram stream, decoded by src/a2/hgr.s: hgr_draw_screen.  Nothing is
re-encoded here; the numbers in the header are copied out verbatim.

Usage:  python tools/a2_art.py [build/art]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a2_assets import (rle_encode_screen, tile_to_hgr, chr_tiles,   # noqa: E402
                       put_cell, DHGR_HEIGHT, DHGR_BYTES_PER_LINE)

SRC = "src"
ARRAY = re.compile(r"const unsigned char\s+(\w+)\s*\[\s*\d*\s*\]\s*=\s*\{(.*?)\}",
                   re.S)
BYTE = re.compile(r"0[xX][0-9A-Fa-f]{2}")

# Disk file name -> (header, C array).  DOS 3.3 names are 15 characters,
# uppercase, no extension: all four fit.
ART = [
    ("TITLE", "title.h", "title"),
    ("CREDITS", "credits.h", "credits"),
    ("GAMEOVER", "gameover.h", "gameover"),
    ("WELLDONE", "welldone.h", "welldone"),
]

MAX_STAGING = 4096
COLS, ROWS = 32, 24          # the //e viewport: 32 x 24 tiles = 224 x 192 px
# The NES nametable is 32 x 30 tiles = 256 x 240 px; HGR is 280 x 192.  240 lines
# do not fit in 192, so a window of 24 nametable rows is taken.  Measured from
# the art itself: the title screen uses nametable rows 4-23 (plus 30-31, which
# are the bottom border) and the credits use rows 7-25.  Rows 3..26 is the
# narrowest window that contains both, so nothing legible is cropped.  Mapping
# rows 0..23 instead cut the credits' last text row and left the bottom 32
# scanlines of the HGR page untouched.
ROW0 = 3


def decode(stream):
    """The tag-form stream _unrle_vram / hgr_draw_screen use:

        tag = stream[0]
        b != tag -> literal: emit b, last = b
        b == tag -> n = next; n == 0 ends; else emit `last` n times
    """
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


def colorize_byte(mono, col, word):
    """Tint one mono HGR byte into the chosen artifact colour (the title's two
    words are a single CHR shape tinted by two NES palettes; HGR reproduces that
    by keeping only the pixel parity that reads as the chosen hue).

    The real HGR artifact rule (pom2games/dev/tools/a2run/a2run.c:374-418):
        pal[hi][x&1]:  hi=1 -> blue (even col) / orange (odd col);  hi=0 ->
        violet / green.  So ORANGE needs hi=1 + an odd absolute column x and
        BLUE needs hi=1 + an even absolute column x.  Absolute column x = col*7+k
        (7 odd) so x&1 = (col&1)^(k&1): the carrier keeps the bit parity k that
        makes x odd (ORANGE) or even (BLUE), and 0x80 sets hi=1.
    """
    if word == 'ORANGE':
        carrier = 0x2A if col % 2 == 0 else 0x55   # odd x  -> odd k on even col
    else:  # BLUE
        carrier = 0x55 if col % 2 == 0 else 0x2A   # even x -> even k on even col
    return 0x80 | (mono & carrier)


# The title's two words are the same CHR shapes tinted by two NES palettes, so
# the colour difference is purely which palette each glyph uses.  The glyphs
# are disjoint tile sets: the big "ALTER EGO" letters are tiles 0x01-0x2e +
# 0xb8-0xbf (rows 3-11 of the nametable), the "PRESS START" letters are tiles
# 0x40-0x7f (rows 11-13).  The split is by tile index, matching the user's
# reference: ORANGE "ALTER EGO" on top, BLUE "PRESS START" below.
TITLE_PRESS_START_TILES = frozenset(
    range(0x40, 0x80))


def hgr_page(tileset, nametable, colorize=True):
    """Nametable -> 192 x 40 HGR page, in scanline order (40 bytes per line).

    Rows ROW0..ROW0+23 of the 32 x 30 nametable become the 192 HGR scanlines;
    each tile row is one byte, and a tile occupies 7 pixels (tile_to_hgr keeps
    the 7 left pixels of the NES tile, so a 32-tile row is 224 pixels wide).
    With colorize (the title only), the glyph tiles are tinted per row band
    into ORANGE / BLUE; the other screens stay mono.
    """
    page = bytearray(192 * 40)
    for idx, tile in enumerate(nametable):
        col, row = idx % COLS, idx // COLS
        if col >= 40:
            continue
        out_row = row - ROW0
        if out_row < 0 or out_row >= ROWS:
            continue
        # hgr_tiles.bin is already in HGR byte form: chr_tiles() reads the CHR
        # blob (bit 7 = leftmost pixel, verified by rendering) into pixel rows,
        # and tile_to_hgr() packs them with bit 6 = pixel 0 (leftmost).  So the
        # tile byte b[r] IS the HGR byte for that row - using it directly is
        # correct.  Re-converting it through tile_to_hgr(rows) bit-reversed the
        # byte (rows[k]=bit k, then tile_to_hgr places bit k at position 6-k),
        # which mirrored every glyph.
        b = tileset[tile * 8:tile * 8 + 8]
        for r in range(8):
            # Scanline is (out_row*8 + r); the page is 40 bytes per scanline, so
            # the 40 multiplies the SCANLINE.  Writing out_row*8 + r*40 + col
            # instead multiplies the row-within-the-tile, which scattered the
            # tiles over a handful of lines and left the page 99% zero (measured:
            # 34 nonzero bytes of 7,680 for the title screen).
            v = b[r]
            if colorize:
                word = 'BLUE' if tile in TITLE_PRESS_START_TILES else 'ORANGE'
                v = colorize_byte(v, col, word)
            page[(out_row * 8 + r) * 40 + col] = v
    return bytes(page)


# DHGR palette: CHR shade -> DHGR/LORES colour number, per title word.
# ALTER EGO (orange family): shade 3 -> ORANGE(9), 2 -> BROWN(8).
# PRESS START (blue family): shade 3 -> BLUE(6), 2 -> DARKBLUE(2).
ORANGE_MAP = {0: 0, 1: 8, 2: 8, 3: 9}
BLUE_MAP = {0: 0, 1: 2, 2: 2, 3: 6}


def dhgr_page(shades, nametable, colorize=True):
    """Nametable -> interleaved 80-slot DHGR page (15,360 bytes).

    shades is chr_tiles() output (flat 64 shades per tile).  Each 8x8 tile is
    2 DHGR colour cells per row (4 px each); the dominant shade of each cell is
    mapped to a DHGR colour by the title's ORANGE/BLUE palette (colourise) or
    kept as the raw shade (no colourise).  The page is returned as the
    interleaved byte sequence dhgr_draw_screen consumes: line 0 slots 0..79,
    line 1 slots 0..79, ...  Slot parity picks the bank at write time.
    """
    lines = [[0] * DHGR_BYTES_PER_LINE for _ in range(DHGR_HEIGHT)]
    for idx, tile in enumerate(nametable):
        col, row = idx % COLS, idx // COLS
        out_row = row - ROW0
        if out_row < 0 or out_row >= ROWS:
            continue
        tp = shades[tile]
        cmap = None
        if colorize:
            cmap = BLUE_MAP if tile in TITLE_PRESS_START_TILES else ORANGE_MAP
        for r in range(8):
            rowpx = tp[r * 8:(r + 1) * 8]
            left = rowpx[0:4]
            right = rowpx[4:8]
            if cmap:
                put_cell(lines[out_row * 8 + r], col * 2, cmap[max(left)])
                put_cell(lines[out_row * 8 + r], col * 2 + 1, cmap[max(right)])
            else:
                put_cell(lines[out_row * 8 + r], col * 2, max(left))
                put_cell(lines[out_row * 8 + r], col * 2 + 1, max(right))
    # flatten to interleaved slot order
    return bytes(b for ln in lines for b in ln)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join("build", "art")
    os.makedirs(out_dir, exist_ok=True)

    tileset = open(os.path.join("build", "hgr_tiles.bin"), "rb").read()
    if len(tileset) < 256 * 8:
        sys.exit("build/hgr_tiles.bin too short for 256 tiles")
    chr_blob = open(os.path.join(SRC, "tileset.chr"), "rb").read()

    total = 0
    for disk_name, header, array in ART:
        text = open(os.path.join(SRC, header), "r", encoding="utf-8",
                    errors="replace").read()
        match = ARRAY.search(text)
        if not match:
            sys.exit("%s: no array named %s" % (header, array))
        if match.group(1) != array:
            sys.exit("%s: found %s, expected %s" % (header, match.group(1), array))
        data = bytes(int(t, 16) for t in BYTE.findall(match.group(2)))
        if len(data) > MAX_STAGING:
            sys.exit("%s: %d bytes does not fit the $1000 staging page"
                     % (header, len(data)))
        path = os.path.join(out_dir, disk_name.lower() + ".bin")
        with open(path, "wb") as fh:
            fh.write(data)
        total += len(data)

        # The form the //e build actually paints: a real HGR page, RLE'd with the
        # tag scheme hgr_draw_screen() decodes.  The nametable stream needs
        # unrle_vram -> put_tile -> hgr_set_row/hgr_put8, and measured on AppleWin
        # that path painted only ~31 of a screen's 768 tiles.
        nametable = decode(data)
        enc = rle_encode_screen(hgr_page(tileset, nametable,
                                         colorize=(array == 'title')))
        if len(enc) > MAX_STAGING:
            sys.exit("%sH: %d bytes does not fit the $1000 staging page"
                     % (disk_name, len(enc)))
        hpath = os.path.join(out_dir, disk_name.lower() + "h.bin")
        with open(hpath, "wb") as fh:
            fh.write(enc)
        print("%-9s %5d B stream | nametable %4d -> HGR RLE %5d B -> %s"
              % (disk_name, len(data), len(nametable), len(enc), hpath))

        # DHGR form (the real-colour screen the game now paints): an interleaved
        # 80-slot page, RLE'd with the same tag scheme dhgr_draw_screen decodes.
        denc = rle_encode_screen(dhgr_page(chr_tiles(chr_blob), nametable,
                                           colorize=(array == 'title')))
        if len(denc) > MAX_STAGING:
            sys.exit("%sDH: %d bytes does not fit the $1000 staging page"
                     % (disk_name, len(denc)))
        dpath = os.path.join(out_dir, disk_name.lower() + "dh.bin")
        with open(dpath, "wb") as fh:
            fh.write(denc)
        print("%-9s DHGR RLE %5d B -> %s" % (disk_name, len(denc), dpath))

    print("total %d bytes, largest single load %d of %d available"
          % (total, max(len(bytes(int(t, 16) for t in BYTE.findall(
              ARRAY.search(open(os.path.join(SRC, h), 'r', encoding='utf-8',
                                    errors='replace').read()).group(2))))
              for _, h, _ in ART), MAX_STAGING))


if __name__ == "__main__":
    main()
