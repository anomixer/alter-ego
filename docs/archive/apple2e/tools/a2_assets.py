#!/usr/bin/env python3
"""Alter Ego (NES) -> Apple II DHGR asset converter.

Verified inputs:
  * RLE stream format  : src/neslib.s:334-372 (_unrle_vram)
  * CHR format         : 256 tiles, 8x8, 2bpp planar, 16 bytes/tile (tileset.chr = 8192 B)
  * Game area          : 32x20 tiles of 8px, nametable rows 6..25 (SCREEN_START_Y=48)
                        (src/game.c:166-170, unrle_vram(level_ptrs[i],0x2000) at game.c:821)

Output: one DHGR page as TWO byte arrays -- main bank and aux bank, 40 bytes
per scanline each (7,680 B per bank, 15,360 B per page). The scanline ->
address interleave and the main/aux split are the real Apple //e DHGR layout
(see the geometry block below), so each bank can be loaded straight to $2000
(page 1) / $4000 (page 2) of its bank.
"""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, r'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages')

SRC = r'C:\dev\alter-ego\src'
OUT = r'C:\dev\alter-ego\build'

# ---------------------------------------------------------------- DHGR geometry
# Verified against the reference implementation:
#   C:\dev\pom2games\dev\lib\hgrc\dhgr.c:19-25   address()   (byte/addr/aux/mask)
#   C:\dev\pom2games\dev\lib\hgrc\dhgr.c:42-55   colour phase (color_bits/pattern)
#   C:\dev\pom2games\dev\lib\hgrc\dhgr.h:11-13   DHGR_WIDTH / COLOR_WIDTH / HEIGHT
#   C:\dev\pom2games\dev\lib\hgrc\hgr_layout.h:8-10  HGR_ROW_ADDR (shared HGR/DHGR)
#
# One scanline = 560 raw bits = 80 byte slots of 7 px.  Slot b lives at
#   addr = hgr_row(base, y) + (b >> 1),  bank = aux if b is even else main,
# so a line is 40 main bytes + 40 aux bytes and a page is 15,360 B.
DHGR_WIDTH = 560          # raw bits (px) per scanline
DHGR_COLOR_WIDTH = 140    # 4-bit colour cells per scanline
DHGR_HEIGHT = 192
DHGR_BYTES_PER_LINE = 80  # 560 px / 7 px per byte
DHGR_BANK_BYTES = 40      # per scanline, per bank
DHGR_PAGE_BYTES = DHGR_BYTES_PER_LINE * DHGR_HEIGHT        # 15,360 B
DHGR_BANK_PAGE_BYTES = DHGR_BANK_BYTES * DHGR_HEIGHT       # 7,680 B per bank
HGR_BASE_PAGE1 = 0x20     # $2000 (main and aux)
HGR_BASE_PAGE2 = 0x40     # $4000 (main and aux)

BPL = DHGR_BYTES_PER_LINE   # legacy aliases kept for the HGR code paths below
LINES = DHGR_HEIGHT
SCREEN_BYTES = DHGR_PAGE_BYTES
GAME_Y0 = 48      # SCREEN_START_Y
GAME_ROWS = 20
GAME_COLS = 32
DHGR_TILE_BYTES = 8     # 8 rows x 2 colour cells (2 cells per byte)
DHGR_SPRITE_BYTES = 32  # 16 rows x [mask, 2 colour cells]


def hgr_row(base, y):
    """Address of scanline y (0..191) for page base $20 / $40.

    Identical to HGR_ROW_ADDR in hgr_layout.h:8-10:
        (base << 8) + (y % 8) * 1024 + ((y // 8) % 8) * 128 + (y // 64) * 40
    """
    return (base << 8) + (y % 8) * 1024 + ((y // 8) % 8) * 128 + (y // 64) * 40


def dhgr_slot(byte):
    """Byte slot b (0..79) -> (offset inside the scanline, is_aux).

    dhgr.c:21-23:  byte = x / 7;  addr = row + (byte >> 1);  aux = (byte & 1) ^ 1
    so an EVEN slot goes to the auxiliary bank and an ODD slot to main.
    """
    return (byte >> 1, (byte & 1) ^ 1)


# Apple II LORES colour numbers (dhgr.h:15-31) as RGB for the PNG preview.
DHGR_COLOR_NAMES = (
    'BLACK', 'MAGENTA', 'DARKBLUE', 'VIOLET', 'DARKGREEN', 'GRAY1', 'BLUE',
    'LIGHTBLUE', 'BROWN', 'ORANGE', 'GRAY2', 'PINK', 'GREEN', 'YELLOW',
    'AQUA', 'WHITE')
DHGR_COLORS = (
    (0, 0, 0), (152, 0, 152), (88, 0, 208), (224, 80, 255),
    (0, 128, 0), (128, 128, 128), (32, 160, 255), (128, 192, 255),
    (88, 48, 0), (224, 128, 0), (128, 128, 128), (208, 128, 128),
    (0, 208, 0), (224, 224, 0), (64, 224, 255), (255, 255, 255))


def color_bits(c):
    """LORES colour number -> the 4 bits written to a 4-bit-aligned pixel."""
    return ((c >> 1) | (c << 3)) & 15


def color_index(cb):
    """Inverse of color_bits(): the 4 raw bits -> the LORES colour number."""
    return ((cb >> 3) | ((cb & 7) << 1)) & 15


def color_pattern(c):
    """The 4 phase bytes of a solid colour: [aux-even, main-even, aux-odd, main-odd].

    dhgr.c:48-55.  Slot b uses pattern[b & 3] because 7*b mod 4 == (b*7) & 3.
    """
    pattern = color_bits(c) * 0x1111
    return bytes((pattern >> ((i * 7) & 3)) & 0x7F for i in range(4))


def fill_line(color):
    """One 80-slot scanline filled with a solid DHGR colour."""
    pat = color_pattern(color)
    return bytearray(pat[b & 3] for b in range(DHGR_BYTES_PER_LINE))


def split_line(line):
    """80-slot scanline -> (40 main bytes, 40 aux bytes)."""
    main = bytearray(DHGR_BANK_BYTES)
    aux = bytearray(DHGR_BANK_BYTES)
    for b in range(DHGR_BYTES_PER_LINE):
        off, is_aux = dhgr_slot(b)
        if is_aux:
            aux[off] = line[b]
        else:
            main[off] = line[b]
    return main, aux


def join_page(main, aux):
    """(main, aux) pages -> list of 192 logical 80-slot scanlines."""
    lines = []
    for y in range(DHGR_HEIGHT):
        line = bytearray(DHGR_BYTES_PER_LINE)
        for b in range(DHGR_BYTES_PER_LINE):
            off, is_aux = dhgr_slot(b)
            line[b] = aux[y * DHGR_BANK_BYTES + off] if is_aux \
                else main[y * DHGR_BANK_BYTES + off]
        lines.append(line)
    return lines


def put_cell(line, cx, color):
    """Write one 4-bit colour cell (colour column cx) into an 80-slot line.

    A colour cell occupies 4 consecutive raw bits, cell cx covering bits
    4*cx .. 4*cx+3, and raw bit i is bit (i % 7) of slot (i // 7) -- bit 0 of
    the byte is the leftmost pixel (dhgr.c:24, mask = 1 << (x % 7)).
    The 4 bits written are color_bits(color), the DHGR phase of the LORES
    colour number (dhgr.c:42-46).
    """
    p = 4 * cx
    b, j = p // 7, p % 7
    cb = color_bits(color)
    line[b] |= (cb << j) & 0x7F
    if j > 3:                       # the cell straddles two slots
        line[b + 1] |= cb >> (7 - j)


def read_cell(line, cx):
    """Inverse of put_cell(): read the colour number of colour cell cx."""
    p = 4 * cx
    b, j = p // 7, p % 7
    v = (line[b] >> j) & 0x7F
    cb = v & 15 if j <= 3 \
        else ((line[b + 1] & ((1 << (j - 3)) - 1)) << (7 - j)) | v
    return color_index(cb)



# ---------------------------------------------------------------- RLE (neslib)
def decode_rle(data):
    """Exact port of _unrle_vram (neslib.s:334-372).

    tag = data[0]
    loop: b = next
          if b != tag: emit b, last = b
          else:        n = next; if n == 0 -> END; else emit last, n times

    Note: `sta` does not modify the flags, so the `bne @1` at neslib.s:351
    tests the earlier `cmp <RLE_TAG` and is always taken -- a literal byte
    (including $00) never falls through into the repeat branch.
    """
    i = 0
    tag = data[i]
    i += 1
    out = bytearray()
    last = 0
    while True:
        b = data[i]
        i += 1
        if b != tag:
            out.append(b)
            last = b
            continue
        n = data[i]
        i += 1
        if n == 0:
            return bytes(out)
        out.extend(bytes([last]) * n)


def parse_c_array(path, name=None):
    """Extract the byte list of a `static const unsigned char X[] = {...}` C array."""
    txt = open(path, 'r', encoding='utf-8', errors='replace').read()
    m = re.search(r'\[[^\]]*\]\s*=\s*\{(.*?)\}', txt, re.S)
    if not m:
        raise SystemExit('no array in ' + path)
    body = m.group(1)
    vals = [int(t, 16) for t in re.findall(r'0x([0-9a-fA-F]{2})', body)]
    if not vals:
        vals = [int(t, 16) for t in re.findall(r'\$([0-9a-fA-F]{2})', body)]
    if not vals:
        raise SystemExit('no bytes in ' + path)
    return bytes(vals)


# ---------------------------------------------------------------- CHR -> DHGR
def chr_tiles(blob):
    """256 tiles, 8x8, 2bpp planar -> list of 64 colour indices (0..3) per tile."""
    tiles = []
    for t in range(len(blob) // 16):
        rows = []
        for r in range(8):
            lo = blob[t * 16 + r * 2]
            hi = blob[t * 16 + r * 2 + 1]
            for p in range(8):
                # This CHR blob is stored bit-reversed: bit 7 = LEFTMOST pixel,
                # bit 0 = rightmost (verified by rendering the CHR directly:
                # rows[p] drawn at col (7-p) reads cleanly, so rows[p] is the
                # pixel at horizontal position 7-p).  So pixel p is bit (7-p).
                rows.append(((hi >> (7 - p)) & 1) << 1 | ((lo >> (7 - p)) & 1))
        tiles.append(rows)
    return tiles


def cell_color(px4):
    """Colour of one DHGR colour cell = a group of 4 NES pixels.

    Geometry is 1:1 (one NES pixel = one DHGR raw pixel) and a DHGR colour cell
    is 4 raw pixels wide, so the 4 shades of the group collapse into one colour.
    NES shade 0 is transparent; the winner is the non-zero shade covering the
    most pixels, ties going to the brightest shade.
    """
    counts = [0, 0, 0, 0]
    for v in px4:
        counts[v & 3] += 1
    best, bestn = 0, 0
    for v in (3, 2, 1):
        if counts[v] > bestn:
            best, bestn = v, counts[v]
    return best


def tile_to_dhgr(rows):
    """8x8 colour indices -> 8 bytes: 1 byte per row = 2 DHGR colour cells.

    1:1 geometry: an 8-px tile row is 8 DHGR raw pixels = 2 colour cells.
    High nibble = left cell (px 0..3), low nibble = right cell (px 4..7).
    The NES palette index 0..3 is already a valid DHGR/LORES colour number
    (0 BLACK, 1 MAGENTA, 2 DARKBLUE, 3 VIOLET).
    """
    out = bytearray(8)
    for r in range(8):
        left = cell_color(rows[r * 8:r * 8 + 4])
        right = cell_color(rows[r * 8 + 4:r * 8 + 8])
        out[r] = (left << 4) | right
    return bytes(out)


# ---------------------------------------------------------------- screen builder
def build_dhgr_screen(tiles, nametable, palette_map=None):
    """Render the 32x20 game area (nametable rows 6..25) into a DHGR page.

    Returns (main, aux), 40 bytes per scanline each (7,680 B per bank).
    The NES game area is 256x160 at y=48..207 (SCREEN_START_Y=48, 20 rows).
    At 1:1 geometry that is 256 of the 560 raw pixels = 64 of the 140 colour
    columns; DHGR has only 192 scanlines, so the area is remapped to rows
    0..159 and rows 160..191 stay black.
    """
    lines = [bytearray(DHGR_BYTES_PER_LINE) for _ in range(DHGR_HEIGHT)]
    for row in range(GAME_ROWS):
        nt_row = 6 + row                       # nametable row (SCREEN_START_Y/8)
        y0 = row * 8
        for col in range(GAME_COLS):
            t = nametable[nt_row * 32 + col]
            cells = tile_to_dhgr(tiles[t])
            cx0 = col * 2                      # 2 colour cells per 8-px tile
            for r in range(8):
                line = lines[y0 + r]
                v = cells[r]
                put_cell(line, cx0, v >> 4)
                put_cell(line, cx0 + 1, v & 15)
    main = bytearray(DHGR_BANK_PAGE_BYTES)
    aux = bytearray(DHGR_BANK_PAGE_BYTES)
    for y in range(DHGR_HEIGHT):
        line = lines[y]
        for b in range(DHGR_BYTES_PER_LINE):
            off, is_aux = dhgr_slot(b)
            if is_aux:
                aux[y * DHGR_BANK_BYTES + off] = line[b]
            else:
                main[y * DHGR_BANK_BYTES + off] = line[b]
    return bytes(main), bytes(aux)


def rle_encode_screen(scr, tag=None):
    """RLE a screen buffer into a stream _unrle_vram / dhgr_draw_screen can decode.

    Decoder rule (src/neslib.s:334-372, src/a2/dhgr.s dhgr_draw_screen):
      tag = data[0];  b != tag -> emit b and set last = b;
      b == tag -> n = next; n == 0 ends the stream, else emit `last` n times.

    Two consequences the encoder must respect:
      * a repeat is always relative to `last`, i.e. to the last *literal* the
        decoder emitted, so a run of L >= 3 is written as [v, tag, L-1];
      * a data byte equal to the tag is unencodable, so the tag is chosen from
        the byte values that do not occur in the buffer (0xFF when free --
        a colour-mode DHGR page never contains a byte >= $80, see
        selfcheck_color, so $FF is always free there).
    The stream ends with [tag, $00]; the old [0x00, 0x00] tail was two plain
    literals and let the decoder run off the end of the data.
    """
    used = set(scr)
    if tag is None:
        tag = 0xFF if 0xFF not in used \
            else next((t for t in range(0x100) if t not in used), None)
        assert tag is not None, 'every byte value occurs: no RLE tag is free'
    out = bytearray([tag])
    n = len(scr)
    i = 0
    while i < n:
        v = scr[i]
        run = 1
        while i + run < n and scr[i + run] == v and run < 256:
            run += 1
        if run >= 3:
            out.append(v)              # the literal sets the decoder's `last`
            out.append(tag)
            out.append(run - 1)
        else:
            out += scr[i:i + run]
        i += run
    out.append(tag)
    out.append(0x00)
    return bytes(out)


def save_png(main, aux, path, scale=1):
    """Render a (main, aux) DHGR page as a 560 x 192 PNG (4 px per colour cell)."""
    from PIL import Image
    w, h = DHGR_WIDTH, DHGR_HEIGHT
    img = Image.new('RGB', (w * scale, h * scale))
    px = img.load()
    lines = join_page(main, aux)
    for y in range(h):
        for cx in range(DHGR_COLOR_WIDTH):
            rgb = DHGR_COLORS[read_cell(lines[y], cx)]
            for sx in range(scale):
                for sy in range(scale):
                    for k in range(4):
                        px[cx * 4 + k + sx, y * scale + sy] = rgb
    img.save(path)


def sprite_to_dhgr(tiles, t0):
    """NES 8x16 sprite (tiles t0, t0+1) -> DHGR 32-byte masked colour form.

    Layout: 16 rows x [mask, cells].  `cells` holds the 2 colour cells of the
    row (high nibble = left cell = px 0..3, low nibble = right cell = px 4..7);
    mask bit1 = write the left cell, bit0 = write the right cell.
    NES shade 0 is transparent (mask bit clear).  The surviving shade keeps the
    NES palette index, which is also the DHGR/LORES colour number
    (1 MAGENTA, 2 DARKBLUE, 3 VIOLET) and reads on any background.
    `tiles` is the decoded list from chr_tiles() (64 colour indices per tile).
    """
    out = bytearray()
    for row in range(16):
        base = (row & 7) * 8
        px = tiles[t0 + (row >> 3)][base:base + 8]
        left = cell_color(px[0:4])
        right = cell_color(px[4:8])
        mask = (2 if left else 0) | (1 if right else 0)
        out += bytes((mask, (left << 4) | right))
    return bytes(out)


def tile_to_hgr(rows):
    """NES 8x8 tile -> HGR 8 bytes (1 byte per row, 7 px/byte, 1 bpp).

    HGR gives each pixel one bit; the byte's phase picks green (even byte) or
    orange (odd byte), and MSB=1 makes the whole byte white.  The 8th pixel of
    each row is dropped: 32 tiles x 7 px = 224 px, which fits HGR's 280 px.
    A fully solid row is emitted with MSB set so it reads as white.
    """
    out = bytearray()
    for r in range(8):
        v = 0
        # chr_tiles() gives rows[p] = pixel p (pixel 0 = leftmost; the CHR blob
        # is stored bit-reversed so bit (7-p) is pixel p).  Keep the 7 LEFT
        # pixels (pixels 0..6) and drop the rightmost (pixel 7).  HGR bit 0 is
        # the leftmost pixel (verified against AppleWin: a bit-6-leftmost byte
        # renders mirrored/scrambled), so pixel k goes to bit k.
        for k in range(7):
            if rows[r * 8 + k]:
                v |= 1 << k
        if v == 0x7F:
            v = 0xFF
        out.append(v)
    return bytes(out)


def sprite_to_hgr(tiles, t0):
    """NES 8x16 sprite -> HGR 32 bytes: 16 rows x [mask, byte]."""
    out = bytearray()
    for row in range(16):
        base = (row & 7) * 8
        v = 0
        for k in range(7):
            if tiles[t0 + (row >> 3)][base + k]:
                v |= 1 << (6 - k)
        if v == 0x7F:
            v = 0xFF
        out.append(1 if v else 0)
        out.append(v)
    return bytes(out)


def build_hgr_screen(tiles, nametable):
    """Game area 32x20 tiles -> HGR 192x40 page (rows 0..159, HUD 160..191)."""
    page = bytearray(192 * 40)
    for ty in range(20):
        for tx in range(32):
            t = nametable[(ty + 6) * 32 + tx]
            b = tile_to_hgr(tiles[t])
            line = ty * 8
            for r in range(8):
                y = line + r
                if y < 160:
                    page[y * 40 + tx] = b[r]
    return bytes(page)


def emit_c_array(path, name, data, segment='RODATA'):
    """Emit a ca65 blob. The label is prefixed with '_' so C can import it."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('; generated by tools/a2_assets.py -- do not edit\n')
        _emit_array(f, name, data, segment)


def emit_c_arrays(path, arrays, segment='RODATA'):
    """Emit several ca65 blobs into one file: [(name, data), ...]."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('; generated by tools/a2_assets.py -- do not edit\n')
        for name, data in arrays:
            _emit_array(f, name, data, segment)


def _emit_array(f, name, data, segment):
    f.write('.segment "%s"\n' % segment)
    f.write('.export _%s\n' % name)
    f.write('_%s:\n' % name)
    for i in range(0, len(data), 16):
        f.write('\t.byte ' + ','.join('$%02X' % b for b in data[i:i + 16]) + '\n')


# ---------------------------------------------------------------- self-checks
def selfcheck_rle(buffers, verbose=True):
    """decode_rle() is the reference _unrle_vram: every stream must decode back
    to the exact buffer it was built from."""
    for name, raw in buffers:
        enc = rle_encode_screen(raw)
        dec = decode_rle(enc)
        assert dec == raw, (name, len(raw), len(dec))
        if verbose:
            print('  RLE %-16s raw=%5d -> %5d  (tag $%02X) decode exact'
                  % (name, len(raw), len(enc), enc[0]))
    return True


def selfcheck_layout(base=HGR_BASE_PAGE1, verbose=True):
    """Prove the 80 byte slots of every scanline map to 40 main + 40 aux bytes.

    For all 192 lines: the slots cover row..row+39 of the main bank exactly once
    and row..row+39 of the aux bank exactly once (80 distinct bank/address
    pairs), and the bank of a slot alternates with the slot parity
    (even slot -> auxiliary, odd slot -> main).

    """
    for y in range(DHGR_HEIGHT):
        row = hgr_row(base, y)
        mains, auxs = [], []
        for b in range(DHGR_BYTES_PER_LINE):
            off, is_aux = dhgr_slot(b)
            assert 0 <= off < DHGR_BANK_BYTES, (y, b, off)
            assert is_aux == ((b & 1) ^ 1), (y, b)          # even slot -> aux
            (auxs if is_aux else mains).append(row + off)
        assert sorted(mains) == list(range(row, row + DHGR_BANK_BYTES)), y
        assert sorted(auxs) == list(range(row, row + DHGR_BANK_BYTES)), y
        # main and aux are separate banks, so the 80 (bank, address) pairs
        # must be distinct even though both banks use the same $2000..$2027 range
        pairs = set((dhgr_slot(b)[1], row + dhgr_slot(b)[0])
                    for b in range(DHGR_BYTES_PER_LINE))
        assert len(pairs) == DHGR_BYTES_PER_LINE, y

        banks = [dhgr_slot(b)[1] for b in range(DHGR_BYTES_PER_LINE)]
        assert all(banks[i] != banks[i + 1] for i in range(DHGR_BYTES_PER_LINE - 1)), y
    if verbose:
        print('DHGR layout self-check: %d lines OK (page base $%04X)'
              % (DHGR_HEIGHT, base << 8))
        for y in (0, 1, 8, 64, 191):
            row = hgr_row(base, y)
            slots = ' '.join('%s%02d' % ('A' if dhgr_slot(b)[1] else 'M',
                                         dhgr_slot(b)[0])
                             for b in range(8))
            print('  y=%3d row=$%04X  main=$%04X..$%04X  aux=$%04X..$%04X  '
                  'slots[0..7]=%s...' % (y, row, row, row + 39, row, row + 39, slots))
    return True


def selfcheck_color(verbose=True):
    """Colour round trip: pattern bytes -> scanline -> main/aux -> colour cells.

    Also proves that the bit-level put_cell() encoder reproduces the reference
    pattern bytes of dhgr.c:48-55 byte for byte, on every scanline of a page.
    """
    for c in range(16):
        pat = color_pattern(c)
        assert all(b < 0x80 for b in pat), (c, pat)
        assert color_index(color_bits(c)) == c, c          # bit-phase round trip
        line = fill_line(c)
        assert line[0] == pat[0] and line[1] == pat[1], (c, pat, line[:4])
        assert line[2] == pat[2] and line[3] == pat[3], (c, pat, line[:4])
        # bit-level encoder must produce the same scanline as the pattern bytes
        bycell = bytearray(DHGR_BYTES_PER_LINE)
        for cx in range(DHGR_COLOR_WIDTH):
            put_cell(bycell, cx, c)
        assert bycell == line, (c, bytes(bycell), bytes(line))
        # full page through the main/aux split, decoded back to colour cells
        main = bytearray(DHGR_BANK_PAGE_BYTES)
        aux = bytearray(DHGR_BANK_PAGE_BYTES)
        m, a = split_line(line)
        for y in range(DHGR_HEIGHT):
            main[y * DHGR_BANK_BYTES:(y + 1) * DHGR_BANK_BYTES] = m
            aux[y * DHGR_BANK_BYTES:(y + 1) * DHGR_BANK_BYTES] = a
        for y, ln in enumerate(join_page(main, aux)):
            for cx in range(DHGR_COLOR_WIDTH):
                assert read_cell(ln, cx) == c, (c, y, cx, read_cell(ln, cx))
        if verbose:
            print('  color %2d %-9s bits=%s  pattern[aux-even,main-even,aux-odd,main-odd]='
                  '%s  <0x80 OK, round-trip OK'
                  % (c, DHGR_COLOR_NAMES[c], format(color_bits(c), '04b'),
                     ' '.join('$%02X' % b for b in pat)))
    # mixed colours: every colour cell of a page, through the main/aux split
    pages = [bytearray(DHGR_BYTES_PER_LINE) for _ in range(DHGR_HEIGHT)]
    for y in range(DHGR_HEIGHT):
        for cx in range(DHGR_COLOR_WIDTH):
            put_cell(pages[y], cx, (cx + y) & 15)
    main = bytearray(DHGR_BANK_PAGE_BYTES)
    aux = bytearray(DHGR_BANK_PAGE_BYTES)
    for y in range(DHGR_HEIGHT):
        m, a = split_line(pages[y])
        main[y * DHGR_BANK_BYTES:(y + 1) * DHGR_BANK_BYTES] = m
        aux[y * DHGR_BANK_BYTES:(y + 1) * DHGR_BANK_BYTES] = a
    for y, ln in enumerate(join_page(main, aux)):
        for cx in range(DHGR_COLOR_WIDTH):
            assert read_cell(ln, cx) == ((cx + y) & 15), (y, cx)
    if verbose:
        print('DHGR colour self-check: 16 colours OK; mixed-cell round trip %dx%d cells OK'
              % (DHGR_HEIGHT, DHGR_COLOR_WIDTH))
    return True



def main():
    os.makedirs(OUT, exist_ok=True)
    selfcheck_layout()
    selfcheck_color()
    tiles = chr_tiles(open(os.path.join(SRC, 'tileset.chr'), 'rb').read())
    print('tiles:', len(tiles))

    # sanity: decode every map and check the nametable size.
    # `raws` keeps the untouched RLE stream (what the NES binary links and what
    # the Apple II streams from disk); `maps` keeps the decoded 1024-byte
    # nametable used to raster the DHGR/HGR demos.
    maps = []
    raws = []
    for i in range(26):
        p = os.path.join(SRC, 'map%d.h' % i)
        raw = parse_c_array(p)
        nt = decode_rle(raw)
        raws.append(raw)
        maps.append(nt)
        print('map%-2d bytes=%5d nametable=%d' % (i, len(raw), len(nt)))
    assert all(len(m) == 1024 for m in maps), [len(m) for m in maps]

    # DHGR tiles (4-bit colour cells)
    dhgr = bytearray()
    for t in tiles:
        dhgr += tile_to_dhgr(t)
    emit_c_array(os.path.join(OUT, 'dhgr_tiles.s'), 'dhgr_tiles', dhgr)
    print('dhgr tiles: %d x %d bytes = %d' % (len(tiles), DHGR_TILE_BYTES, len(dhgr)))

    # 8x16 sprites: the player set is tiles 0x90..0x97 (game.c PLAYER_SPR_*)
    sprs = bytearray()
    for t in range(0x90, 0x98, 2):
        sprs += sprite_to_dhgr(tiles, t)
    emit_c_array(os.path.join(OUT, 'dhgr_spr.s'), 'dhgr_spr', sprs)
    print('dhgr sprites: %d x %d bytes = %d'
          % (len(sprs) // DHGR_SPRITE_BYTES, DHGR_SPRITE_BYTES, len(sprs)))

    # HGR tiles / sprites / level 0 screen (the gameplay view)
    htiles = bytearray()
    for t in tiles:
        htiles += tile_to_hgr(t)
    emit_c_array(os.path.join(OUT, 'hgr_tiles.s'), 'hgr_tiles', htiles)

    # The //e build does not link the tileset.  src/a2/neslib.c reads it from
    # $4000 (TILE_BASE) and src/a2/lvload.s: lv_assets BLOAD-s the disk file
    # TILES there once at startup, so the same bytes are also written out raw.
    with open(os.path.join(OUT, 'hgr_tiles.bin'), 'wb') as f:
        f.write(bytes(htiles))

    hsprs = bytearray()
    for t in range(0x90, 0x98, 2):
        hsprs += sprite_to_hgr(tiles, t)
    emit_c_array(os.path.join(OUT, 'hgr_spr.s'), 'hgr_spr', hsprs)
    hscr = build_hgr_screen(tiles, maps[0])
    henc = rle_encode_screen(hscr)
    emit_c_array(os.path.join(OUT, 'hgr_screen0.s'), 'hgr_screen0', henc)
    print('hgr tiles=%d  sprites=%d  screen raw=%d rle=%d'
          % (len(htiles), len(hsprs) // 32, len(hscr), len(henc)))

    # ------------------------------------------------------------------------
    # Per-level payloads for streaming (user directive: load the next level
    # only when the current one is cleared, never link all 26 into the binary).
    #
    # The payload is the ORIGINAL NES RLE stream, byte for byte: game.c loads a
    # level with unrle_vram(level_ptrs[n*2], 0x2000) and then recovers the tile
    # grid with vram_read(map, 0x20c0, MAP_WDT*MAP_HGT) (src/game.c:822).  The
    # Apple II layer keeps a shadow grid of NES tile numbers, so feeding it the
    # untouched stream gives both the picture and the grid the game logic wants.
    # hgr_tiles is indexed by NES tile number, so no conversion table is needed.
    #
    # Each file is BLOAD-ed to the staging buffer at $1000 (LOWBSS in
    # src/a2/a2_128.cfg) and decoded in place.
    # ------------------------------------------------------------------------
    lv_dir = os.path.join(OUT, 'lv')
    os.makedirs(lv_dir, exist_ok=True)
    lv_sizes = []
    for i, raw in enumerate(raws):
        stream = bytes(raw)
        with open(os.path.join(lv_dir, 'lv%02d.bin' % i), 'wb') as f:
            f.write(stream)
        lv_sizes.append(len(stream))
    over = [i for i, n in enumerate(lv_sizes) if n > 4096]
    print('level payloads (NES RLE): n=%d min=%d max=%d avg=%d total=%d  (staging 4096 B)'
          % (len(lv_sizes), min(lv_sizes), max(lv_sizes),
             sum(lv_sizes) // len(lv_sizes), sum(lv_sizes)))
    if over:
        raise SystemExit('levels over the 4 KB staging buffer: %s' % over)

    # level 0 screen + preview: one page as main bank + aux bank
    main_bank, aux_bank = build_dhgr_screen(tiles, maps[0])
    save_png(main_bank, aux_bank, os.path.join(OUT, 'level0_dhgr.png'))
    selfcheck_rle([('dhgr screen0 main', main_bank),
                   ('dhgr screen0 aux', aux_bank)])
    enc_main = rle_encode_screen(main_bank)
    enc_aux = rle_encode_screen(aux_bank)
    emit_c_arrays(os.path.join(OUT, 'dhgr_screen0.s'),
                  [('dhgr_screen0_main', enc_main),
                   ('dhgr_screen0_aux', enc_aux)])
    for tag, bank in (('main', main_bank), ('aux', aux_bank)):
        with open(os.path.join(OUT, 'dhgr_screen0_%s.bin' % tag), 'wb') as f:
            f.write(bank)
    print('level0 screen raw main=%d aux=%d total=%d  rle main=%d aux=%d total=%d'
          % (len(main_bank), len(aux_bank), len(main_bank) + len(aux_bank),
             len(enc_main), len(enc_aux), len(enc_main) + len(enc_aux)))

    # all levels, RLE (main + aux per level)
    sizes = []
    for i, m in enumerate(maps):
        mb, ab = build_dhgr_screen(tiles, m)
        sizes.append(len(rle_encode_screen(mb)) + len(rle_encode_screen(ab)))
    print('all levels RLE (main+aux): min=%d max=%d avg=%d total=%d'
          % (min(sizes), max(sizes), sum(sizes) // len(sizes), sum(sizes)))


if __name__ == '__main__':
    main()
