#!/usr/bin/env python3
"""Convert a source NES full-screen RLE nametable for the VERA tile layer."""
from pathlib import Path
import os
import re
import sys

import a2vera_title as V

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("AE2VERA_ART_OUT") or (ROOT / "vera/build"))
# The credits screen names the target platform.  Default is the Apple II VERA
# release; the Commander X16 build sets AE2VERA_CREDITS_PLATFORM='COMMANDER X16'
# and writes to its own directory so vera/build stays byte-identical.
PLATFORM = os.environ.get("AE2VERA_CREDITS_PLATFORM", "APPLE II VERA")



def palette_array(name):
    text = (ROOT / "src/palettes.h").read_text(encoding="ascii")
    m = re.search(r"\b" + re.escape(name) + r"\[16\]\s*=\s*\{([^}]*)\}", text)
    if not m:
        raise ValueError(f"palette {name} not found")
    values = [int(v, 16) for v in re.findall(r"0x([\da-fA-F]{2})", m.group(1))]
    if len(values) != 16:
        raise ValueError(f"{name} must have 16 entries")
    return values


def convert(header, palette_name, stem):
    raw = V.decode_rle(V.c_array(ROOT / "src" / header))
    if len(raw) != 1024:
        raise ValueError(f"{header} decoded to {len(raw)} bytes, expected 1024")
    nt, attrs = raw[:960], raw[960:]
    banks = bytearray((attrs[(y >> 2) * 8 + (x >> 2)] >>
                       (((y & 2) << 1) | (x & 2))) & 3
                      for y in range(30) for x in range(32))
    if stem == 'credits':
        # Keep all upstream credits, moving them up five 8-pixel rows.
        nt = bytearray(nt[5*32:]) + bytearray(5*32)
        banks = banks[5*32:] + bytearray(5*32)
        font = {chr(65+i): 0x80+i for i in range(16)}
        font.update({chr(81+i): 0x6A+i for i in range(6)})
        font.update({chr(87+i): 0x7A+i for i in range(4)})
        font.update({str(i): 0xF0+i for i in range(10)})
        font[' '] = 0
        for y, line, bank in ((24, f'{PLATFORM} CONVERSION BY', 3),
                              (26, 'ANOMIXER 2026', 1)):
            x = 3  # Match the left edge of every upstream credit line.
            for i, ch in enumerate(line):
                nt[y*32+x+i] = font[ch]
                banks[y*32+x+i] = bank
    chrdata = (ROOT / "src/tileset.chr").read_bytes()
    codes = palette_array(palette_name)
    tilemap = bytearray(64 * 32 * 2)
    for y in range(30):
        for x in range(32):
            bank = banks[y*32+x]
            off = (y * 64 + x + 4) * 2
            tilemap[off] = nt[y * 32 + x]
            tilemap[off + 1] = bank << 4
            if stem == 'ending':
                duplicate=(y*64+((x+4+32)&63))*2
                tilemap[duplicate:duplicate+2]=tilemap[off:off+2]
    if stem == 'ending':
        for y in (24,25):
            for x in range(8,25):
                tilemap[(y*64+((x+4+32)&63))*2]=0
    pal = bytearray(512)
    for bank in range(4):
        for shade in range(4):
            r, g, b = V.nes_rgb(codes[bank * 4 + shade])
            pos = (bank * 16 + shade) * 2
            pal[pos] = (g >> 4) << 4 | (b >> 4)
            pal[pos + 1] = r >> 4
    sprites=palette_array('palSprites')
    for bank in range(4):
        for shade in range(4):
            r,g,b=V.nes_rgb(sprites[bank*4+shade])
            pos=((bank+4)*16+shade)*2
            pal[pos]=(g>>4)<<4|(b>>4)
            pal[pos+1]=r>>4
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}_map.bin").write_bytes(tilemap)
    (OUT / f"{stem}_palette.bin").write_bytes(pal)

    from PIL import Image
    image = Image.new("RGB", (320, 240), (0, 0, 0))
    pixels = image.load()
    for y in range(30):
        for x in range(32):
            tile = nt[y * 32 + x]
            bank = banks[y*32+x]
            for ty in range(8):
                lo = chrdata[tile * 16 + ty]
                hi = chrdata[tile * 16 + ty + 8]
                for tx in range(8):
                    shade = (((hi >> (7 - tx)) & 1) << 1) | ((lo >> (7 - tx)) & 1)
                    pixels[32 + x * 8 + tx, y * 8 + ty] = V.nes_rgb(codes[bank * 4 + shade])
    image.save(OUT / f"{stem}_preview.png")
    print(f"{header}: {len(tilemap)}B VERA tilemap + {len(pal)}B palette")
    print(f"preview: {OUT / f'{stem}_preview.png'}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "credits"):
        convert("credits.h", "palTitleBG", "credits")
    if which in ("all", "ending"):
        convert("welldone.h", "palWellDone", "ending")
    if which in ("all", "gameover"):
        convert("gameover.h", "palGameBG1", "gameover")
