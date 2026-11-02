#!/usr/bin/env python3
"""Convert the NES title nametable/CHR/palettes to native VERA 4bpp tiles."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "vera/build"

def c_array(path):
    text = path.read_text(encoding="ascii")
    m = re.search(r"\[[^\]]*\]\s*=\s*\{(.*?)\}", text, re.S)
    if not m:
        raise ValueError(f"array missing in {path}")
    return bytes(int(x, 16) for x in re.findall(r"0x([\da-fA-F]{2})", m.group(1)))

def decode_rle(data):
    tag, i, last, out = data[0], 1, 0, bytearray()
    while i < len(data):
        b = data[i]; i += 1
        if b != tag:
            out.append(b); last = b
        else:
            n = data[i]; i += 1
            if n == 0: break
            out.extend([last] * n)
    return out

def nes_rgb(code):
    # FCEUX-13 palette used by the repo's NES preview tooling.
    p = [
      (96,96,96),(0,0,120),(20,0,128),(44,0,110),(74,0,78),(108,0,24),(90,3,2),(81,24,0),
      (52,36,0),(0,52,0),(0,50,0),(0,52,32),(0,44,120),(0,0,0),(2,2,2),(2,2,2),
      (196,196,196),(0,88,222),(48,31,252),(127,20,224),(168,0,176),(192,6,92),(192,43,14),(166,64,16),
      (111,97,0),(48,128,0),(0,124,0),(0,124,60),(0,110,132),(20,20,20),(4,4,4),(4,4,4),
      (240,240,240),(76,170,255),(111,115,245),(176,112,255),(218,90,255),(240,96,192),(248,131,109),(208,144,48),
      (212,192,48),(102,208,0),(38,221,26),(46,200,102),(52,194,190),(84,84,84),(6,6,6),(6,6,6),
      (255,255,255),(182,218,255),(200,202,255),(218,194,255),(240,190,255),(252,188,238),(255,208,180),(255,218,144),
      (236,236,146),(220,246,158),(184,255,162),(174,234,190),(158,239,239),(190,190,190),(8,8,8),(8,8,8)]
    return p[code & 63]

def encode_rle(data):
    """Pack byte runs for the small VERA map loader (run or literal tokens)."""
    out=bytearray(); i=0
    while i<len(data):
        j=i+1
        while j<len(data) and data[j]==data[i] and j-i<130: j+=1
        if j-i>=3:
            out.extend((0x80|(j-i-3),data[i])); i=j
        else:
            start=i; i=j
            while i<len(data) and i-start<128:
                j=i+1
                while j<len(data) and data[j]==data[i] and j-i<3: j+=1
                if j-i>=3: break
                i=j
            n=i-start
            out.append(n-1); out.extend(data[start:i])
    return out

def main():
    raw = decode_rle(c_array(ROOT / "src/title.h"))
    if len(raw) != 1024: raise ValueError(f"title data size {len(raw)} != 1024")
    nametable, attrs = raw[:960], raw[960:]
    chrdata = (ROOT / "src/tileset.chr").read_bytes()
    if len(chrdata) != 8192: raise ValueError("expected 8KB CHR")
    # NES CHR tiles store plane 0 in bytes 0..7 and plane 1 in bytes 8..15.
    # VERA 4bpp tile bytes store even x in high nibble, odd x in low nibble.
    tiles = bytearray()
    for t in range(256):
        for y in range(8):
            lo, hi = chrdata[t*16+y], chrdata[t*16+y+8]
            for x in range(0,8,2):
                a = (((hi >> (7-x)) & 1) << 1) | ((lo >> (7-x)) & 1)
                b = (((hi >> (6-x)) & 1) << 1) | ((lo >> (6-x)) & 1)
                tiles.append((a << 4) | b)
    # VERA map is 64x32, two bytes per cell. Place 32x30 NES title at x=4.
    tilemap = bytearray(64*32*2)
    palette_codes = []
    for y in range(30):
        for x in range(32):
            tile = nametable[y*32+x]
            av = attrs[(y >> 2)*8+(x >> 2)]
            pal = (av >> (((y & 2) << 1) | (x & 2))) & 3
            off = (y*64+x+4)*2
            tilemap[off] = tile
            tilemap[off+1] = pal << 4
    # Populate four 16-colour VERA palette banks with the NES subpalettes.
    ptxt=(ROOT/'src/palettes.h').read_text(encoding='ascii')
    m=re.search(r'palTitleBG\[16\]\s*=\s*\{([^}]*)\}',ptxt)
    if not m: raise ValueError('palTitleBG unavailable')
    nes=[int(v,16) for v in re.findall(r'0x([\da-fA-F]{2})',m.group(1))]
    if len(nes)!=16: raise ValueError('palTitleBG should have 16 entries')
    pal=bytearray(512)
    for bank in range(4):
        for shade in range(4):
            r,g,b=nes_rgb(nes[bank*4+shade])
            idx=bank*16+shade
            pal[idx*2]=(g>>4)<<4 | (b>>4)
            pal[idx*2+1]=r>>4
            pal[(idx+64)*2]=pal[idx*2]
            pal[(idx+64)*2+1]=pal[idx*2+1]
            palette_codes.append((r,g,b))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'title_tiles_4bpp.bin').write_bytes(tiles)
    packed_map=encode_rle(tilemap)
    (OUT/'title_screen_map_rle.bin').write_bytes(packed_map)
    (OUT/'title_screen_palette.bin').write_bytes(pal[:256])
    # NES title_screen() alternates the normal nametable and a duplicate with
    # its 20 PRESS START cells erased. Store byte offsets and source tile IDs.
    prompt=[]
    for y in range(30):
        for x in range(32):
            tile=nametable[y*32+x]
            if 0x40<=tile<=0x7f:
                off=((y*64+x+4)*2)
                prompt.extend((off&255,off>>8,tile))
    (OUT/'title_screen_prompt.bin').write_bytes(bytes((len(prompt)//3,))+bytes(prompt))
    from PIL import Image
    img=Image.new('RGB',(320,240),(0,0,0)); px=img.load()
    for y in range(30):
      for x in range(32):
        tile=nametable[y*32+x]
        av=attrs[(y>>2)*8+(x>>2)]; bank=(av>>(((y&2)<<1)|(x&2)))&3
        for ty in range(8):
          for tx in range(8):
            lo,hi=chrdata[tile*16+ty],chrdata[tile*16+ty+8]
            shade=(((hi>>(7-tx))&1)<<1)|((lo>>(7-tx))&1)
            px[32+x*8+tx,y*8+ty]=nes_rgb(nes[bank*4+shade])
    img.save(OUT/'title_vera_preview.png')
    print(f"title: {len(tiles)} tile bytes, map {len(tilemap)} -> {len(packed_map)}B, {len(pal[:256])} palette bytes, {len(prompt)//3} flashing cells")
    print(f"preview: {OUT/'title_vera_preview.png'}")
if __name__=='__main__': main()
